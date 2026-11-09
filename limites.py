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

# Extratos em PDF que cada plano pode importar por mês de Lisboa (o Free não importa PDF).
# Contam à parte dos pedidos à IA: cada PDF conta aqui E gasta 1 pedido. Para mudar, muda-se só aqui.
LIMITES_PDF_POR_PLANO: dict[str, int] = {
    "essencial": 15,
    "completo": 30,
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


def limite_pdf_do_plano(plano: str | None) -> int:
    """Quantos extratos em PDF o plano pode importar por mês. 0 no Free e em planos desconhecidos."""
    return LIMITES_PDF_POR_PLANO.get(plano, 0)


def plano_efetivo(plano: str | None, ativo_ate: date | None, hoje: date) -> str | None:
    """O plano que vale hoje: um plano pago que já terminou passa a contar como Free.

    A base de dados não muda (o plano pago fica na coluna, para o CEO saber o que renovar):
    calcula-se aqui, em cada leitura. Os planos pagos valem até ao ativo_ate, incluindo esse dia.
    Um plano pago sem data é um erro nos dados: na dúvida, vale como Free (não paga IA a mais
    e também não bloqueia a conta).
    """
    if plano in PLANOS_PAGOS and (ativo_ate is None or ativo_ate < hoje):
        return "free"
    return plano


def plano_inclui(plano: str | None, funcao: str) -> bool:
    """Se o plano tem a função. As que não estão em FUNCOES_PAGAS são de todos os planos."""
    return funcao not in FUNCOES_PAGAS or plano in PLANOS_PAGOS


def plano_do_utilizador(user_id: str) -> str | None:
    """O plano que vale hoje para o utilizador (plano_efetivo), ou None se não houver linha."""
    plano, ativo_ate = assinatura_do_utilizador(user_id)
    return plano_efetivo(plano, ativo_ate, hoje_em_lisboa())


def exigir_funcao(user_id: str, funcao: str) -> None:
    """Responde 402 se o plano do utilizador não tiver a função.

    402 e não 403: no frontend, 403 quer dizer "assinatura expirada" e manda para outra página.
    """
    if not plano_inclui(plano_do_utilizador(user_id), funcao):
        raise HTTPException(status_code=402, detail=FUNCOES_PAGAS[funcao])


# Códigos de erro do PostgREST quando uma coluna não existe (ex.: uso_ia.funcao antes da sql/016).
COLUNA_NAO_EXISTE = {"PGRST204", "42703"}


def pdfs_no_mes(user_id: str) -> int:
    """Quantos extratos em PDF o utilizador já mandou ler à IA neste mês de Lisboa.

    Conta as linhas da uso_ia com funcao='importar_pdf' (sql/016). Antes da 016 a coluna não existe:
    conta-se então pelas chamadas à IA de leitura de PDF (chamadas_ia, sql/014). Se nem isso der,
    devolve 0 (fica só o limite de pedidos à IA, como antes) e deixa um aviso nos logs.
    """
    inicio = inicio_do_periodo("mes", agora_utc()).isoformat()
    try:
        resposta = (
            supabase.table("uso_ia")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("funcao", "importar_pdf")
            .gte("criado_em", inicio)
            .execute()
        )
        return resposta.count or 0
    except APIError as erro:
        if erro.code not in COLUNA_NAO_EXISTE:
            raise
    print("AVISO: coluna uso_ia.funcao não encontrada (sql/016); a contar os PDF pela tabela chamadas_ia.")
    try:
        resposta = (
            supabase.table("chamadas_ia")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("funcao", "extrato_pdf")
            .eq("origem", "app")
            .gte("criado_em", inicio)
            .execute()
        )
        return resposta.count or 0
    except APIError as erro:
        # Falha fechado: sem saber quantos PDF já foram lidos, não se lê mais nenhum (o CSV continua).
        print(f"AVISO: não foi possível contar os PDF deste mês: {erro}")
        raise HTTPException(
            status_code=503, detail="Não foi possível importar o PDF agora. Tenta outra vez daqui a pouco."
        )


def mensagem_do_limite_pdf(limite: int) -> str:
    """O texto do 429 do limite de PDF (igual ao do frontend, textosPlanos.ts)."""
    return (
        f"Chegaste ao limite de {limite} extratos PDF este mês. O contador volta a zero no dia 1. "
        "Até lá, podes importar o extrato em CSV."
    )


def exigir_limite_pdf(user_id: str) -> None:
    """Responde 429 se o utilizador já importou os PDF do mês que o plano permite.

    Chama-se depois de o PDF ser aceite (plano, tamanho, páginas, espaço na conta) e logo antes
    de gastar o pedido à IA: um PDF recusado nunca conta.
    """
    limite = limite_pdf_do_plano(plano_do_utilizador(user_id))
    if pdfs_no_mes(user_id) >= limite:
        raise HTTPException(status_code=429, detail=mensagem_do_limite_pdf(limite))


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
    """O plano, o limite, os pedidos do período e até quando dura: o que o menu lateral mostra.

    Um plano pago que terminou aparece como Free, com o nome e a data do plano que terminou.
    """
    na_tabela, ativo_ate = assinatura_do_utilizador(user_id)
    plano = plano_efetivo(na_tabela, ativo_ate, hoje_em_lisboa())
    # Só há "plano terminado" quando se sabe a data (um pago sem data é um erro nos dados).
    terminou_em = ativo_ate if plano != na_tabela else None
    if plano == "free":
        ativo_ate = None  # o Free não acaba, mesmo que a coluna tenha uma data perdida
    periodo = periodo_do_plano(plano)
    usadas = pedidos_no_periodo(user_id, periodo)
    limite_pdf = limite_pdf_do_plano(plano)
    return EstadoPlano(
        plano=plano,
        limite=limite_do_plano(plano),
        periodo=periodo,
        usadas=usadas,
        usadas_hoje=usadas,  # nome antigo, só para o frontend antigo não partir durante o deploy
        ativo_ate=ativo_ate,
        plano_terminado=na_tabela if terminou_em else None,
        terminou_em=terminou_em,
        pdf_usados=pdfs_no_mes(user_id) if limite_pdf > 0 else 0,
        pdf_limite=limite_pdf,
    )


def planos_disponiveis() -> list[PlanoDisponivel]:
    """Todos os planos e os seus limites, pela ordem de LIMITES_POR_PLANO (free, essencial, completo)."""
    return [
        PlanoDisponivel(plano=plano, limite_diario=limite, periodo=periodo, limite_pdf=limite_pdf_do_plano(plano))
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


# Códigos de erro do PostgREST quando a função registar_pedido_ia não existe com os parâmetros enviados
# (a migração sql/015 ainda não foi corrida, ou a sql/016, que lhe junta o p_funcao).
FUNCAO_NAO_EXISTE = {"PGRST202", "42883"}


def _chamar_registar_pedido_ia(parametros: dict) -> bool | None:
    """Chama a função registar_pedido_ia. None se não existir com estes parâmetros."""
    try:
        resposta = supabase.rpc("registar_pedido_ia", parametros).execute()
    except APIError as erro:
        if erro.code in FUNCAO_NAO_EXISTE:
            return None
        raise
    # A função devolve um boolean: o PostgREST responde só "true" ou "false". Qualquer outra coisa conta como não.
    return resposta.data is True


def registar_pedido_atomico(user_id: str, desde: datetime, limite: int, funcao: str) -> bool | None:
    """Conta e regista o pedido de uma só vez, na base de dados (função registar_pedido_ia).

    Tenta primeiro a versão da sql/016, que grava também a funcao; se ainda não existir,
    usa a da sql/015 (o pedido conta na mesma, só fica sem a funcao).
    Devolve True se registou, False se o utilizador já estava no limite,
    e None se nenhuma das versões existe no Supabase (aí usa-se o caminho antigo).
    """
    parametros = {"p_user_id": user_id, "p_desde": desde.isoformat(), "p_limite": limite}
    registado = _chamar_registar_pedido_ia(parametros | {"p_funcao": funcao})
    if registado is None:
        print("AVISO: registar_pedido_ia sem p_funcao (sql/016 por correr); o pedido fica sem a funcao.")
        registado = _chamar_registar_pedido_ia(parametros)
    return registado


def registar_pedido_em_dois_passos(user_id: str, periodo: str, limite: int, funcao: str) -> bool:
    """O caminho antigo: conta e depois insere. Pedidos ao mesmo tempo podem passar o limite.

    Só serve enquanto a migração 015 não for corrida; depois pode apagar-se.
    """
    if pedidos_no_periodo(user_id, periodo) >= limite:
        return False
    try:
        supabase.table("uso_ia").insert({"user_id": user_id, "funcao": funcao}).execute()
    except APIError as erro:
        if erro.code not in COLUNA_NAO_EXISTE:
            raise
        # Sem a sql/016 a coluna funcao não existe: o pedido grava-se sem ela, para contar na mesma.
        supabase.table("uso_ia").insert({"user_id": user_id}).execute()
    return True


def registar_pergunta(user_id: str, funcao: str) -> None:
    """Conta o pedido à IA, ou responde 429 se o utilizador já chegou ao limite do plano no período.

    funcao diz para que foi o pedido (chat, resumo, importar_pdf...): fica na coluna funcao da uso_ia,
    para se saber o que gasta mais, e é por ela que se contam os PDF do mês.
    """
    plano = plano_do_utilizador(user_id)
    limite, periodo = limite_do_plano(plano), periodo_do_plano(plano)

    registado = registar_pedido_atomico(user_id, inicio_do_periodo(periodo, agora_utc()), limite, funcao)
    if registado is None:
        # Aparece nos logs do Render: se continuar a aparecer depois de correr a 015, algo está mal.
        print("AVISO: função registar_pedido_ia não encontrada (sql/015); a usar o contador em dois passos.")
        registado = registar_pedido_em_dois_passos(user_id, periodo, limite, funcao)

    if not registado:
        raise HTTPException(status_code=429, detail=mensagem_do_limite(limite, periodo))


def pode_usar_ia(user_id: str, funcao: str) -> bool:
    """Como registar_pergunta(), mas devolve False em vez de responder 429.

    Serve para as rotas que funcionam sem IA: a movimentação grava-se sem categoria,
    e o resumo mostra um aviso, em vez de o pedido inteiro falhar.
    """
    try:
        registar_pergunta(user_id, funcao)
        return True
    except HTTPException:
        return False


def aviso_resumo_sem_pedidos(user_id: str) -> str:
    """O texto do resumo do mês quando já não há pedidos à IA (dia nos pagos, mês no Free)."""
    if periodo_do_plano(plano_do_utilizador(user_id)) == "mes":
        return "Chegaste ao limite de pedidos à IA deste mês. O resumo volta no dia 1."
    return "Chegaste ao limite de pedidos à IA de hoje. O resumo volta depois da meia-noite."
