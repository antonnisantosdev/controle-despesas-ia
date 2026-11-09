"""Limites de pedidos à IA e funções de cada plano, para cada utilizador não gastar demasiados créditos.

O plano vem da assinatura (coluna plano da tabela assinaturas). O Free conta os pedidos por mês;
os planos pagos contam por dia. O dia e o mês são os de Lisboa, não os do servidor (o Render está em UTC).
"""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from postgrest.exceptions import APIError

from database import supabase
from models import EstadoPlano, PlanoDisponivel

# Pedidos à IA de cada plano e o período em que se contam ("dia" ou "mes").
# Para mudar um limite, muda-se só aqui.
LIMITES_POR_PLANO: dict[str, tuple[int, str]] = {
    "free": (30, "mes"),
    "essencial": (20, "dia"),
    "completo": (50, "dia"),
}

# Funções que só os planos pagos têm, com a mensagem do 402 para quem não as tem.
PLANOS_PAGOS = {"essencial", "completo"}
FUNCOES_PAGAS = {
    "importar_pdf": (
        "A importação de extratos em PDF está disponível nos planos Essencial e Completo. "
        "No Free, podes importar o extrato em CSV."
    ),
    "ler_talao": "A leitura de talões está disponível nos planos Essencial e Completo.",
}

# Páginas máximas de um extrato em PDF. A IA lê o PDF inteiro numa só chamada: cada página a mais
# custa tokens, por isso um PDF maior é recusado antes de chamar a IA (e sem gastar um pedido).
MAX_PAGINAS_PDF = 10

# Movimentações máximas de uma conta. Sem teto, importar CSV sem pedidos à IA (que é grátis)
# deixava encher a base de dados sem fim. Uma pessoa real fica muito abaixo disto.
MAX_TRANSACOES_POR_CONTA = 20000


def exigir_espaco_na_conta(atuais: int, novas: int) -> None:
    """Responde 422 se as movimentações atuais mais as novas passarem MAX_TRANSACOES_POR_CONTA."""
    if atuais + novas > MAX_TRANSACOES_POR_CONTA:
        raise HTTPException(
            status_code=422,
            detail="Chegaste ao máximo de 20 000 movimentações nesta conta. Fala connosco se precisares de mais.",
        )


# Hora de Lisboa, com a mudança de hora incluída. No Windows a base de dados de fusos vem
# do pacote tzdata (requirements.txt); no Linux (Render, GitHub Actions) já vem com o sistema.
FUSO_LISBOA = ZoneInfo("Europe/Lisbon")


def agora_utc() -> datetime:
    """A hora atual em UTC. Função à parte para os testes poderem fixar a hora."""
    return datetime.now(timezone.utc)


def hoje_em_lisboa() -> date:
    """A data de hoje em Lisboa (o servidor está em UTC: entre as 23:00 e a meia-noite de verão já é amanhã)."""
    return agora_utc().astimezone(FUSO_LISBOA).date()


def inicio_do_periodo(periodo: str, agora: datetime) -> datetime:
    """O início do dia ou do mês de Lisboa em que cai agora, em UTC (é assim que o criado_em se compara)."""
    hoje_em_lisboa = agora.astimezone(FUSO_LISBOA).date()
    primeiro_dia = hoje_em_lisboa.replace(day=1) if periodo == "mes" else hoje_em_lisboa
    meia_noite = datetime.combine(primeiro_dia, time(0), tzinfo=FUSO_LISBOA)
    return meia_noite.astimezone(timezone.utc)


# --- Planos ---


def limite_do_plano(plano: str | None) -> int:
    """Quantos pedidos à IA o plano permite no seu período.

    plano vem da base de dados: pode ser None (a assinatura não tem linha)
    ou um nome que não está em LIMITES_POR_PLANO. Na dúvida, 0: sem IA.
    """
    return LIMITES_POR_PLANO.get(plano, (0, "dia"))[0]


def periodo_do_plano(plano: str | None) -> str:
    """ "dia" ou "mes": em que período se contam os pedidos do plano."""
    return LIMITES_POR_PLANO.get(plano, (0, "dia"))[1]


def plano_inclui(plano: str | None, funcao: str) -> bool:
    """Se o plano tem a função. As que não estão em FUNCOES_PAGAS são de todos os planos."""
    return funcao not in FUNCOES_PAGAS or plano in PLANOS_PAGOS


def plano_do_utilizador(user_id: str) -> str | None:
    """O plano da assinatura do utilizador, ou None se não houver linha."""
    resposta = supabase.table("assinaturas").select("plano").eq("user_id", user_id).execute()
    return resposta.data[0]["plano"] if resposta.data else None


def exigir_funcao(user_id: str, funcao: str) -> None:
    """Responde 402 se o plano do utilizador não tiver a função.

    402 e não 403: no frontend, 403 quer dizer "assinatura expirada" e manda para outra página.
    """
    if not plano_inclui(plano_do_utilizador(user_id), funcao):
        raise HTTPException(status_code=402, detail=FUNCOES_PAGAS[funcao])


