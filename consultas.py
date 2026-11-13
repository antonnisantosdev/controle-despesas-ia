"""Consultas à base de dados partilhadas por várias partes da API (dashboard, chat, planeamento)."""

import re
import unicodedata

from postgrest.exceptions import APIError

from dashboard import gastos_por_categoria, limites_do_mes
from database import ler_todas, supabase
from limites import COLUNA_NAO_EXISTE
from models import GastoCategoria

# Quantos movimentos a procura devolve por extenso (os de maior valor); dos outros só vai a contagem.
MAX_AMOSTRA_MOVIMENTOS = 10
# As descrições vão cortadas para a IA: chegam para reconhecer o movimento e gastam menos tokens.
MAX_CARACTERES_DESCRICAO = 60
# As notas pessoais (sql/025) também vão cortadas para a IA.
MAX_CARACTERES_NOTA = 100

# O que movimentos_entre lê; a nota só existe depois da sql/025. O id vai na amostra do chat:
# é com ele que a IA aponta para uma movimentação nas propostas (o servidor volta a lê-la pelo id e pelo dono).
COLUNAS_MOVIMENTOS = "id, data, descricao, valor, categoria"
COLUNAS_MOVIMENTOS_COM_NOTA = COLUNAS_MOVIMENTOS + ", nota"


def _transacoes_entre(
    user_id: str, primeiro_mes: str, ultimo_mes: str, colunas: str = "data, categoria, valor"
) -> list[dict]:
    """As colunas pedidas das transações do primeiro ao último mês (os dois incluídos).

    ler_todas lê página a página: o Supabase corta em 1000 linhas sem avisar.
    """
    inicio, _ = limites_do_mes(primeiro_mes)
    _, fim = limites_do_mes(ultimo_mes)
    return ler_todas(
        lambda: supabase.table("transacoes")
        .select(colunas)
        .eq("user_id", user_id)
        .gte("data", inicio.isoformat())
        .lt("data", fim.isoformat())
        .order("id")
    )


def contar_transacoes(user_id: str) -> int:
    """Quantas movimentações o utilizador tem. head=True: o Supabase devolve só o número, sem linhas."""
    resposta = supabase.table("transacoes").select("id", count="exact", head=True).eq("user_id", user_id).execute()
    return resposta.count or 0


def transacao_do_utilizador(user_id: str, transacao_id: int) -> dict | None:
    """A movimentação com este id, só se for deste utilizador (senão None, como se não existisse).

    select("*"): antes da sql/025 a linha vem sem a chave nota, e quem chama sabe que as notas não existem.
    """
    resposta = (
        supabase.table("transacoes").select("*").eq("id", transacao_id).eq("user_id", user_id).limit(1).execute()
    )
    return resposta.data[0] if resposta.data else None


def gastos_do_mes(user_id: str, mes: str) -> list[GastoCategoria]:
    """Quanto o utilizador gastou em cada categoria num mês, do maior gasto para o menor."""
    return gastos_por_categoria(_transacoes_entre(user_id, mes, mes))


def gastos_de_varios_meses(user_id: str, meses: list[str]) -> dict[str, list[GastoCategoria]]:
    """Os gastos por categoria de cada mês da lista (por ordem), numa só consulta à base de dados."""
    if not meses:
        return {}
    linhas = _transacoes_entre(user_id, min(meses), max(meses))
    # Separa-se pelo início da data ("2026-10-05" -> "2026-10"); um mês sem transações fica com a lista vazia.
    return {mes: gastos_por_categoria([linha for linha in linhas if linha["data"][:7] == mes]) for mes in meses}


