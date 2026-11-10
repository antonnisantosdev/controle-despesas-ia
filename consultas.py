"""Consultas à base de dados partilhadas por várias partes da API (dashboard, chat, planeamento)."""

from dashboard import gastos_por_categoria, limites_do_mes
from database import ler_todas, supabase
from models import GastoCategoria


def _transacoes_entre(user_id: str, primeiro_mes: str, ultimo_mes: str) -> list[dict]:
    """A categoria, o valor e a data das transações do primeiro ao último mês (os dois incluídos).

    ler_todas lê página a página: o Supabase corta em 1000 linhas sem avisar.
    """
    inicio, _ = limites_do_mes(primeiro_mes)
    _, fim = limites_do_mes(ultimo_mes)
    return ler_todas(
        lambda: supabase.table("transacoes")
        .select("data, categoria, valor")
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
