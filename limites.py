"""Limite diário de perguntas à IA, para cada utilizador não gastar demasiados créditos.

O limite depende do plano da assinatura (coluna plano da tabela assinaturas).
"""

from datetime import date

from fastapi import HTTPException

from database import supabase
from models import EstadoPlano, PlanoDisponivel

# Perguntas à IA por dia em cada plano. Para mudar um limite, muda-se só aqui.
LIMITES_POR_PLANO = {"free": 5, "essencial": 20, "completo": 50}

# Páginas máximas de um extrato em PDF. A IA lê o PDF inteiro numa só chamada: cada página a mais
# custa tokens, por isso um PDF maior é recusado antes de chamar a IA (e sem gastar um pedido).
MAX_PAGINAS_PDF = 10


def limite_do_plano(plano: str | None) -> int:
    """Quantas perguntas por dia o plano permite.

    plano vem da base de dados: pode ser None (a assinatura não tem linha)
    ou um nome que não está em LIMITES_POR_PLANO.
    """
    return LIMITES_POR_PLANO.get(plano, 0)
    


def plano_do_utilizador(user_id: str) -> str | None:
    """O plano da assinatura do utilizador, ou None se não houver linha."""
    resposta = supabase.table("assinaturas").select("plano").eq("user_id", user_id).execute()
    return resposta.data[0]["plano"] if resposta.data else None


def perguntas_de_hoje(user_id: str) -> int:
    """Quantas perguntas à IA o utilizador já fez hoje."""
    # count="exact" pede ao Supabase só o número de linhas (como um SELECT COUNT(*)), sem as trazer.
    resposta = (
        supabase.table("uso_ia")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("criado_em", date.today().isoformat())
        .execute()
    )
    return resposta.count or 0


def assinatura_do_utilizador(user_id: str) -> tuple[str | None, date | None]:
    """O plano e o ativo_ate da assinatura, numa só consulta. (None, None) se não houver linha."""
    resposta = supabase.table("assinaturas").select("plano, ativo_ate").eq("user_id", user_id).execute()
    if not resposta.data:
        return None, None
    linha = resposta.data[0]
    ativo_ate = date.fromisoformat(linha["ativo_ate"]) if linha.get("ativo_ate") else None
    return linha["plano"], ativo_ate


def estado_do_plano(user_id: str) -> EstadoPlano:
    """O plano, o limite, as perguntas de hoje e até quando dura: o que o menu lateral mostra."""
    plano, ativo_ate = assinatura_do_utilizador(user_id)
    if plano == "free":
        ativo_ate = None  # o Free não acaba, mesmo que a coluna tenha uma data perdida
    return EstadoPlano(
        plano=plano,
        limite=limite_do_plano(plano),
        usadas_hoje=perguntas_de_hoje(user_id),
        ativo_ate=ativo_ate,
    )


def planos_disponiveis() -> list[PlanoDisponivel]:
    """Todos os planos e os seus limites, pela ordem de LIMITES_POR_PLANO (free, essencial, completo)."""
    return [PlanoDisponivel(plano=plano, limite_diario=limite) for plano, limite in LIMITES_POR_PLANO.items()]


def registar_pergunta(user_id: str) -> None:
    """Conta a pergunta de hoje, ou responde 429 se o utilizador já chegou ao limite do plano."""
    limite = limite_do_plano(plano_do_utilizador(user_id))

    if perguntas_de_hoje(user_id) >= limite:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Chegaste ao limite de hoje. Já usaste os {limite} pedidos à IA do teu plano. "
                "O contador volta a zero à meia-noite."
            ),
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
