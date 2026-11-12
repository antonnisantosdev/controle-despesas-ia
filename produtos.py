"""Preço de um produto por loja, a partir dos talões (Minhas compras). Sem IA: só contas e texto.

- chave_do_produto: o nome normalizado que junta o mesmo produto entre talões e lojas
  ("LEITE M/GORDO 1L" e "Leite meio-gordo 1 L" dão os dois "leite meio gordo").
- O preço guardado em compra_itens.preco é o VALOR DA LINHA: o preço unitário é preco / quantidade.
- O utilizador pode juntar duas chaves que são o mesmo produto (tabela produtos_alias, sql/018).

Precisa da sql/018 corrida (colunas produto_chave, unidade e nome_generico, e a tabela produtos_alias).
Os itens gravados antes da 018 têm produto_chave vazio: a chave calcula-se aqui, ao ler (preenchimento preguiçoso).
"""

import re
from collections import defaultdict
from datetime import date

from fastapi import HTTPException

from consultas import normalizar
from database import ler_todas, supabase
from limites import hoje_em_lisboa
from mensagens import msg
from models import (
    JuncaoProdutos,
    PrecoHistorico,
    PrecoNaLoja,
    PrecosDoProduto,
    PrecosPorUnidade,
    ProdutoResumo,
)

# Tamanho máximo de uma chave (igual ao do JuntarProdutos, em models.py).
MAX_CARACTERES_CHAVE = 100
# Só se lê o início do texto: um texto enorme (ex.: milhares de algarismos) não chega às contas.
MAX_CARACTERES_TEXTO = 300
# Produtos devolvidos pela lista e linhas do histórico de um produto.
MAX_PRODUTOS = 50
MAX_HISTORICO = 100
# Passos máximos ao seguir as junções (A -> B -> C...): trava qualquer ciclo que escape à validação.
MAX_PASSOS_ALIAS = 20
# Só se leem as compras dos últimos 24 meses: cada pedido lê todos os itens desse período (custo e tempo).
MESES_DE_COMPRAS = 24
# Junções máximas por utilizador (acima, 422): trava quem tente encher a tabela produtos_alias.
MAX_JUNCOES = 500

# --- Normalização do nome ---

# Abreviaturas com barra, vistas antes de tirar a pontuação: "C/ AÇÚCAR", "S/ GLÚTEN", "M/GORDO".
_ABREVIATURAS_COM_BARRA = [
    (re.compile(r"(?<![a-z0-9])m\s*/\s*g(?![a-z0-9])"), " meio gordo "),
    (re.compile(r"(?<![a-z0-9])m\s*/\s*"), " meio "),
    (re.compile(r"(?<![a-z0-9])c\s*/\s*"), " com "),
    (re.compile(r"(?<![a-z0-9])s\s*/\s*"), " sem "),
]

# Palavras cortadas comuns nos talões portugueses. Só as óbvias: na dúvida, fica como está.
ABREVIATURAS = {
    "gord": "gordo",
    "magr": "magro",
    "iog": "iogurte",
    "iogur": "iogurte",
    "nat": "natural",
    "choc": "chocolate",
    "integ": "integral",
    "cong": "congelado",
    "peq": "pequeno",
}

# Unidades de medida do tamanho da embalagem, e o fator para a unidade base (g, ml ou unidades).
# Sem "mg": nos talões, "LEITE MG" é leite meio gordo, não miligramas.
_PESO = {"kg": 1000, "kgs": 1000, "g": 1, "gr": 1, "grs": 1}
_VOLUME = {"l": 1000, "lt": 1000, "lts": 1000, "ml": 1, "cl": 10, "dl": 100}
_UNIDADES = {"un": 1, "uni": 1, "und": 1, "unid": 1, "unids": 1}
_MEDIDAS = _PESO | _VOLUME | _UNIDADES
_NOMES_MEDIDAS = "|".join(sorted(_MEDIDAS, key=len, reverse=True))

_NUMERO = r"\d+(?:\.\d+)?"
# "1l", "1.5kg", "500" (o número sozinho; a unidade pode vir na palavra seguinte).
_TAMANHO = re.compile(rf"^({_NUMERO})({_NOMES_MEDIDAS})?$")
# "6x1l", "4x120g", "6x1" (pack: quantas embalagens x o tamanho de cada uma).
_PACK_COM_TAMANHO = re.compile(rf"^(\d+)x({_NUMERO})({_NOMES_MEDIDAS})?$")
# "x6" ou "6x" (pack sem tamanho na mesma palavra).
_SO_PACK = re.compile(r"^(?:x(\d+)|(\d+)x)$")


