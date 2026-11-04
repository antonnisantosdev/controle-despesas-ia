"""Minha reserva: objetivos de poupança (criar, listar, atualizar o valor poupado e apagar)."""

from database import supabase
from models import NovoObjetivo, Objetivo

COLUNAS = "id, nome, valor_alvo, data_alvo, valor_poupado"


def listar_objetivos(user_id: str) -> list[Objetivo]:
    """Os objetivos do utilizador, do prazo mais próximo para o mais distante."""
    resposta = supabase.table("objetivos").select(COLUNAS).eq("user_id", user_id).order("data_alvo").execute()
    return [Objetivo(**linha) for linha in resposta.data]


def criar_objetivo(user_id: str, novo: NovoObjetivo) -> Objetivo:
    # mode="json" converte a data_alvo em texto ("2027-07-01"), que é o que o Supabase aceita.
    dados = novo.model_dump(mode="json") | {"user_id": user_id}
    return Objetivo(**supabase.table("objetivos").insert(dados).execute().data[0])


def atualizar_poupado(user_id: str, objetivo_id: int, valor_poupado: float) -> Objetivo | None:
    """Muda o total poupado. Devolve None se o objetivo não existir ou não for deste utilizador."""
    # O .eq("user_id") é o que impede alguém de mudar um objetivo de outra pessoa só por saber o id.
    resposta = (
        supabase.table("objetivos")
        .update({"valor_poupado": valor_poupado})
        .eq("id", objetivo_id)
        .eq("user_id", user_id)
        .execute()
    )
    return Objetivo(**resposta.data[0]) if resposta.data else None


def apagar_objetivo(user_id: str, objetivo_id: int) -> bool:
    """Apaga o objetivo. Devolve False se não existir ou não for deste utilizador."""
    resposta = supabase.table("objetivos").delete().eq("id", objetivo_id).eq("user_id", user_id).execute()
    return bool(resposta.data)
