"""Recolhe os números de um mês (e do anterior) para a IA escrever o resumo mensal.

Aqui não há tool use: sabemos à partida que dados são precisos, por isso vamos
buscá-los todos de uma vez e a IA só tem de os explicar.
"""

import hashlib
import json
from datetime import datetime, timezone

from dashboard import gastos_por_categoria, limites_do_mes, mes_anterior, resumo_mensal
from database import supabase
from models import ResumoMes
from orcamento import juntar, limites_do_utilizador


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
        # Só as categorias com orçamento definido: o limite e quanto já se gastou neste mês.
        "orcamentos": [
            linha.model_dump()
            for linha in juntar(limites_do_utilizador(user_id), gastos_por_categoria(deste_mes))
            if linha.limite is not None
        ],
    }


# --- Resumos já escritos pela IA ---
# Ficam na tabela resumos_ia (sql/016): sobrevivem a um reinício do Render, por isso o mesmo resumo
# não gasta outro pedido à IA. Se a tabela ainda não existir (ou o Supabase falhar), ficam na memória
# do servidor, como antes da 016 (perdem-se quando o Render reinicia).
RESUMOS_EM_MEMORIA: dict[str, ResumoMes] = {}


def assinatura_dos_dados(dados: dict) -> str:
    """Uma "impressão digital" dos números do mês: muda se qualquer número mudar.

    sort_keys: a mesma informação dá sempre o mesmo texto, seja qual for a ordem das chaves.
    """
    texto = json.dumps(dados, sort_keys=True, default=str)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _chave_memoria(user_id: str, mes: str, assinatura: str) -> str:
    return f"{user_id}:{mes}:{assinatura}"


def resumo_guardado(user_id: str, mes: str, assinatura: str) -> ResumoMes | None:
    """O resumo já escrito para estes números, ou None se os números mudaram (ou nunca houve resumo)."""
    try:
        resposta = (
            supabase.table("resumos_ia")
            .select("texto, alertas")
            .eq("user_id", user_id)
            .eq("mes", mes)
            .eq("assinatura", assinatura)
            .execute()
        )
        if resposta.data:
            linha = resposta.data[0]
            return ResumoMes(resumo=linha["texto"], alertas=linha["alertas"] or [])
    except Exception as erro:
        print(f"AVISO: não foi possível ler os resumos guardados (sql/016 por correr?) ({getattr(erro, 'code', None) or type(erro).__name__}).")
    return RESUMOS_EM_MEMORIA.get(_chave_memoria(user_id, mes, assinatura))


def guardar_resumo(user_id: str, mes: str, assinatura: str, resumo: ResumoMes) -> None:
    """Guarda o resumo do mês. Há um só por utilizador e mês: um resumo novo substitui o antigo."""
    try:
        supabase.table("resumos_ia").upsert(
            {
                "user_id": user_id,
                "mes": mes,
                "assinatura": assinatura,
                "texto": resumo.resumo,
                "alertas": [alerta.model_dump() for alerta in resumo.alertas],
                # No ON CONFLICT o default da coluna não volta a correr: a data vai explícita.
                "criado_em": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="user_id,mes",
        ).execute()
        return
    except Exception as erro:
        print(f"AVISO: não foi possível guardar o resumo (sql/016 por correr?) ({getattr(erro, 'code', None) or type(erro).__name__}).")
    RESUMOS_EM_MEMORIA[_chave_memoria(user_id, mes, assinatura)] = resumo


def esquecer_resumos(user_id: str) -> None:
    """Tira da memória os resumos do utilizador (quando apaga a conta). Os da tabela vão com a conta (ON DELETE CASCADE)."""
    prefixo = f"{user_id}:"
    # list(): uma cópia das chaves, para outro pedido poder escrever no dicionário ao mesmo tempo sem RuntimeError.
    for chave in [chave for chave in list(RESUMOS_EM_MEMORIA) if chave.startswith(prefixo)]:
        RESUMOS_EM_MEMORIA.pop(chave, None)
