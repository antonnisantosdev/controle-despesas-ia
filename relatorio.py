"""Resumo anual das finanças (GET /relatorio, GET /relatorio/csv e POST /relatorio/resumo-ia).

Só contas sobre as movimentações já gravadas: nada fiscal (não é IRS nem e-fatura).
Lê numa só consulta o ano pedido e o anterior (para a comparação), sempre filtrado pelo user_id do token.
As saídas vão em positivo (34.2 e não -34.2), como no dashboard.
"""

import csv
import io
from datetime import date

from consultas import movimentos_entre
from database import supabase
from models import (
    CategoriaComparada,
    CategoriaRelatorio,
    ComparacaoAno,
    MesRelatorio,
    ObjetivoRelatorio,
    RecorrenteAno,
    RelatorioAnual,
    SaidaRelatorio,
    TotaisAno,
)
from objetivos import listar_objetivos
from recorrentes import agrupar_despesas, recorrentes_dos_grupos

# Textos do contador (não mudar sem falar com ele).
TITULO = "Resumo anual das tuas finanças – {ano}"
AVISO = (
    "Resumo pessoal feito a partir dos extratos e movimentos que registaste, com categorias atribuídas "
    "automaticamente (podem ter erros). Não é um documento fiscal nem aconselhamento financeiro e não "
    "substitui o e-fatura nem um contabilista."
)
NOTA_CATEGORIAS = "Categorias da app, não correspondem às do e-fatura."

# Os mesmos textos por país onde a pessoa vive (pais da conta). O título BR é o do frontend (textosRelatorio.ts);
# o aviso e a nota BR são TEXTO NOVO, por rever pelo copywriter e pelo contador.
TEXTOS_POR_PAIS = {
    "PT": {"titulo": TITULO, "aviso": AVISO, "nota_categorias": NOTA_CATEGORIAS},
    "BR": {
        "titulo": "Resumo anual das suas finanças – {ano}",
        "aviso": (
            "Resumo pessoal feito a partir dos extratos e movimentações que você registrou, com categorias "
            "atribuídas automaticamente (podem ter erros). Não é um documento fiscal nem consultoria financeira "
            "e não substitui os documentos oficiais nem a orientação de um contador."
        ),
        "nota_categorias": "Categorias da app, não correspondem às categorias fiscais.",
    },
}

# Ano mais antigo aceite no relatório.
PRIMEIRO_ANO = 2000
MAX_MAIORES_SAIDAS = 10
MAX_CARACTERES_DESCRICAO = 100

# O que se mostra em vez do nome guardado na base de dados. O contador pediu "Entradas", nunca "rendimento".
ETIQUETAS = {"rendimento": "Entradas"}
# No BR, os rótulos das categorias do frontend (lib/opcoes.ts, ROTULOS_CATEGORIAS.BR), com maiúscula.
ETIQUETAS_POR_PAIS = {
    "PT": ETIQUETAS,
    "BR": {
        "casa": "Moradia",
        "telecomunicações": "Telefone e internet",
        "rendimento": "Receitas",
        "levantamentos": "Saques",
        "compras extra": "Compras extras",
    },
}
SEM_CATEGORIA = "sem categoria"


def etiqueta(categoria: str | None, pais: str = "PT") -> str:
    """O nome da categoria para mostrar no país dado: em PT "rendimento" passa a "Entradas"; sem categoria,
    "sem categoria". A chave guardada (categoria) nunca muda."""
    if not categoria:
        return SEM_CATEGORIA
    # Com maiúscula ("Casa"), como na app: o CSV mostra a etiqueta tal e qual.
    etiquetas = ETIQUETAS_POR_PAIS.get(pais, ETIQUETAS)
    return etiquetas.get(categoria, categoria[:1].upper() + categoria[1:])


def ano_valido(ano: int, hoje: date) -> bool:
    """De PRIMEIRO_ANO até ao ano de hoje (não há relatório de anos que ainda não começaram)."""
    return PRIMEIRO_ANO <= ano <= hoje.year


def meses_do_relatorio(ano: int, hoje: date) -> list[str]:
    """Os meses que o relatório conta: o ano inteiro, ou até ao mês atual se for o ano corrente."""
    ultimo = hoje.month if ano == hoje.year else 12
    return [f"{ano}-{mes:02d}" for mes in range(1, ultimo + 1)]


