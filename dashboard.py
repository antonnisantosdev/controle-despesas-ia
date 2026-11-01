"""Contas do dashboard: recebem transações já lidas da base de dados e devolvem totais.

Não falam com o Supabase nem com o FastAPI, por isso são fáceis de testar
(e o chat da Fase 5 vai poder reaproveitá-las).
"""

from datetime import date

from models import GastoCategoria


def limites_do_mes(mes: str) -> tuple[date, date]:
    """Para "2026-10" devolve (1 de outubro, 1 de novembro): o fim fica de fora."""
    if not mes or len(mes) != 7 or mes[4] != "-":
        raise ValueError(f"mes inválido: {mes}")
    inicio = date.fromisoformat(f"{mes}-01")
    if inicio.month == 12:
        fim = date(inicio.year + 1, 1, 1)
    else:
        fim = date(inicio.year, inicio.month + 1, 1)
    return inicio, fim


def gastos_por_categoria(transacoes: list[dict]) -> list[GastoCategoria]:
    """Soma as despesas de cada categoria, da maior para a menor."""
    totais: dict[str, float] = {}

    for transacao in transacoes:
        valor = transacao["valor"]
        # Só despesas: o salário e o dinheiro recebido não são gastos.
        if valor >= 0:
            continue
        categoria = transacao["categoria"] or "sem categoria"
        # abs() tira o sinal: -34.2 passa a 34.2, que é como um gráfico de gastos se lê.
        totais[categoria] = totais.get(categoria, 0) + abs(valor)

    gastos = [GastoCategoria(categoria=categoria, total=round(total, 2)) for categoria, total in totais.items()]
    return sorted(gastos, key=lambda gasto: gasto.total, reverse=True)