def pedidos_no_periodo(user_id: str, periodo: str) -> int:
    """Quantos pedidos à IA o utilizador já fez neste dia (ou mês) de Lisboa."""
    inicio = inicio_do_periodo(periodo, agora_utc())
    # count="exact" pede ao Supabase só o número de linhas (como um SELECT COUNT(*)), sem as trazer.
    resposta = (
        supabase.table("uso_ia")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("criado_em", inicio.isoformat())
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
    """O plano, o limite, os pedidos do período e até quando dura: o que o menu lateral mostra."""
    plano, ativo_ate = assinatura_do_utilizador(user_id)
    if plano == "free":
        ativo_ate = None  # o Free não acaba, mesmo que a coluna tenha uma data perdida
    periodo = periodo_do_plano(plano)
    usadas = pedidos_no_periodo(user_id, periodo)
    return EstadoPlano(
        plano=plano,
        limite=limite_do_plano(plano),
        periodo=periodo,
        usadas=usadas,
        usadas_hoje=usadas,  # nome antigo, só para o frontend antigo não partir durante o deploy
        ativo_ate=ativo_ate,
    )


def planos_disponiveis() -> list[PlanoDisponivel]:
    """Todos os planos e os seus limites, pela ordem de LIMITES_POR_PLANO (free, essencial, completo)."""
    return [
        PlanoDisponivel(plano=plano, limite_diario=limite, periodo=periodo)
        for plano, (limite, periodo) in LIMITES_POR_PLANO.items()
    ]


def mensagem_do_limite(limite: int, periodo: str) -> str:
    """O texto do 429, conforme o plano conta por dia ou por mês."""
    if periodo == "mes":
        return (
            f"Chegaste ao limite deste mês. Já usaste os {limite} pedidos à IA deste mês. "
            "O contador volta a zero no dia 1."
        )
    return (
        f"Chegaste ao limite de hoje. Já usaste os {limite} pedidos à IA do teu plano. "
        "O contador volta a zero à meia-noite."
    )


# Códigos de erro do PostgREST quando a função registar_pedido_ia não existe
# (a migração sql/015_so_a_api_escreve.sql ainda não foi corrida no Supabase).
FUNCAO_NAO_EXISTE = {"PGRST202", "42883"}


def registar_pedido_atomico(user_id: str, desde: datetime, limite: int) -> bool | None:
    """Conta e regista o pedido de uma só vez, na base de dados (função registar_pedido_ia, sql/015).

    Devolve True se registou, False se o utilizador já estava no limite,
    e None se a função ainda não existe no Supabase (aí usa-se o caminho antigo).
    """
    try:
        resposta = supabase.rpc(
            "registar_pedido_ia", {"p_user_id": user_id, "p_desde": desde.isoformat(), "p_limite": limite}
        ).execute()
    except APIError as erro:
        if erro.code in FUNCAO_NAO_EXISTE:
            return None
        raise
    # A função devolve um boolean: o PostgREST responde só "true" ou "false". Qualquer outra coisa conta como não.
    return resposta.data is True


def registar_pedido_em_dois_passos(user_id: str, periodo: str, limite: int) -> bool:
    """O caminho antigo: conta e depois insere. Pedidos ao mesmo tempo podem passar o limite.

    Só serve enquanto a migração 015 não for corrida; depois pode apagar-se.
    """
    if pedidos_no_periodo(user_id, periodo) >= limite:
        return False
    supabase.table("uso_ia").insert({"user_id": user_id}).execute()
    return True


def registar_pergunta(user_id: str) -> None:
    """Conta o pedido à IA, ou responde 429 se o utilizador já chegou ao limite do plano no período."""
    plano = plano_do_utilizador(user_id)
    limite, periodo = limite_do_plano(plano), periodo_do_plano(plano)

    registado = registar_pedido_atomico(user_id, inicio_do_periodo(periodo, agora_utc()), limite)
    if registado is None:
        # Aparece nos logs do Render: se continuar a aparecer depois de correr a 015, algo está mal.
        print("AVISO: função registar_pedido_ia não encontrada (sql/015); a usar o contador em dois passos.")
        registado = registar_pedido_em_dois_passos(user_id, periodo, limite)

    if not registado:
        raise HTTPException(status_code=429, detail=mensagem_do_limite(limite, periodo))


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


def aviso_resumo_sem_pedidos(user_id: str) -> str:
    """O texto do resumo do mês quando já não há pedidos à IA (dia nos pagos, mês no Free)."""
    if periodo_do_plano(plano_do_utilizador(user_id)) == "mes":
        return "Chegaste ao limite de pedidos à IA deste mês. O resumo volta no dia 1."
    return "Chegaste ao limite de pedidos à IA de hoje. O resumo volta depois da meia-noite."