def _totais(linhas: list[dict]) -> TotaisAno:
    entradas = sum(linha["valor"] for linha in linhas if linha["valor"] > 0)
    saidas = sum(-linha["valor"] for linha in linhas if linha["valor"] < 0)
    return TotaisAno(entradas=round(entradas, 2), saidas=round(saidas, 2), saldo=round(entradas - saidas, 2))


def _saidas_por_categoria(linhas: list[dict]) -> dict[str, float]:
    """Soma das saídas de cada categoria (a chave é o nome da base de dados, ou "" sem categoria)."""
    totais: dict[str, float] = {}
    for linha in linhas:
        if linha["valor"] < 0:
            chave = linha.get("categoria") or ""
            totais[chave] = totais.get(chave, 0) - linha["valor"]
    return totais


def _mes_a_mes(linhas: list[dict], meses: list[str]) -> list[MesRelatorio]:
    resultado = []
    for mes in meses:
        do_mes = [linha for linha in linhas if linha["data"][:7] == mes]
        totais = _totais(do_mes)
        resultado.append(MesRelatorio(mes=mes, **totais.model_dump(), com_dados=bool(do_mes)))
    return resultado


def _categorias(linhas: list[dict], total_saidas: float, pais: str) -> list[CategoriaRelatorio]:
    """As saídas por categoria, da maior para a menor, com a % das saídas do ano."""
    totais = _saidas_por_categoria(linhas)
    categorias = [
        CategoriaRelatorio(
            categoria=categoria or SEM_CATEGORIA,
            etiqueta=etiqueta(categoria, pais),
            total=round(total, 2),
            percentagem=round(total / total_saidas * 100, 1) if total_saidas else 0.0,
        )
        for categoria, total in totais.items()
    ]
    return sorted(categorias, key=lambda c: c.total, reverse=True)


def _comparacao(
    atuais: list[dict], anteriores: list[dict], ano: int, meses: list[str], pais: str
) -> ComparacaoAno | None:
    """O ano anterior nos mesmos meses (janeiro a novembro, se o relatório for até novembro).

    None se o ano anterior não tiver movimentações nesses meses: não se compara com zeros inventados.
    """
    meses_comparados = [mes[5:] for mes in meses]
    anteriores = [linha for linha in anteriores if linha["data"][5:7] in meses_comparados]
    if not anteriores:
        return None
    agora, antes = _saidas_por_categoria(atuais), _saidas_por_categoria(anteriores)
    categorias = [
        CategoriaComparada(
            categoria=categoria or SEM_CATEGORIA,
            etiqueta=etiqueta(categoria, pais),
            total=round(agora.get(categoria, 0), 2),
            total_anterior=round(antes.get(categoria, 0), 2),
            diferenca=round(agora.get(categoria, 0) - antes.get(categoria, 0), 2),
        )
        for categoria in set(agora) | set(antes)
    ]
    return ComparacaoAno(
        ano=ano - 1,
        meses_comparados=meses_comparados,
        meses_com_dados=len({linha["data"][5:7] for linha in anteriores}),
        totais=_totais(anteriores),
        categorias=sorted(categorias, key=lambda c: c.total, reverse=True),
    )


def _descricao_curta(descricao: str | None) -> str:
    # Espaços e mudanças de linha seguidos ficam um só espaço antes de cortar.
    return " ".join((descricao or "").split())[:MAX_CARACTERES_DESCRICAO]


def _maiores_saidas(linhas: list[dict], pais: str) -> list[SaidaRelatorio]:
    saidas = sorted((l for l in linhas if l["valor"] < 0), key=lambda l: (l["valor"], l["data"]))
    return [
        SaidaRelatorio(
            data=date.fromisoformat(linha["data"][:10]),
            descricao=_descricao_curta(linha.get("descricao")),
            valor=round(-linha["valor"], 2),
            categoria=linha.get("categoria"),
            etiqueta=etiqueta(linha.get("categoria"), pais),
            nota=linha.get("nota"),  # None antes da sql/025 ou sem nota
        )
        for linha in saidas[:MAX_MAIORES_SAIDAS]
    ]