def movimentos_entre(
    user_id: str, primeiro_mes: str, ultimo_mes: str, categoria: str | None = None, tipo: str = "todos"
) -> list[dict]:
    """A data, a descrição, o valor, a categoria e a nota das transações do primeiro ao último mês (os dois incluídos).

    A categoria (já validada contra a lista fixa) e o tipo filtram logo na base de dados, para ler menos linhas.
    Os termos de pesquisa nunca vão para a consulta: comparam-se em Python (resumir_movimentos).
    Antes da sql/025 a coluna nota não existe: lê-se outra vez sem ela (as linhas ficam sem nota).
    """
    inicio, _ = limites_do_mes(primeiro_mes)
    _, fim = limites_do_mes(ultimo_mes)

    def consulta(colunas: str):
        q = (
            supabase.table("transacoes")
            .select(colunas)
            .eq("user_id", user_id)
            .gte("data", inicio.isoformat())
            .lt("data", fim.isoformat())
        )
        if categoria is not None:
            q = q.eq("categoria", categoria)
        if tipo == "saidas":
            q = q.lt("valor", 0)
        elif tipo == "entradas":
            q = q.gt("valor", 0)
        return q.order("id")

    try:
        return ler_todas(lambda: consulta(COLUNAS_MOVIMENTOS_COM_NOTA))
    except APIError as erro:
        if erro.code not in COLUNA_NAO_EXISTE:
            raise
    print("AVISO: coluna transacoes.nota não encontrada (sql/025); movimentos lidos sem a nota.")
    return ler_todas(lambda: consulta(COLUNAS_MOVIMENTOS))


def normalizar(texto: str) -> str:
    """Sem acentos e sem maiúsculas, para comparar: "Combustível" e "COMBUSTIVEL" ficam iguais."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(letra for letra in decomposto if not unicodedata.combining(letra)).casefold()


def _coincide(linha: dict, termos: list[str], categoria: str | None, tipo: str) -> bool:
    """Se a transação entra na procura: o tipo, a categoria (se pedida) e pelo menos um dos termos (se houver),
    na descrição ou na nota pessoal."""
    valor = linha["valor"]
    if (tipo == "saidas" and valor >= 0) or (tipo == "entradas" and valor <= 0):
        return False
    if categoria is not None and linha.get("categoria") != categoria:
        return False
    if not termos:
        return True
    # Comparação de texto em Python (não ILIKE): % e _ são letras como as outras, não curingas.
    # Cada termo tem de começar uma palavra: "Rita" encontra "MB WAY RITA S", mas não "Margarita";
    # "combust" continua a encontrar "Combustível".
    # A descrição e a nota juntas, separadas por uma mudança de linha (um termo não junta as duas).
    texto = normalizar((linha.get("descricao") or "") + "\n" + (linha.get("nota") or ""))
    return any(re.search(r"(?<!\w)" + re.escape(normalizar(termo)), texto) for termo in termos)


def _texto_curto(texto: str | None, maximo: int) -> str:
    # Espaços e mudanças de linha seguidos ficam um só espaço antes de cortar.
    return " ".join((texto or "").split())[:maximo]


def _na_amostra(linha: dict) -> dict:
    movimento = {
        "id": linha.get("id"),
        "data": linha["data"],
        "descricao": _texto_curto(linha.get("descricao"), MAX_CARACTERES_DESCRICAO),
        "valor": linha["valor"],
        "categoria": linha.get("categoria"),
    }
    # A nota só vai quando existe: menos tokens nos movimentos sem nota.
    nota = _texto_curto(linha.get("nota"), MAX_CARACTERES_NOTA)
    if nota:
        movimento["nota"] = nota
    return movimento


def resumir_movimentos(linhas: list[dict], termos: list[str], categoria: str | None, tipo: str) -> dict:
    """Os totais dos movimentos que coincidem e uma amostra dos de maior valor (em valor absoluto)."""
    encontrados = [linha for linha in linhas if _coincide(linha, termos, categoria, tipo)]
    maiores = sorted(encontrados, key=lambda linha: abs(linha["valor"]), reverse=True)[:MAX_AMOSTRA_MOVIMENTOS]
    return {
        "total_saidas": round(sum(-linha["valor"] for linha in encontrados if linha["valor"] < 0), 2),
        "total_entradas": round(sum(linha["valor"] for linha in encontrados if linha["valor"] > 0), 2),
        "n_movimentos": len(encontrados),
        "amostra": [_na_amostra(linha) for linha in maiores],
        "restantes": len(encontrados) - len(maiores),
    }
