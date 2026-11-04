"""Minhas compras: gravar um talão revisto pelo utilizador (a transação, a compra e os produtos)."""

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

    return Compra(**compra, itens=nova.itens)
