"""Consultas à base de dados partilhadas por várias partes da API (dashboard, chat, planeamento)."""

import re
import unicodedata

from dashboard import gastos_por_categoria, limites_do_mes
from database import ler_todas, supabase
from models import GastoCategoria

# Quantos movimentos a procura devolve por extenso (os de maior valor); dos outros só vai a contagem.
MAX_AMOSTRA_MOVIMENTOS = 10
# As descrições vão cortadas para a IA: chegam para reconhecer o movimento e gastam menos tokens.
MAX_CARACTERES_DESCRICAO = 60


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
    """A data, a descrição, o valor e a categoria das transações do primeiro ao último mês (os dois incluídos).

    A categoria (já validada contra a lista fixa) e o tipo filtram logo na base de dados, para ler menos linhas.
    Os termos de pesquisa nunca vão para a consulta: comparam-se em Python (resumir_movimentos).
    """
    inicio, _ = limites_do_mes(primeiro_mes)
    _, fim = limites_do_mes(ultimo_mes)

    def consulta():
        q = (
            supabase.table("transacoes")
            .select("data, descricao, valor, categoria")
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

    return ler_todas(consulta)


def normalizar(texto: str) -> str:
    """Sem acentos e sem maiúsculas, para comparar: "Combustível" e "COMBUSTIVEL" ficam iguais."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(letra for letra in decomposto if not unicodedata.combining(letra)).casefold()


def _coincide(linha: dict, termos: list[str], categoria: str | None, tipo: str) -> bool:
    """Se a transação entra na procura: o tipo, a categoria (se pedida) e pelo menos um dos termos (se houver)."""
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
    descricao = normalizar(linha.get("descricao") or "")
    return any(re.search(r"(?<!\w)" + re.escape(normalizar(termo)), descricao) for termo in termos)


def _na_amostra(linha: dict) -> dict:
    # Espaços e mudanças de linha seguidos ficam um só espaço antes de cortar.
    descricao = " ".join((linha.get("descricao") or "").split())[:MAX_CARACTERES_DESCRICAO]
    return {"data": linha["data"], "descricao": descricao, "valor": linha["valor"], "categoria": linha.get("categoria")}


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
