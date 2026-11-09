"""Planeamento: orçamento mensal por categoria e quanto já se gastou de cada um."""

from datetime import datetime, timezone

from consultas import gastos_do_mes
from dashboard import mes_anterior
from database import supabase
from models import AlertaOrcamento, GastoCategoria, LinhaOrcamento

# A partir de que parte do orçamento gasta aparece o alerta "Estás perto do orçamento do mês".
LIMIAR_ALERTA_ORCAMENTO = 0.9


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


def alertas_de_orcamento(linhas: list[LinhaOrcamento]) -> list[AlertaOrcamento]:
    """As categorias com orçamento em que o gasto já chegou a 90% ("perto") ou a 100% ("atingido").

    Só contas, sem IA. Primeiro as que passaram o orçamento, depois as mais perto do limite.
    """
    alertas = []
    for linha in linhas:
        if not linha.limite:  # sem orçamento (None) ou 0: não há com que comparar
            continue
        if linha.gasto >= linha.limite:
            nivel = "atingido"
        elif linha.gasto >= linha.limite * LIMIAR_ALERTA_ORCAMENTO:
            nivel = "perto"
        else:
            continue
        alertas.append(AlertaOrcamento(categoria=linha.categoria, gasto=linha.gasto, limite=linha.limite, nivel=nivel))
    return sorted(alertas, key=lambda alerta: (alerta.nivel != "atingido", -alerta.gasto / alerta.limite))


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


def resumir_historico(gastos_por_mes: dict[str, list[GastoCategoria]]) -> dict[str, dict]:
    """Para cada categoria: o gasto de cada mês (0 se não houve), a média e o máximo.

    Exemplo de entrada: {"2026-10": [GastoCategoria(categoria="casa", total=450.0)], "2026-11": [...]}
    Exemplo de saída:   {"casa": {"meses": {"2026-10": 450.0, "2026-11": 42.1}, "media": 246.05, "maximo": 450.0}}
    """
    categorias = set(g.categoria for gastos in gastos_por_mes.values() for g in gastos)

    resumo = {}
    for categoria in categorias:
        # O gasto desta categoria em cada mês; 0 nos meses em que não houve nenhum.
        meses = {
            mes: next((g.total for g in gastos if g.categoria == categoria), 0.0)
            for mes, gastos in gastos_por_mes.items()
        }
        valores = list(meses.values())
        resumo[categoria] = {
            "meses": meses,
            # A dividir por todos os meses (incluindo os de 0): é isso que mostra se um gasto foi pontual.
            "media": round(sum(valores) / len(valores), 2),
            "maximo": max(valores),
        }
    return resumo


def historico_para_sugestao(user_id: str, mes: str, quantos_meses: int = 3) -> dict[str, dict]:
    """Os gastos dos últimos meses (o mês escolhido e os anteriores), já resumidos para a IA."""
    meses = [mes]
    while len(meses) < quantos_meses:
        meses.append(mes_anterior(meses[-1]))
    return resumir_historico({m: gastos_do_mes(user_id, m) for m in sorted(meses)})
