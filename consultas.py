"""Consultas à base de dados partilhadas por várias partes da API (dashboard, chat, planeamento)."""

from dashboard import gastos_por_categoria, limites_do_mes
from database import supabase
from models import GastoCategoria


def gastos_do_mes(user_id: str, mes: str) -> list[GastoCategoria]:
    """Quanto o utilizador gastou em cada categoria num mês, do maior gasto para o menor."""
    inicio, fim = limites_do_mes(mes)
    resposta = (
        supabase.table("transacoes")
        .select("categoria, valor")
        .eq("user_id", user_id)
        .gte("data", inicio.isoformat())
        .lt("data", fim.isoformat())
        .execute()
    )
    return gastos_por_categoria(resposta.data)