def _recorrentes(linhas: list[dict], ano: int, hoje: date, pais: str) -> list[RecorrenteAno]:
    """Os pagamentos que se repetem (recorrentes.py) com o que somaram no ano.

    A deteção é a mesma do Planeamento, sobre as movimentações do ano: num ano que já acabou, entram
    os que continuavam ativos em dezembro (um cancelado a meio do ano não aparece).
    """
    referencia = hoje if ano == hoje.year else date(ano, 12, 31)
    # Uma só passagem pelas linhas: cada descrição normaliza-se uma vez e os pagamentos somam-se pelo grupo.
    grupos = agrupar_despesas(linhas)
    resultado = []
    for chave, recorrente in recorrentes_dos_grupos(grupos, referencia):
        pagamentos = grupos[chave]
        resultado.append(
            RecorrenteAno(
                descricao=_descricao_curta(recorrente.descricao),
                categoria=recorrente.categoria,
                etiqueta=etiqueta(recorrente.categoria, pais),
                valor_mensal=recorrente.valor_mensal,
                pagamentos_no_ano=len(pagamentos),
                total_no_ano=round(sum(-linha["valor"] for linha in pagamentos), 2),
            )
        )
    return sorted(resultado, key=lambda r: r.total_no_ano, reverse=True)


def _objetivos(user_id: str) -> list[ObjetivoRelatorio]:
    """Os objetivos de poupança como estão hoje (a base de dados não guarda o histórico)."""
    return [
        ObjetivoRelatorio(
            nome=o.nome,
            valor_alvo=o.valor_alvo,
            valor_poupado=o.valor_poupado,
            data_alvo=o.data_alvo,
            percentagem=round(o.valor_poupado / o.valor_alvo * 100, 1) if o.valor_alvo else 0.0,
        )
        for o in listar_objetivos(user_id)
    ]


def montar_relatorio(
    ano: int, linhas: list[dict], objetivos: list[ObjetivoRelatorio], hoje: date, pais: str = "PT"
) -> RelatorioAnual:
    """O relatório a partir das movimentações já lidas (do ano e do anterior). Sem base de dados: fácil de testar.

    pais: onde a pessoa vive (título, aviso e etiquetas das categorias nesse país).
    """
    textos = TEXTOS_POR_PAIS.get(pais, TEXTOS_POR_PAIS["PT"])
    meses = meses_do_relatorio(ano, hoje)
    do_ano = [linha for linha in linhas if linha["data"][:7] in meses]
    do_anterior = [linha for linha in linhas if linha["data"][:4] == str(ano - 1)]
    mes_a_mes = _mes_a_mes(do_ano, meses)
    sem_dados = [m.mes for m in mes_a_mes if not m.com_dados]
    totais = _totais(do_ano)
    return RelatorioAnual(
        ano=ano,
        titulo=textos["titulo"].format(ano=ano),
        aviso=textos["aviso"],
        nota_categorias=textos["nota_categorias"],
        ate_mes=meses[-1],
        ano_incompleto=ano == hoje.year or bool(sem_dados),
        meses_sem_dados=sem_dados,
        totais=totais,
        meses=mes_a_mes,
        categorias=_categorias(do_ano, totais.saidas, pais),
        comparacao=_comparacao(do_ano, do_anterior, ano, meses, pais),
        maiores_saidas=_maiores_saidas(do_ano, pais),
        recorrentes=_recorrentes(do_ano, ano, hoje, pais),
        objetivos=objetivos,
    )


def primeiro_ano_com_dados(user_id: str) -> int | None:
    """O ano da movimentação mais antiga deste utilizador (1 linha só), ou None. Uma falha não estraga o relatório."""
    try:
        resposta = (
            supabase.table("transacoes").select("data").eq("user_id", user_id).order("data").limit(1).execute()
        )
        linhas = resposta.data or []
        return int(str(linhas[0]["data"])[:4]) if linhas else None
    except Exception as erro:
        print(f"AVISO: não foi possível ler o primeiro ano com movimentações ({getattr(erro, 'code', None) or type(erro).__name__}).")
        return None