def _numero(valor: float) -> str:
    """Até 3 casas decimais, com ponto e sem zeros à direita: 1.0 -> "1", 1.50 -> "1.5"."""
    return f"{valor:.3f}".rstrip("0").rstrip(".")


def formatar_tamanho(valor: float, medida: str) -> str:
    """O tamanho num formato único. Pesos em g abaixo de 1000 g e em kg a partir daí; volumes em ml
    abaixo de 1000 ml e em l a partir daí; unidades em "un".
    "1L", "1000ML" -> "1 l"; "0,75L" -> "750 ml"; "500G", "0,5KG" -> "500 g"; "1,5KG" -> "1.5 kg"."""
    base = valor * _MEDIDAS[medida]
    if medida in _PESO:
        return f"{_numero(base / 1000)} kg" if base >= 1000 else f"{_numero(base)} g"
    if medida in _VOLUME:
        return f"{_numero(base / 1000)} l" if base >= 1000 else f"{_numero(base)} ml"
    return f"{_numero(base)} un"


def _separar_tamanhos(palavras: list[str]) -> tuple[list[str], list[str], int | None]:
    """Separa as palavras do nome, os tamanhos (já formatados) e o número de embalagens do pack.

    Números sem unidade (preços, códigos) e unidades soltas ("BANANA KG") saem.
    """
    nome: list[str] = []
    tamanhos: list[str] = []
    pack: int | None = None
    i = 0
    while i < len(palavras):
        palavra = palavras[i]
        seguinte = palavras[i + 1] if i + 1 < len(palavras) else ""
        if m := _PACK_COM_TAMANHO.match(palavra):
            medida = m.group(3) or (seguinte if seguinte in _MEDIDAS else None)
            if medida:
                pack = int(m.group(1))
                tamanhos.append(formatar_tamanho(float(m.group(2)), medida))
                i += 1 if m.group(3) else 2
                continue
        elif m := _TAMANHO.match(palavra):
            medida = m.group(2) or (seguinte if seguinte in _MEDIDAS else None)
            if medida:
                tamanhos.append(formatar_tamanho(float(m.group(1)), medida))
                i += 1 if m.group(2) else 2
                continue
            if seguinte == "x" and m.group(1).isdigit():  # "6 x 1 l"
                pack = int(m.group(1))
                i += 2
                continue
            i += 1  # um número sem unidade: preço ou código
            continue
        elif m := _SO_PACK.match(palavra):
            pack = int(m.group(1) or m.group(2))
            i += 1
            continue
        elif palavra == "x" and seguinte.isdigit():  # "1 l x 6"
            pack = int(seguinte)
            i += 2
            continue
        elif palavra in _MEDIDAS or palavra == "x":
            i += 1
            continue
        nome.append(ABREVIATURAS.get(palavra, palavra))
        i += 1
    return nome, tamanhos, pack


def chave_do_produto(texto: str, com_tamanho: bool = True) -> str:
    """O nome normalizado de um produto, para juntar o mesmo produto entre talões. Determinista, sem IA.

    Sem acentos e em minúsculas, sem pontuação, com as abreviaturas óbvias por extenso e com o tamanho da
    embalagem num formato único no fim ("LEITE M/G 1L" e "Leite meio-gordo 1000 ml" dão "leite meio gordo 1 l";
    "1,5 L" dá outro produto). Um pack fica "6x1 l" (ou "6x" sem tamanho).
    com_tamanho=False nos produtos ao peso ou ao litro (unidade kg ou l): aí o número é o que se pesou,
    não o tamanho da embalagem, e sai.
    Se não sobrar nada (ex.: só números), fica o texto normalizado.
    Normalizar uma chave dá a mesma chave (as rotas normalizam a chave que recebem no endereço).
    """
    texto = normalizar((texto or "")[:MAX_CARACTERES_TEXTO])
    for padrao, por_extenso in _ABREVIATURAS_COM_BARRA:
        texto = padrao.sub(por_extenso, texto)
    # Vírgula decimal passa a ponto ("1,5kg" -> "1.5kg"); o resto da pontuação passa a espaço.
    texto = re.sub(r"(?<=\d),(?=\d)", ".", texto)
    texto = re.sub(r"(?<=\d)\.(?!\d)|(?<!\d)\.", " ", texto)
    texto = re.sub(r"[^a-z0-9.]+", " ", texto)

    nome, tamanhos, pack = _separar_tamanhos(texto.split())
    if pack and pack > 1:
        if tamanhos:
            tamanhos[0] = f"{pack}x{tamanhos[0]}"
        else:
            tamanhos.append(f"{pack}x")
    # Ao peso, o tamanho sai; mas se o nome for só medidas (ex.: "500g"), fica o tamanho: senão a chave
    # guardada ("500g") e a mesma chave normalizada na rota ("500 g") eram diferentes.
    if com_tamanho or not nome:
        nome += tamanhos

    return _juntar_ate_ao_maximo(nome) or _juntar_ate_ao_maximo(texto.split())


