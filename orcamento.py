"""Planeamento: orçamento mensal por categoria e quanto já se gastou de cada um."""

from datetime import datetime, timezone

from consultas import gastos_do_mes
from database import supabase
from models import GastoCategoria, LinhaOrcamento


def limites_do_utilizador(user_id: str) -> dict[str, float]:
    """Os orçamentos guardados, como {"restaurantes": 50.0, "alimentação": 200.0}."""
    resposta = supabase.table("orcamentos").select("categoria, limite").eq("user_id", user_id).execute()
    return {linha["categoria"]: float(linha["limite"]) for linha in resposta.data}


def juntar(limites: dict[str, float], gastos: list[GastoCategoria]) -> list[LinhaOrcamento]:
    """Uma linha por categoria que tem orçamento, gastos no mês, ou as duas coisas."""
    categorias = set(limites.keys()) | {g.categoria for g in gastos}
    linhas = []
    for categoria in categorias:
        limite = limites.get(categoria)
        gasto = next((g.total for g in gastos if g.categoria == categoria), 0.0)
        linhas.append(LinhaOrcamento(categoria=categoria, limite=limite, gasto=gasto))
    return linhas


def planeamento_do_mes(user_id: str, mes: str) -> list[LinhaOrcamento]:
    linhas = juntar(limites_do_utilizador(user_id), gastos_do_mes(user_id, mes))
    # As categorias com orçamento primeiro (as mais "gastas" em primeiro), depois as que só têm gastos.
    return sorted(linhas, key=lambda linha: (linha.limite is None, -linha.gasto))


def guardar_limite(user_id: str, categoria: str, limite: float) -> None:
    # upsert: se a categoria já tinha orçamento, substitui; senão, cria.
    supabase.table("orcamentos").upsert(
        {
            "user_id": user_id,
            "categoria": categoria,
            "limite": limite,
            "atualizado_em": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="user_id,categoria",
    ).execute()