def relatorio_do_ano(user_id: str, ano: int, hoje: date, pais: str = "PT") -> RelatorioAnual:
    """Lê as movimentações do ano e do anterior (página a página, só deste utilizador) e monta o relatório."""
    linhas = movimentos_entre(user_id, f"{ano - 1}-01", f"{ano}-12")
    relatorio = montar_relatorio(ano, linhas, _objetivos(user_id), hoje, pais)
    relatorio.primeiro_ano = primeiro_ano_com_dados(user_id)
    return relatorio


# --- Para a IA (resumo do ano) ---


def dados_para_ia(relatorio: RelatorioAnual) -> dict:
    """Só números já calculados e nomes de categorias: nunca descrições nem notas de movimentos, nem nomes de objetivos."""
    comparacao = relatorio.comparacao
    return {
        "ano": relatorio.ano,
        "ate_mes": relatorio.ate_mes,
        "ano_incompleto": relatorio.ano_incompleto,
        "meses_sem_dados": relatorio.meses_sem_dados,
        "totais": relatorio.totais.model_dump(),
        "mes_a_mes": [m.model_dump(exclude={"com_dados"}) for m in relatorio.meses if m.com_dados],
        "saidas_por_categoria": [
            {"categoria": c.etiqueta, "total": c.total, "percentagem": c.percentagem} for c in relatorio.categorias
        ],
        "ano_anterior_mesmos_meses": (
            {
                "ano": comparacao.ano,
                "meses_com_dados": comparacao.meses_com_dados,
                "totais": comparacao.totais.model_dump(),
            }
            if comparacao
            else None
        ),
        "maiores_saidas": [{"categoria": s.etiqueta, "valor": s.valor, "mes": s.data.isoformat()[:7]} for s in relatorio.maiores_saidas],
        "pagamentos_que_se_repetem": {
            "quantos": len(relatorio.recorrentes),
            "total_no_ano": round(sum(r.total_no_ano for r in relatorio.recorrentes), 2),
        },
        "objetivos_de_poupanca": {
            "quantos": len(relatorio.objetivos),
            "valor_alvo_total": round(sum(o.valor_alvo for o in relatorio.objetivos), 2),
            "valor_poupado_total": round(sum(o.valor_poupado for o in relatorio.objetivos), 2),
        },
    }


# --- CSV para o Excel em português ---

# Uma célula que começa por um destes caracteres o Excel pode ler como fórmula (CSV injection).
INICIOS_PERIGOSOS = ("=", "+", "-", "@", "\t", "\r", "\n")


def texto_seguro(texto: str) -> str:
    """Põe um apóstrofo antes de um texto que o Excel leria como fórmula ("=HYPERLINK(...)" -> "'=HYPERLINK(...)")."""
    return "'" + texto if texto.startswith(INICIOS_PERIGOSOS) else texto


def numero_pt(valor: float) -> str:
    """1234.5 -> "1234,50": vírgula decimal e sem separador de milhares, que o Excel em português lê como número."""
    return f"{valor:.2f}".replace(".", ",")


def _celula(valor) -> str:
    """Números com vírgula decimal (gerados aqui, nunca precisam de apóstrofo); textos protegidos contra fórmulas."""
    if valor is None:
        return ""
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return numero_pt(float(valor))
    return texto_seguro(str(valor))


NOMES_DOS_MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)  # fmt: skip


def nome_do_mes(mes: str) -> str:
    """ "2026-03" -> "março de 2026". Em texto, para o Excel não o trocar por uma data."""
    return f"{NOMES_DOS_MESES[int(mes[5:7]) - 1]} de {mes[:4]}"


# Os rótulos do CSV que mudam no BR (o resto é igual nos dois países). TEXTO NOVO (BR).
ROTULOS_CSV = {
    "PT": {
        "meses_sem": "Meses sem movimentos",
        "objetivos": "Objetivos de poupança (hoje)",
        "objetivo": "Objetivo",
        "poupado": "Poupado",
        "percentagem_poupada": "% poupada",
    },
    "BR": {
        "meses_sem": "Meses sem movimentações",
        "objetivos": "Metas de economia (hoje)",
        "objetivo": "Meta",
        "poupado": "Guardado",
        "percentagem_poupada": "% guardada",
    },
}
SIMBOLOS_MOEDA = {"EUR": "€", "BRL": "R$"}