def _juntar_ate_ao_maximo(partes: list[str]) -> str:
    """Junta as partes com espaços até MAX_CARACTERES_CHAVE, sem cortar nenhuma a meio (um tamanho como
    "1.5 l" é uma parte só: cortado ficava "1.5", que a normalização seguinte tirava)."""
    chave = ""
    for parte in partes:
        candidata = f"{chave} {parte}" if chave else parte
        if len(candidata) > MAX_CARACTERES_CHAVE:
            # Uma palavra sozinha maior do que o máximo fica cortada (não há como a partir de outra forma).
            return chave or parte[:MAX_CARACTERES_CHAVE]
        chave = candidata
    return chave


def preco_unitario(preco: float, quantidade: float) -> float | None:
    """O preço por unidade, kg ou litro: o preço da linha a dividir pela quantidade.

    None (a linha não entra nas contas) se a quantidade não for positiva ou o preço for 0 (um brinde
    a 0 € puxava o mínimo para 0 e enganava a comparação).
    """
    if not quantidade or quantidade <= 0 or preco is None or preco <= 0:
        return None
    return round(preco / quantidade, 2)


# --- Leitura dos itens do utilizador ---


def _unidade_do_item(item: dict) -> str:
    """A unidade do item. Os itens de antes da 018 (sem produto_chave) ficam todos com "un" na base de dados:
    nesses, uma quantidade com casas decimais só pode ser um peso (as regras do talão pedem o peso em kg)."""
    unidade = item.get("unidade") or "un"
    if item.get("produto_chave") is None and unidade == "un":
        quantidade = float(item.get("quantidade") or 0)
        if quantidade != int(quantidade):
            return "kg"
    return unidade


