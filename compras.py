"""Minhas compras: gravar um talão revisto pelo utilizador (a transação, a compra e os produtos) e listá-los."""

from database import supabase
from models import Compra, NovaCompra


def gravar_compra(user_id: str, nova: NovaCompra) -> Compra:
    """Grava 3 coisas, por esta ordem: a transação (com o total), a compra e os produtos."""
    # 1. A transação: é ela que entra no dashboard, no Planeamento e no chat, como qualquer outra despesa.
    transacao = {
        "data": nova.data.isoformat(),
        "descricao": f"Talão: {nova.loja}",
        "valor": -nova.total,  # é uma despesa: na tabela, as despesas são negativas
        "categoria": nova.categoria,
        "metodo_pagamento": nova.metodo_pagamento,
        "user_id": user_id,
    }
    transacao_id = supabase.table("transacoes").insert(transacao).execute().data[0]["id"]

    try:
        # 2. A compra, ligada à transação.
        compra = (
            supabase.table("compras")
            .insert(
                {
                    "user_id": user_id,
                    "transacao_id": transacao_id,
                    "loja": nova.loja,
                    "data": nova.data.isoformat(),
                    "total": nova.total,
                }
            )
            .execute()
            .data[0]
        )
        # 3. Os produtos, todos num só pedido (uma lista de linhas, como na importação do CSV).
        itens = [item.model_dump() | {"compra_id": compra["id"]} for item in nova.itens]
        supabase.table("compra_itens").insert(itens).execute()
    except Exception:
        # O Supabase não junta os 3 inserts numa só operação. Se o 2 ou o 3 falhar, apaga-se a transação,
        # e o ON DELETE CASCADE leva a compra e os produtos: não fica nada a meio.
        supabase.table("transacoes").delete().eq("id", transacao_id).execute()
        raise

    # model_dump: o Pydantic 2 não aceita um ItemCompra onde a Compra espera um ItemTalao (dava 500 depois de gravar).
    return Compra(**compra, itens=[item.model_dump() for item in nova.itens])


def listar_compras(user_id: str) -> list[Compra]:
    """As compras do utilizador, das mais recentes para as mais antigas, cada uma com os seus produtos."""
    # "compra_itens(...)" dentro do select: o Supabase segue a chave estrangeira compra_id e traz os
    # produtos de cada compra no mesmo pedido (como um JOIN, mas já arrumado por compra).
    resposta = (
        supabase.table("compras")
        .select("id, transacao_id, loja, data, total, compra_itens(descricao, quantidade, preco)")
        .eq("user_id", user_id)
        .order("data", desc=True)
        .order("id", desc=True)
        .execute()
    )
    return [Compra(**linha, itens=linha["compra_itens"]) for linha in resposta.data]
