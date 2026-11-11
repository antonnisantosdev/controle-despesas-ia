"""Limites de pedidos à IA e funções de cada plano, para cada utilizador não gastar demasiados créditos.

O plano vem da assinatura (coluna plano da tabela assinaturas). O Free conta os pedidos por mês;
os planos pagos contam por dia. Os contadores começam no início do dia (ou mês) mais antigo entre
Lisboa e São Paulo (inicio_dos_contadores), não no do servidor (o Render está em UTC): mudar de país
nunca dá pedidos a mais. O "hoje" mostrado é o do país onde a pessoa vive (sql/020). O ativo_ate dos
planos pagos conta-se sempre em Lisboa (é o CEO que o escreve, em Portugal).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import TYPE_CHECKING, Literal
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from postgrest.exceptions import APIError

from database import supabase

# O models.py usa os limites do histórico do chat (abaixo): para não haver importação circular,
# os modelos importam-se dentro das funções que os usam.
if TYPE_CHECKING:
    from models import EstadoPlano, PlanoDisponivel

# Pedidos à IA de cada plano e o período em que se contam ("dia" ou "mes").
# Para mudar um limite, muda-se só aqui.
LIMITES_POR_PLANO: dict[str, tuple[int, str]] = {
    "free": (30, "mes"),
    "essencial": (20, "dia"),
    "completo": (50, "dia"),
}


# --- Como a IA trabalha em cada plano ---


@dataclass(frozen=True)
class ConfigIA:
    """O que cada plano recebe da IA nas respostas em texto (chat, resumo, orçamento, poupança).

    effort: quanto a IA "pensa" antes de responder (mais esforço, mais tokens e mais custo).
    max_tokens: no resumo, orçamento e poupança, o máximo de tokens da resposta; no chat,
        o orçamento de saída da pergunta inteira (todas as voltas juntas, ver MAX_VOLTAS_CHAT).
    meses_historico: meses de calendário que as ferramentas do chat veem, a contar com o atual
        (3 = o mês atual e os 2 anteriores). None = sem limite.
    memoria_mensagens: mensagens anteriores da conversa que o chat recebe (0 = cada pergunta é nova).
    cache: se as instruções e as ferramentas do chat vão com prompt caching.

    Não se aplica à leitura de PDF, à categorização nem aos talões: aí a resposta cresce com o
    tamanho do documento, e com estes max_tokens sairia cortada (ficam com os valores do ia.py).
    """

    effort: Literal["low", "medium", "high"]
    max_tokens: int
    meses_historico: int | None
    memoria_mensagens: int
    cache: bool


# Decisão do CEO. Para mudar o que um plano recebe da IA, muda-se só aqui.
CONFIG_IA_POR_PLANO: dict[str, ConfigIA] = {
    "free": ConfigIA(effort="low", max_tokens=1024, meses_historico=3, memoria_mensagens=0, cache=False),
    "essencial": ConfigIA(effort="low", max_tokens=2048, meses_historico=12, memoria_mensagens=4, cache=False),
    "completo": ConfigIA(effort="medium", max_tokens=4096, meses_historico=None, memoria_mensagens=10, cache=True),
}

# Voltas máximas do chat por pergunta (cada volta é uma chamada à IA, que pode pedir ferramentas).
# Junto com o orçamento de saída (max_tokens do plano, para a pergunta inteira), põe um teto ao custo
# de cada pergunta: sem isto, uma pergunta do Completo podia custar 5 voltas x 4096 tokens de saída,
# mais as entradas repetidas em cada volta. Com 3 voltas e 4096 tokens no total, o pior caso fica limitado.
MAX_VOLTAS_CHAT = 3

# Tokens de saída mínimos para fazer mais uma volta do chat. Com menos do que isto, a resposta final
# sairia cortada a meio, e a volta custava as entradas (instruções, ferramentas, conversa) para nada:
# o chat para e pede para reformular a pergunta.
MIN_TOKENS_POR_VOLTA = 256

# Pedidos de ferramentas que o chat corre numa só volta. Os que passarem não correm: a IA recebe um erro
# e pode pedi-los na volta seguinte. Evita que uma resposta peça dezenas de consultas à base de dados.
MAX_FERRAMENTAS_POR_VOLTA = 4

# Tamanho do histórico do chat (vem do browser e pode ser falsificado). Cada pergunta antiga tem o
# tamanho máximo de uma pergunta; cada resposta antiga da IA, até 2000 caracteres; e o histórico inteiro
# até 4000, para não encher o prompt (e o custo), mesmo nos planos com mais memória.
MAX_CARACTERES_PERGUNTA_HISTORICO = 500
MAX_CARACTERES_RESPOSTA_HISTORICO = 2000
MAX_CARACTERES_HISTORICO = 4000


def config_ia_do_plano(plano: str | None) -> ConfigIA:
    """A configuração da IA do plano. Plano desconhecido ou None: a do Free (a mais barata)."""
    return CONFIG_IA_POR_PLANO.get(plano or "", CONFIG_IA_POR_PLANO["free"])


def primeiro_mes_visivel(config: ConfigIA, hoje: date) -> str | None:
    """O mês mais antigo ("AAAA-MM") que as ferramentas do chat podem ver. None = sem limite.

    Meses de calendário: com 3 meses e hoje a 9 de novembro, vê-se desde setembro (dia 1).
    """
    if config.meses_historico is None:
        return None
    # Conta em "meses absolutos" (ano x 12 + mês) para atravessar a mudança de ano sem casos especiais.
    absoluto = hoje.year * 12 + (hoje.month - 1) - (config.meses_historico - 1)
    return f"{absoluto // 12:04d}-{absoluto % 12 + 1:02d}"


# Funções que só os planos pagos têm, com a mensagem do 402 para quem não as tem.
PLANOS_PAGOS = {"essencial", "completo"}
FUNCOES_PAGAS = {
    "importar_pdf": (
        "A importação de extratos em PDF está disponível nos planos Essencial e Completo. "
        "No Free, podes importar o extrato em CSV."
    ),
    "ler_talao": "A leitura de talões está disponível nos planos Essencial e Completo.",
    # O mesmo texto do frontend.
    "precos_por_loja": "Comparar preços entre as lojas onde compraste está disponível nos planos Essencial e Completo.",
    "exportar_relatorio": (
        "Descarregar o resumo anual em CSV (para abrir numa folha de cálculo) está disponível nos planos "
        "Essencial e Completo. No Free, podes ver o resumo na app e guardá-lo em PDF."
    ),
}

# Funções que só o plano Completo tem, com a mensagem do 402 para os outros planos.
FUNCOES_SO_COMPLETO = {
    "resumo_anual_ia": (
        "O resumo do ano escrito pela IA está disponível no plano Completo. "
        "Os números do resumo anual continuam disponíveis no teu plano."
    ),
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


# Hora de Lisboa e de São Paulo, com a mudança de hora incluída. No Windows a base de dados de fusos vem
# do pacote tzdata (requirements.txt); no Linux (Render, GitHub Actions) já vem com o sistema.
FUSO_LISBOA = ZoneInfo("Europe/Lisbon")
FUSO_SAO_PAULO = ZoneInfo("America/Sao_Paulo")

# O fuso de cada país onde a pessoa pode viver (assinaturas.pais). País desconhecido: Lisboa.
FUSO_POR_PAIS: dict[str, ZoneInfo] = {"PT": FUSO_LISBOA, "BR": FUSO_SAO_PAULO}


def fuso_do_pais(pais: str | None) -> ZoneInfo:
    """O fuso horário do país onde a pessoa vive. País desconhecido ou None: Lisboa (como até aqui)."""
    return FUSO_POR_PAIS.get(pais or "", FUSO_LISBOA)


def agora_utc() -> datetime:
    """A hora atual em UTC. Função à parte para os testes poderem fixar a hora."""
    return datetime.now(timezone.utc)


def hoje_no_fuso(fuso: ZoneInfo) -> date:
    """A data de hoje nesse fuso (o servidor está em UTC: em Lisboa, às 23:30 UTC de verão já é amanhã;
    em São Paulo, às 01:00 UTC ainda é ontem)."""
    return agora_utc().astimezone(fuso).date()


def hoje_em_lisboa() -> date:
    """A data de hoje em Lisboa. Serve para o ativo_ate dos planos e para o que não é de um utilizador (demo)."""
    return hoje_no_fuso(FUSO_LISBOA)


def inicio_do_periodo(periodo: str, agora: datetime, fuso: ZoneInfo = FUSO_LISBOA) -> datetime:
    """O início do dia ou do mês (no fuso dado) em que cai agora, em UTC (é assim que o criado_em se compara)."""
    hoje = agora.astimezone(fuso).date()
    primeiro_dia = hoje.replace(day=1) if periodo == "mes" else hoje
    meia_noite = datetime.combine(primeiro_dia, time(0), tzinfo=fuso)
    return meia_noite.astimezone(timezone.utc)


def inicio_dos_contadores(periodo: str, agora: datetime) -> datetime:
    """O início do período dos limites (pedidos à IA e PDF): o MAIS ANTIGO entre todos os fusos de FUSO_POR_PAIS.

    Revisão de segurança: se cada conta contasse no fuso do seu país, mudar de país nas definições
    (Lisboa <-> São Paulo) abria uma janela nova e dava pedidos a dobrar. Com o mais antigo, mudar de país
    nunca dá pedidos a mais (falha fechada). O preço: perto da meia-noite o período fica umas horas maior
    (até 3 h, ou 4 h com a hora de verão de Lisboa). O fuso do país serve só para mostrar datas e o "hoje".
    """
    return min(inicio_do_periodo(periodo, agora, fuso) for fuso in FUSO_POR_PAIS.values())


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
    """Se o plano tem a função. As que não estão em FUNCOES_PAGAS nem em FUNCOES_SO_COMPLETO são de todos os planos."""
    if funcao in FUNCOES_SO_COMPLETO:
        return plano == "completo"
    return funcao not in FUNCOES_PAGAS or plano in PLANOS_PAGOS


def plano_do_utilizador(user_id: str) -> str | None:
    """O plano que vale hoje para o utilizador (plano_efetivo), ou None se não houver linha."""
    conta = assinatura_do_utilizador(user_id)
    return plano_efetivo(conta.plano, conta.ativo_ate, hoje_em_lisboa())


def hoje_do_utilizador(user_id: str) -> date:
    """A data de hoje no país onde o utilizador vive (mês dos alertas, relatório, histórico do chat...)."""
    return hoje_no_fuso(assinatura_do_utilizador(user_id).fuso)


def plano_e_config_ia(user_id: str) -> tuple[str | None, ConfigIA]:
    """O plano que vale hoje e a configuração da IA desse plano (um pago que terminou conta como Free)."""
    plano = plano_do_utilizador(user_id)
    return plano, config_ia_do_plano(plano)


def exigir_funcao(user_id: str, funcao: str) -> None:
    """Responde 402 se o plano do utilizador não tiver a função.

    402 e não 403: no frontend, 403 quer dizer "assinatura expirada" e manda para outra página.
    """
    if not plano_inclui(plano_do_utilizador(user_id), funcao):
        mensagem = FUNCOES_SO_COMPLETO.get(funcao) or FUNCOES_PAGAS[funcao]
        raise HTTPException(status_code=402, detail=mensagem)


# Códigos de erro do PostgREST quando uma coluna não existe (ex.: uso_ia.funcao antes da sql/016).
COLUNA_NAO_EXISTE = {"PGRST204", "42703"}


def pdfs_no_mes(user_id: str) -> int:
    """Quantos extratos em PDF o utilizador já mandou ler à IA neste mês (desde inicio_dos_contadores).

    Conta as linhas da uso_ia com funcao='importar_pdf' (sql/016). Antes da 016 a coluna não existe:
    conta-se então pelas chamadas à IA de leitura de PDF (chamadas_ia, sql/014). Se nem isso der,
    devolve 0 (fica só o limite de pedidos à IA, como antes) e deixa um aviso nos logs.
    """
    inicio = inicio_dos_contadores("mes", agora_utc()).isoformat()
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
    """Quantos pedidos à IA o utilizador já fez neste dia (ou mês), desde inicio_dos_contadores."""
    inicio = inicio_dos_contadores(periodo, agora_utc())
    # count="exact" pede ao Supabase só o número de linhas (como um SELECT COUNT(*)), sem as trazer.
    resposta = (
        supabase.table("uso_ia")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("criado_em", inicio.isoformat())
        .execute()
    )
    return resposta.count or 0


# --- Assinatura e perfil da conta (país, países das contas e moeda: sql/020) ---

PAISES = ("PT", "BR")
MOEDAS = ("EUR", "BRL")
# A moeda de cada país das contas: bancos só PT, a moeda é EUR; só BR, BRL.
MOEDA_DO_PAIS = {"PT": "EUR", "BR": "BRL"}


@dataclass(frozen=True)
class Assinatura:
    """A linha da conta na tabela assinaturas.

    pais: onde a pessoa vive (língua, fuso, formatos). paises_bancos: de que países são os cartões e contas.
    moeda: a moeda principal (Fase 1: uma moeda por conta). com_perfil: False se as colunas da sql/020
    ainda não existem (o perfil é então o de sempre, PT / {PT} / EUR, e a API não escreve a moeda).
    """

    plano: str | None = None
    ativo_ate: date | None = None
    pais: str = "PT"
    paises_bancos: tuple[str, ...] = ("PT",)
    moeda: str = "EUR"
    com_perfil: bool = False

    @property
    def fuso(self) -> ZoneInfo:
        return fuso_do_pais(self.pais)


def _perfil_da_linha(linha: dict) -> dict:
    """O país, os países das contas e a moeda de uma linha da base de dados. Valores fora da lista
    (não deviam existir: há CHECK na sql/020) passam aos de sempre, para nada partir."""
    pais = linha.get("pais") if linha.get("pais") in PAISES else "PT"
    bancos = tuple(p for p in (linha.get("paises_bancos") or []) if p in PAISES) or ("PT",)
    moeda = linha.get("moeda") if linha.get("moeda") in MOEDAS else "EUR"
    return {"pais": pais, "paises_bancos": bancos, "moeda": moeda}


def assinatura_do_utilizador(user_id: str) -> Assinatura:
    """A assinatura da conta (plano, ativo_ate e perfil), numa só consulta. Sem linha: Assinatura() (plano None).

    Antes da sql/020 as colunas do perfil não existem: lê só o plano e o ativo_ate, e o perfil fica
    PT / {PT} / EUR (como todas as contas até aqui), com um aviso nos logs.
    """
    try:
        resposta = (
            supabase.table("assinaturas")
            .select("plano, ativo_ate, pais, paises_bancos, moeda")
            .eq("user_id", user_id)
            .execute()
        )
        com_perfil = True
    except APIError as erro:
        if erro.code not in COLUNA_NAO_EXISTE:
            raise
        print("AVISO: colunas pais/paises_bancos/moeda não encontradas (sql/020); a conta conta como PT/EUR.")
        resposta = supabase.table("assinaturas").select("plano, ativo_ate").eq("user_id", user_id).execute()
        com_perfil = False
    if not resposta.data:
        return Assinatura()
    linha = resposta.data[0]
    ativo_ate = date.fromisoformat(linha["ativo_ate"]) if linha.get("ativo_ate") else None
    perfil = _perfil_da_linha(linha) if com_perfil else {}
    return Assinatura(plano=linha["plano"], ativo_ate=ativo_ate, com_perfil=com_perfil, **perfil)


def moeda_da_conta(user_id: str) -> str | None:
    """A moeda principal da conta, para gravar em cada movimento e compra novos (nunca a que vem do pedido).

    None antes da sql/020 (a coluna moeda ainda não existe: não se envia). Depois da 020 um gatilho
    na base de dados põe a mesma moeda, mesmo que a API se engane.
    """
    conta = assinatura_do_utilizador(user_id)
    return conta.moeda if conta.com_perfil else None


def estado_do_plano(user_id: str) -> EstadoPlano:
    """O plano, o limite, os pedidos do período e até quando dura: o que o menu lateral mostra.

    Um plano pago que terminou aparece como Free, com o nome e a data do plano que terminou.
    """
    from models import EstadoPlano

    conta = assinatura_do_utilizador(user_id)
    na_tabela, ativo_ate = conta.plano, conta.ativo_ate
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
        memoria_mensagens=config_ia_do_plano(plano).memoria_mensagens,
        meses_historico=config_ia_do_plano(plano).meses_historico,
        pais=conta.pais,
        paises_bancos=list(conta.paises_bancos),
        moeda=conta.moeda,
    )


def planos_disponiveis() -> list[PlanoDisponivel]:
    """Todos os planos e os seus limites, pela ordem de LIMITES_POR_PLANO (free, essencial, completo)."""
    from models import PlanoDisponivel

    return [
        PlanoDisponivel(
            plano=plano,
            limite_diario=limite,
            periodo=periodo,
            limite_pdf=limite_pdf_do_plano(plano),
            memoria_mensagens=config_ia_do_plano(plano).memoria_mensagens,
            meses_historico=config_ia_do_plano(plano).meses_historico,
        )
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

    registado = registar_pedido_atomico(user_id, inicio_dos_contadores(periodo, agora_utc()), limite, funcao)
    if registado is None:
        # Aparece nos logs do Render: se continuar a aparecer depois de correr a 015, algo está mal.
        print("AVISO: função registar_pedido_ia não encontrada (sql/015); a usar o contador em dois passos.")
        registado = registar_pedido_em_dois_passos(user_id, periodo, limite, funcao)

    if not registado:
        raise HTTPException(status_code=429, detail=mensagem_do_limite(limite, periodo))


def _chamar_registar_pdf_ia(parametros: dict) -> str | None:
    """Chama a função registar_pdf_ia (sql/017). None se ainda não existir no Supabase."""
    try:
        resposta = supabase.rpc("registar_pdf_ia", parametros).execute()
    except APIError as erro:
        if erro.code in FUNCAO_NAO_EXISTE:
            return None
        raise
    # A função devolve texto ('ok', 'pdf' ou 'pedidos'): o PostgREST responde só essa palavra.
    return resposta.data if isinstance(resposta.data, str) else ""


def registar_pdf(user_id: str) -> None:
    """Conta a leitura de um PDF (um pedido à IA "importar_pdf") ou responde 429 com o limite que falhou.

    Chama-se depois de o PDF ser aceite (plano, tamanho, páginas, espaço na conta) e logo antes
    de chamar a IA: um PDF recusado nunca conta.
    Com a sql/017, o limite de PDF do mês e o de pedidos à IA veem-se e o pedido regista-se de uma só vez,
    na base de dados (sem corridas entre PDF enviados ao mesmo tempo). Sem a 017, usa o caminho antigo
    em dois passos (exigir_limite_pdf e registar_pergunta) e deixa um aviso nos logs.
    """
    plano = plano_do_utilizador(user_id)
    limite, periodo = limite_do_plano(plano), periodo_do_plano(plano)
    limite_pdf = limite_pdf_do_plano(plano)
    agora = agora_utc()

    resultado = _chamar_registar_pdf_ia(
        {
            "p_user_id": user_id,
            "p_desde_pedidos": inicio_dos_contadores(periodo, agora).isoformat(),
            "p_limite_pedidos": limite,
            "p_desde_pdf": inicio_dos_contadores("mes", agora).isoformat(),
            "p_limite_pdf": limite_pdf,
        }
    )
    if resultado is None:
        # Aparece nos logs do Render: se continuar a aparecer depois de correr a 017, algo está mal.
        print("AVISO: função registar_pdf_ia não encontrada (sql/017); a usar o limite de PDF em dois passos.")
        exigir_limite_pdf(user_id)
        registar_pergunta(user_id, "importar_pdf")
        return

    if resultado == "ok":
        return
    if resultado == "pdf":
        raise HTTPException(status_code=429, detail=mensagem_do_limite_pdf(limite_pdf))
    if resultado == "pedidos":
        raise HTTPException(status_code=429, detail=mensagem_do_limite(limite, periodo))
    # Resposta inesperada: falha fechado (não se sabe se o pedido contou, por isso não se chama a IA).
    print(f"AVISO: registar_pdf_ia devolveu uma resposta inesperada: {resultado!r}")
    raise HTTPException(status_code=503, detail="Não foi possível importar o PDF agora. Tenta outra vez daqui a pouco.")


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