def inicio_do_periodo(hoje: date) -> date:
    """O dia 1 do mês de há MESES_DE_COMPRAS meses: as compras anteriores não entram nos preços."""
    absoluto = hoje.year * 12 + (hoje.month - 1) - MESES_DE_COMPRAS
    return date(absoluto // 12, absoluto % 12 + 1, 1)


def _linhas_de_compras(user_id: str) -> list[dict]:
    """As compras do utilizador dos últimos MESES_DE_COMPRAS meses, cada uma com os seus produtos
    (o filtro user_id vem sempre do token)."""
    desde = inicio_do_periodo(hoje_em_lisboa()).isoformat()
    return ler_todas(
        lambda: supabase.table("compras")
        .select("id, loja, data, compra_itens(descricao, quantidade, preco, produto_chave, unidade, nome_generico)")
        .eq("user_id", user_id)
        .gte("data", desde)
        .order("id")
    )


def itens_do_utilizador(user_id: str) -> list[dict]:
    """Todos os produtos comprados pelo utilizador, um por linha de talão, já com a chave (sem as junções)."""
    itens = []
    for compra in _linhas_de_compras(user_id):
        for item in compra.get("compra_itens") or []:
            unidade = _unidade_do_item(item)
            chave = item.get("produto_chave") or chave_do_produto(
                item.get("nome_generico") or item["descricao"], com_tamanho=unidade == "un"
            )
            itens.append(
                {
                    "compra_id": compra["id"],
                    "loja": compra["loja"],
                    "data": date.fromisoformat(str(compra["data"])[:10]),
                    "chave": chave,
                    "nome": item.get("nome_generico") or item["descricao"],
                    "unidade": unidade,
                    "quantidade": float(item["quantidade"]),
                    "preco": float(item["preco"]),
                }
            )
    return itens


# --- Junções (alias) ---


def alias_do_utilizador(user_id: str) -> dict[str, str]:
    """As junções do utilizador: chave de origem -> chave de destino."""
    resposta = (
        supabase.table("produtos_alias").select("chave_origem, chave_destino").eq("user_id", user_id).execute()
    )
    return {linha["chave_origem"]: linha["chave_destino"] for linha in resposta.data}


def chave_final(chave: str, alias: dict[str, str]) -> str:
    """Segue as junções até ao fim (A -> B -> C dá C). Num ciclo (não devia haver), para onde começou."""
    vistas = {chave}
    atual = chave
    for _ in range(MAX_PASSOS_ALIAS):
        seguinte = alias.get(atual)
        if seguinte is None:
            return atual
        if seguinte in vistas:
            return chave
        vistas.add(seguinte)
        atual = seguinte
    return chave


def fecha_ciclo(origem: str, destino: str, alias: dict[str, str]) -> bool:
    """Se a junção origem -> destino, somada às que já existem, cria um ciclo.

    Segue o caminho a partir do destino, já com a junção nova: é ciclo se passar pela origem ou repetir
    uma chave. (O chave_final não serve aqui: num ciclo devolve a chave de partida e esconde-o.)
    """
    mapa = alias | {origem: destino}
    vistas = {origem, destino}
    atual = destino
    while atual in mapa:
        atual = mapa[atual]
        if atual in vistas:
            return True
        vistas.add(atual)
    return False


def aplicar_alias(itens: list[dict], alias: dict[str, str]) -> list[dict]:
    return [item | {"chave": chave_final(item["chave"], alias)} for item in itens]


def juntar_produtos(user_id: str, chave_origem: str, chave_destino: str, pais: str = "PT") -> None:
    """Grava a junção chave_origem -> chave_destino. 404 se uma das chaves não existir nos itens do utilizador;
    422 se forem iguais ou se a junção fechasse um ciclo (A -> B -> A). pais: a língua das mensagens."""
    origem, destino = chave_origem.strip(), chave_destino.strip()
    if not origem or not destino or origem == destino:
        raise HTTPException(status_code=422, detail=msg("juntar_iguais", pais))
    chaves = {item["chave"] for item in itens_do_utilizador(user_id)}
    if origem not in chaves or destino not in chaves:
        raise HTTPException(status_code=404, detail=msg("produto_nao_encontrado", pais))
    alias = alias_do_utilizador(user_id)
    # Juntar outra vez a mesma origem substitui a junção: não conta para o teto.
    if origem not in alias and len(alias) >= MAX_JUNCOES:
        raise HTTPException(status_code=422, detail=msg("juntar_maximo", pais, maximo=MAX_JUNCOES))
    if fecha_ciclo(origem, destino, alias):
        raise HTTPException(status_code=422, detail=msg("juntar_ao_contrario", pais))
    supabase.table("produtos_alias").upsert(
        {"user_id": user_id, "chave_origem": origem, "chave_destino": destino},
        on_conflict="user_id,chave_origem",
    ).execute()


def juncoes_do_utilizador(user_id: str) -> list[JuncaoProdutos]:
    """As junções do utilizador, das mais recentes para as mais antigas, com o nome mostrado de cada chave."""
    linhas = (
        supabase.table("produtos_alias")
        .select("chave_origem, chave_destino, criado_em")
        .eq("user_id", user_id)
        .order("criado_em", desc=True)
        .execute()
        .data
    )
    if not linhas:
        return []
    # O nome de cada chave antes das junções (cada chave tem o seu nome, mesmo a que foi juntada a outra).
    por_chave: dict[str, list[dict]] = defaultdict(list)
    for item in itens_do_utilizador(user_id):
        por_chave[item["chave"]].append(item)

    def nome(chave: str) -> str:
        itens = por_chave.get(chave)
        return _mais_recente(itens)["nome"] if itens else chave

    juncoes = [
        JuncaoProdutos(
            chave_origem=linha["chave_origem"],
            nome_origem=nome(linha["chave_origem"]),
            chave_destino=linha["chave_destino"],
            nome_destino=nome(linha["chave_destino"]),
            criado_em=linha.get("criado_em"),
        )
        for linha in linhas
    ]
    # Ordena também aqui (a base de dados já ordena; isto garante a ordem com criado_em vazio).
    juncoes.sort(key=lambda juncao: juncao.criado_em.timestamp() if juncao.criado_em else 0, reverse=True)
    return juncoes


def separar_produtos(user_id: str, chave_origem: str, pais: str = "PT") -> None:
    """Desfaz a junção de chave_origem. 404 se não houver (mensagem na língua de pais).

    Procura primeiro a chave tal como veio (só sem espaços nas pontas) e depois a normalizada: uma junção
    gravada com uma chave antiga, de outra regra de normalização, também se consegue desfazer.
    """
    exata = chave_origem.strip()
    for chave in dict.fromkeys([exata, chave_do_produto(exata)]):
        resposta = (
            supabase.table("produtos_alias").delete().eq("user_id", user_id).eq("chave_origem", chave).execute()
        )
        if resposta.data:
            return
    raise HTTPException(status_code=404, detail=msg("juncao_nao_existe", pais))


# --- Contas ---


def _loja_chave(loja: str) -> str:
    """Para juntar "Supermercado Bom Preço" e "SUPERMERCADO BOM PRECO" na mesma loja."""
    return " ".join(normalizar(loja).split())


def _mais_recente(itens: list[dict]) -> dict:
    return max(itens, key=lambda item: (item["data"], item["compra_id"]))


def lista_de_produtos(itens: list[dict], pesquisa: str | None = None) -> list[ProdutoResumo]:
    """Um resumo por produto (chave final), dos comprados há menos tempo para os mais antigos."""
    por_chave: dict[str, list[dict]] = defaultdict(list)
    for item in itens:
        por_chave[item["chave"]].append(item)

    termo = " ".join(normalizar(pesquisa or "").split())
    produtos = []
    for chave, do_produto in por_chave.items():
        recente = _mais_recente(do_produto)
        if termo and termo not in chave and termo not in normalizar(recente["nome"]):
            continue
        produtos.append(
            ProdutoResumo(
                chave=chave,
                nome=recente["nome"],
                unidades=sorted({item["unidade"] for item in do_produto}),
                ultima_data=recente["data"],
                n_lojas=len({_loja_chave(item["loja"]) for item in do_produto}),
                n_compras=len({item["compra_id"] for item in do_produto}),
            )
        )
    produtos.sort(key=lambda produto: (-produto.ultima_data.toordinal(), produto.nome))
    return produtos[:MAX_PRODUTOS]


def _precos_numa_unidade(unidade: str, itens: list[dict]) -> PrecosPorUnidade:
    por_loja: dict[str, list[dict]] = defaultdict(list)
    for item in itens:
        por_loja[_loja_chave(item["loja"])].append(item)

    lojas = []
    for da_loja in por_loja.values():
        recente = _mais_recente(da_loja)
        precos = [item["preco_unitario"] for item in da_loja]
        # A média sai dos preços por unidade sem arredondar: arredondar duas vezes tirava 1 cêntimo (1,196 → 1,19).
        brutos = [item["preco"] / item["quantidade"] for item in da_loja]
        lojas.append(
            PrecoNaLoja(
                loja=recente["loja"],
                preco_recente=recente["preco_unitario"],
                data_recente=recente["data"],
                preco_minimo=min(precos),
                preco_medio=round(sum(brutos) / len(brutos), 2),
                n_compras=len({item["compra_id"] for item in da_loja}),
            )
        )
    lojas.sort(key=lambda loja: (loja.preco_recente, loja.loja))

    ordenados = sorted(itens, key=lambda item: (item["data"], item["compra_id"]), reverse=True)
    historico = [
        PrecoHistorico(data=item["data"], loja=item["loja"], preco_unitario=item["preco_unitario"])
        for item in ordenados[:MAX_HISTORICO]
    ]
    return PrecosPorUnidade(unidade=unidade, lojas=lojas, historico=historico)


def precos_do_produto(itens: list[dict], chave: str) -> PrecosDoProduto | None:
    """Os preços unitários de um produto por loja, separados por unidade. None se não houver o produto."""
    do_produto = [item for item in itens if item["chave"] == chave]
    if not do_produto:
        return None
    por_unidade: dict[str, list[dict]] = defaultdict(list)
    for item in do_produto:
        unitario = preco_unitario(item["preco"], item["quantidade"])
        if unitario is not None:
            por_unidade[item["unidade"]].append(item | {"preco_unitario": unitario})
    # A unidade com mais compras primeiro (normalmente só há uma).
    unidades = sorted(por_unidade, key=lambda unidade: (-len(por_unidade[unidade]), unidade))
    return PrecosDoProduto(
        chave=chave,
        nome=_mais_recente(do_produto)["nome"],
        por_unidade=[_precos_numa_unidade(unidade, por_unidade[unidade]) for unidade in unidades],
    )


# --- O que as rotas chamam ---


def produtos_do_utilizador(user_id: str, pesquisa: str | None = None) -> list[ProdutoResumo]:
    itens = aplicar_alias(itens_do_utilizador(user_id), alias_do_utilizador(user_id))
    return lista_de_produtos(itens, pesquisa)


def precos_do_utilizador(user_id: str, chave: str) -> PrecosDoProduto | None:
    alias = alias_do_utilizador(user_id)
    itens = aplicar_alias(itens_do_utilizador(user_id), alias)
    # Uma chave que foi juntada a outra mostra o produto onde ficou.
    return precos_do_produto(itens, chave_final(chave.strip(), alias))
