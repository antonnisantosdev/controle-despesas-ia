"""Minha reserva: objetivos de poupança (criar, listar, atualizar o valor poupado e apagar)
e as contas do plano de poupança, que a IA depois avalia e explica.
"""

from datetime import date

from dashboard import mes_anterior, resumo_mensal
from database import ler_todas, supabase
from models import NovoObjetivo, Objetivo
from orcamento import historico_para_sugestao

COLUNAS = "id, nome, valor_alvo, data_alvo, valor_poupado"


def listar_objetivos(user_id: str) -> list[Objetivo]:
    """Os objetivos do utilizador, do prazo mais próximo para o mais distante."""
    resposta = supabase.table("objetivos").select(COLUNAS).eq("user_id", user_id).order("data_alvo").execute()
    return [Objetivo(**linha) for linha in resposta.data]


def obter_objetivo(user_id: str, objetivo_id: int) -> Objetivo | None:
    """Um objetivo deste utilizador, ou None se não existir (ou for de outra pessoa)."""
    resposta = (
        supabase.table("objetivos").select(COLUNAS).eq("id", objetivo_id).eq("user_id", user_id).execute()
    )
    return Objetivo(**resposta.data[0]) if resposta.data else None


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


# ---------- Contas do plano de poupança (sem IA) ----------

# Quantos meses completos entram no saldo médio. O mês atual fica de fora: ainda não acabou,
# e um mês a meio (com o salário mas sem as despesas todas) faria a poupança parecer maior.
MESES_SALDO_MEDIO = 3

# Dos objetivos só se compromete 80% do saldo médio: os outros 20% são folga para imprevistos.
PARTE_DO_SALDO_PARA_POUPAR = 0.8


def meses_ate(data_alvo: date, hoje: date) -> int:
    """Quantos meses de poupança faltam até à data_alvo, a contar com o mês de hoje.

    Devolve 0 se a data_alvo já passou (o prazo terminou: não há meses para poupar).
    """
    if data_alvo < hoje:
        return 0
    meses = (data_alvo.year - hoje.year) * 12 + (data_alvo.month - hoje.month) + 1
    
    return meses


def saldo_medio(user_id: str, hoje: date) -> tuple[float, list[str]]:
    """Média de (receitas - despesas) nos últimos meses completos, e quais foram esses meses."""
    linhas = ler_todas(lambda: supabase.table("transacoes").select("data, valor").eq("user_id", user_id).order("id"))
    mes_atual = hoje.strftime("%Y-%m")
    completos = [m for m in resumo_mensal(linhas) if m.mes < mes_atual][-MESES_SALDO_MEDIO:]
    if not completos:
        return 0.0, []
    media = sum(m.receitas - m.despesas for m in completos) / len(completos)
    return round(media, 2), [m.mes for m in completos]


def necessario_por_mes(objetivo: Objetivo, hoje: date) -> float | None:
    """Quanto é preciso poupar por mês para chegar ao alvo a tempo. None se o prazo já terminou."""
    falta = max(objetivo.valor_alvo - objetivo.valor_poupado, 0)
    meses = meses_ate(objetivo.data_alvo, hoje)
    if meses == 0:
        return None
    return round(falta / meses, 2)


def dados_do_plano(user_id: str, objetivo: Objetivo, hoje: date) -> dict:
    """Tudo o que a IA precisa para avaliar o objetivo, já calculado. A IA não faz contas, só as explica."""
    saldo, meses_usados = saldo_medio(user_id, hoje)

    # Os outros objetivos também precisam de dinheiro todos os meses: competem pelo mesmo saldo.
    outros = [o for o in listar_objetivos(user_id) if o.id != objetivo.id]
    outros_por_mes = sum(necessario_por_mes(o, hoje) or 0 for o in outros)

    # Gastos médios por categoria nos mesmos meses do saldo: é onde a IA vai procurar o que cortar.
    gastos = historico_para_sugestao(user_id, meses_usados[-1], len(meses_usados)) if meses_usados else {}

    return {
        "objetivo": objetivo.nome,
        "valor_alvo": objetivo.valor_alvo,
        "valor_poupado": objetivo.valor_poupado,
        "falta": round(max(objetivo.valor_alvo - objetivo.valor_poupado, 0), 2),
        "data_alvo": objetivo.data_alvo.isoformat(),
        "meses_ate_ao_prazo": meses_ate(objetivo.data_alvo, hoje),
        "necessario_por_mes": necessario_por_mes(objetivo, hoje),
        "saldo_medio_mensal": saldo,
        "maximo_para_poupar_por_mes": round(max(saldo, 0) * PARTE_DO_SALDO_PARA_POUPAR, 2),
        "meses_do_saldo_medio": meses_usados,
        "outros_objetivos_por_mes": round(outros_por_mes, 2),
        "gastos_medios_por_categoria": {categoria: dados["media"] for categoria, dados in gastos.items()},
    }
