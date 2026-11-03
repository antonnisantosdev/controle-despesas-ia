"""Recolhe os números de um mês (e do anterior) para a IA escrever o resumo mensal.

Aqui não há tool use: sabemos à partida que dados são precisos, por isso vamos
buscá-los todos de uma vez e a IA só tem de os explicar.
"""

from dashboard import gastos_por_categoria, limites_do_mes, mes_anterior, resumo_mensal
from database import supabase


def recolher_dados(user_id: str, mes: str) -> dict:
    anterior = mes_anterior(mes)
    inicio, _ = limites_do_mes(anterior)
    _, fim = limites_do_mes(mes)

    # Uma só consulta para os dois meses; depois separa-se pelo início da data ("2026-10-...").
    linhas = (
        supabase.table("transacoes")
        .select("data, descricao, valor, categoria")
        .eq("user_id", user_id)
        .gte("data", inicio.isoformat())
        .lt("data", fim.isoformat())
        .execute()
    ).data
    deste_mes = [linha for linha in linhas if linha["data"].startswith(mes)]
    do_anterior = [linha for linha in linhas if linha["data"].startswith(anterior)]

    # As 3 despesas maiores do mês (os valores mais negativos), para a IA explicar picos.
    maiores = sorted((linha for linha in deste_mes if linha["valor"] < 0), key=lambda linha: linha["valor"])[:3]

    return {
        "mes": mes,
        "mes_anterior": anterior,
        "transacoes_no_mes": len(deste_mes),
        "totais": [total.model_dump() for total in resumo_mensal(linhas)],
        "gastos_por_categoria": {
            mes: [gasto.model_dump() for gasto in gastos_por_categoria(deste_mes)],
            anterior: [gasto.model_dump() for gasto in gastos_por_categoria(do_anterior)],
        },
        "maiores_despesas": maiores,
    }
