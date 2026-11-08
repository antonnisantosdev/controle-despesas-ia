"""Limite diário de perguntas ao chat, para cada utilizador não gastar demasiados créditos da IA.

O número muda-se no .env (LIMITE_PERGUNTAS_DIA), sem mexer no código.
"""

import os
from datetime import date

from fastapi import HTTPException

from database import supabase

LIMITE_PERGUNTAS_DIA = int(os.getenv("LIMITE_PERGUNTAS_DIA", "30"))


def registar_pergunta(user_id: str) -> None:
    """Conta a pergunta de hoje, ou responde 429 se o utilizador já chegou ao limite."""
    # count="exact" pede ao Supabase só o número de linhas (como um SELECT COUNT(*)), sem as trazer.
    resposta = (
        supabase.table("uso_ia")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("criado_em", date.today().isoformat())
        .execute()
    )
    feitas_hoje = resposta.count or 0

    if feitas_hoje >= LIMITE_PERGUNTAS_DIA:
        raise HTTPException(
            status_code=429,
            detail=f"Chegaste ao limite diário de {LIMITE_PERGUNTAS_DIA} perguntas. Volta amanhã!",
        )

    # Ainda pode perguntar: esta pergunta passa a contar para o total de hoje.
    supabase.table("uso_ia").insert({"user_id": user_id}).execute()


def pode_usar_ia(user_id: str) -> bool:
    """Como registar_pergunta(), mas devolve False em vez de responder 429.

    Serve para as rotas que funcionam sem IA: a movimentação grava-se sem categoria,
    e o resumo mostra um aviso, em vez de o pedido inteiro falhar.
    """
    try:
        registar_pergunta(user_id)
        return True
    except HTTPException:
        return False