def relatorio_em_csv(relatorio: RelatorioAnual, pais: str = "PT", moeda: str = "EUR") -> bytes:
    """O relatório em CSV: várias tabelas separadas por uma linha em branco, separador ";", UTF-8 com BOM.

    Uma só folha com tabelas por baixo umas das outras abre direto no Excel em português (o BOM diz-lhe
    que é UTF-8, senão os acentos saíam estragados; o ";" é o separador de listas do Excel PT e BR).
    pais: a língua dos rótulos; moeda: o símbolo nos cabeçalhos ("Valor (€)" ou "Valor (R$)").
    """
    rotulos = ROTULOS_CSV.get(pais, ROTULOS_CSV["PT"])
    m = SIMBOLOS_MOEDA.get(moeda, "€")
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")

    def linha(*celulas):
        escritor.writerow([_celula(c) for c in celulas])

    linha(relatorio.titulo)
    linha(relatorio.aviso)
    if relatorio.ano_incompleto:
        sem_dados = (
            f" {rotulos['meses_sem']}: {', '.join(relatorio.meses_sem_dados)}." if relatorio.meses_sem_dados else ""
        )
        linha(f"Ano incompleto: dados até {nome_do_mes(relatorio.ate_mes)}.{sem_dados}")
    escritor.writerow([])

    linha("Resumo", f"Valor ({m})")
    linha("Entradas", relatorio.totais.entradas)
    linha("Saídas", relatorio.totais.saidas)
    linha("Saldo", relatorio.totais.saldo)
    escritor.writerow([])

    linha("Mês", f"Entradas ({m})", f"Saídas ({m})", f"Saldo ({m})")
    for mes in relatorio.meses:
        linha(nome_do_mes(mes.mes), mes.entradas, mes.saidas, mes.saldo)
    escritor.writerow([])

    linha("Gastos por categoria")
    linha(relatorio.nota_categorias)
    linha("Categoria", f"Total ({m})", "% das saídas")
    for categoria in relatorio.categorias:
        linha(categoria.etiqueta, categoria.total, categoria.percentagem)
    escritor.writerow([])

    if relatorio.comparacao:
        comp = relatorio.comparacao
        linha(f"Comparação com {comp.ano} (meses {comp.meses_comparados[0]} a {comp.meses_comparados[-1]})")
        linha("", str(relatorio.ano), str(comp.ano), f"Diferença ({m})")
        linha("Entradas", relatorio.totais.entradas, comp.totais.entradas, relatorio.totais.entradas - comp.totais.entradas)
        linha("Saídas", relatorio.totais.saidas, comp.totais.saidas, relatorio.totais.saidas - comp.totais.saidas)
        for categoria in comp.categorias:
            linha(categoria.etiqueta, categoria.total, categoria.total_anterior, categoria.diferenca)
        escritor.writerow([])

    linha(f"{MAX_MAIORES_SAIDAS} maiores saídas")
    linha("Data", "Descrição", f"Valor ({m})", "Categoria", "Nota")
    for saida_ in relatorio.maiores_saidas:
        # A nota pessoal vai inteira (máx. 300), numa só linha e protegida contra fórmulas como os outros textos.
        nota = " ".join((saida_.nota or "").split())
        linha(saida_.data.isoformat(), _descricao_curta(saida_.descricao), saida_.valor, saida_.etiqueta, nota)
    escritor.writerow([])

    linha("Pagamentos que se repetem")
    linha("Descrição", "Categoria", "Pagamentos no ano", f"Total no ano ({m})")
    for recorrente in relatorio.recorrentes:
        linha(_descricao_curta(recorrente.descricao), recorrente.etiqueta, str(recorrente.pagamentos_no_ano), recorrente.total_no_ano)
    escritor.writerow([])

    linha(rotulos["objetivos"])
    linha(rotulos["objetivo"], f"Valor alvo ({m})", f"{rotulos['poupado']} ({m})", "Data alvo", rotulos["percentagem_poupada"])
    for objetivo in relatorio.objetivos:
        linha(_descricao_curta(objetivo.nome), objetivo.valor_alvo, objetivo.valor_poupado, objetivo.data_alvo.isoformat(), objetivo.percentagem)

    # "utf-8-sig" escreve o BOM no início.
    return saida.getvalue().encode("utf-8-sig")
