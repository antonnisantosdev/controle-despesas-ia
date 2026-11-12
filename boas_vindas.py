"""Questionário de boas-vindas (sql/021): o que a conta nova responde na 1.ª entrada.

- O país, os países dos cartões e contas e a moeda gravam-se no perfil da conta (perfil.atualizar_perfil, sql/020).
- O motivo e os objetivos (opcionais, só opções fechadas) ficam na tabela boas_vindas.
- assinaturas.boas_vindas_em marca a conta como respondida (o frontend deixa de abrir o questionário).

A IA não usa estas respostas. As métricas tiram-se só agregadas (consultas no fim da sql/021).
Antes da sql/021 as rotas respondem 503 e não gravam nada. Nada aqui escreve o user_id nos logs.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from postgrest.exceptions import APIError

from database import supabase
from limites import Assinatura, assinatura_do_utilizador, esquecer_assinatura
from mensagens import msg
from models import BoasVindasGuardadas, RespostasBoasVindas
from perfil import atualizar_perfil, moedas_possiveis

# As opções aceites (iguais às do CHECK da sql/021). Valores estranhos lidos da base de dados não se devolvem.
MOTIVOS = ("nao_sei", "fim_mes", "supermercado", "folhas", "poupar", "experimentar", "outro")
OBJETIVOS = ("importar", "categorias", "orcamento", "chat", "resumo", "reserva", "taloes")


def agora_utc() -> datetime:
    """A hora atual em UTC. Função à parte para os testes poderem fixá-la."""
    return datetime.now(timezone.utc)


def _indisponivel(pais: str | None) -> HTTPException:
    return HTTPException(status_code=503, detail=msg("boas_vindas_indisponivel", pais))


def _conta_com_021(user_id: str) -> Assinatura:
    """A assinatura da conta, ou 503 se a sql/021 ainda não foi corrida (ou a leitura falhou)."""
    try:
        conta = assinatura_do_utilizador(user_id)
    except APIError as erro:
        print(f"AVISO: boas-vindas não leu a assinatura ({erro.code}).")
        raise _indisponivel(None)
    if not conta.com_boas_vindas:
        print("AVISO: rota /conta/boas-vindas antes da sql/021.")
        raise _indisponivel(conta.pais)
    return conta


def _gravar_perfil(
    user_id: str, pedido: RespostasBoasVindas, conta: Assinatura
) -> tuple[str, list[str], str, str | None]:
    """Grava o país, os bancos e a moeda. Devolve (pais, bancos, moeda, aviso).

    Se a moeda não puder mudar (409: a conta já tem dados), grava o resto com a moeda de antes e devolve o aviso.
    Se os bancos pedidos não servirem para a moeda de antes (ex.: só BR numa conta em EUR), ficam os de antes.
    conta: a assinatura já lida no início do pedido (o perfil de antes; o 409 não mudou nada).
    """
    try:
        novo = atualizar_perfil(user_id, pedido.pais, list(pedido.paises_bancos), pedido.moeda)
        return novo.pais, list(novo.paises_bancos), novo.moeda, None
    except HTTPException as erro:
        if erro.status_code != 409:
            raise
        aviso = erro.detail
    bancos = list(pedido.paises_bancos) if conta.moeda in moedas_possiveis(pedido.paises_bancos) else list(conta.paises_bancos)
    novo = atualizar_perfil(user_id, pedido.pais, bancos, conta.moeda)
    return novo.pais, list(novo.paises_bancos), novo.moeda, aviso


def guardar_respostas(user_id: str, pedido: RespostasBoasVindas) -> BoasVindasGuardadas:
    """PUT /conta/boas-vindas: grava o perfil e as respostas e marca o questionário como feito.

    503 antes da sql/021 (sem gravar nada) ou se a base de dados falhar. O 422 e o 503 do perfil vêm do perfil.py.
    """
    conta = _conta_com_021(user_id)
    pais, bancos, moeda, aviso = _gravar_perfil(user_id, pedido, conta)
    agora = agora_utc().isoformat()
    objetivos = list(pedido.objetivos) if pedido.objetivos else None  # [] é o mesmo que saltar
    try:
        # O respondido_em só se escreve na 1.ª vez (DEFAULT now()); o upsert só muda as colunas enviadas.
        supabase.table("boas_vindas").upsert(
            {"user_id": user_id, "motivo": pedido.motivo, "objetivos": objetivos, "atualizado_em": agora},
            on_conflict="user_id",
        ).execute()
        # Só marca da 1.ª vez: nas definições a data do questionário fica a de quando foi feito.
        supabase.table("assinaturas").update({"boas_vindas_em": agora}).eq("user_id", user_id).is_(
            "boas_vindas_em", "null"
        ).execute()
    except APIError as erro:
        print(f"AVISO: respostas das boas-vindas não gravadas ({erro.code}).")
        raise _indisponivel(pais)
    esquecer_assinatura(user_id)
    return BoasVindasGuardadas(
        pais=pais, paises_bancos=bancos, moeda=moeda, motivo=pedido.motivo, objetivos=objetivos, aviso=aviso
    )


def ler_respostas(user_id: str) -> BoasVindasGuardadas:
    """GET /conta/boas-vindas (para as definições): o perfil da conta e as respostas (None se não respondeu)."""
    conta = _conta_com_021(user_id)
    try:
        resposta = supabase.table("boas_vindas").select("motivo, objetivos").eq("user_id", user_id).execute()
    except APIError as erro:
        print(f"AVISO: respostas das boas-vindas não lidas ({erro.code}).")
        raise _indisponivel(conta.pais)
    linha = resposta.data[0] if resposta.data else {}
    motivo = linha.get("motivo") if linha.get("motivo") in MOTIVOS else None
    objetivos = [o for o in dict.fromkeys(linha.get("objetivos") or []) if o in OBJETIVOS] or None
    return BoasVindasGuardadas(
        pais=conta.pais, paises_bancos=list(conta.paises_bancos), moeda=conta.moeda, motivo=motivo, objetivos=objetivos
    )


def apagar_respostas(user_id: str) -> None:
    """DELETE /conta/boas-vindas: apaga o motivo e os objetivos (a linha inteira). O perfil e a marca ficam."""
    conta = _conta_com_021(user_id)
    try:
        supabase.table("boas_vindas").delete().eq("user_id", user_id).execute()
    except APIError as erro:
        print(f"AVISO: respostas das boas-vindas não apagadas ({erro.code}).")
        raise _indisponivel(conta.pais)
