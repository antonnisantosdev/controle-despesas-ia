import logging
import os
import re
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, UploadFile
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from postgrest.exceptions import APIError
from supabase import AuthApiError, AuthError

from auth import (
    FORMATO_CODE_CHALLENGE,
    apagar_utilizador,
    destino_google_valido,
    fazer_login,
    fazer_registo,
    guardar_origem,
    obter_utilizador_atual,
    obter_utilizador_confirmado,
    trocar_codigo_google,
    url_login_google,
)
from compras import gravar_compra, listar_compras
from dashboard import limites_do_mes, resumo_mensal
from consultas import gastos_do_mes
from database import ler_todas, supabase
from demo import (
    MENSAGEM_BLOQUEIO_DEMO,
    MENSAGEM_DEMO_DESLIGADA,
    config_demo,
    criar_token_demo,
    e_conta_demo,
    garantir_dados_da_semana,
    registar_entrada_demo,
    registar_forma_do_ip,
)
from ferramentas import PropostasDoPedido, executar_ferramenta, ferramentas_para
from dados_demo import MERCADOS_COMPRAS_DEMO, ORCAMENTO_COMPRAS_DEMO, achados_compras_demo
from ia import ErroIA, categorizar, conversar, fazer_compras, ler_extrato_pdf, ler_talao, planear_poupanca, resumir_ano, resumir_mes, sugerir_orcamento
from importar_csv import (
    MAX_ENTRADAS_ARVORE_PDF,
    MAX_MOVIMENTOS_CSV,
    ErroImportacao,
    ExtratoGrandeDemais,
    PdfIlegivel,
    contar_paginas_pdf,
    ler_extrato,
    transacoes_do_pdf,
)
from limite_ip import (
    LIMITE_GOOGLE_INICIO,
    LIMITE_GOOGLE_TROCA,
    LIMITE_LISTA_ESPERA,
    LIMITE_LOGIN,
    LIMITE_LOGIN_POR_EMAIL,
    LIMITE_REGISTO,
    ip_do_pedido,
    registar_mudanca_de_perfil,
)
from lista_espera import inscrever
from lista_compras import MERCADOS, calcular_plano, limpar_itens
from mensagens import Local, msg
from limites import (
    COLUNA_NAO_EXISTE,
    MAX_PAGINAS_PDF,
    abrir_cache_do_pedido,
    aviso_resumo_sem_pedidos,
    estado_do_plano,
    estado_listas_compras,
    exigir_espaco_na_conta,
    exigir_funcao,
    fechar_cache_do_pedido,
    hoje_do_utilizador,
    local_do_utilizador,
    moeda_da_conta,
    plano_e_config_ia,
    planos_disponiveis,
    pode_usar_ia,
    listas_no_mes,
    registar_lista_compras,
    registar_pdf,
    registar_pergunta,
)
from objetivos import (
    apagar_objetivo,
    atualizar_poupado,
    criar_objetivo,
    dados_do_plano,
    listar_objetivos,
    obter_objetivo,
)
from produtos import chave_do_produto, juncoes_do_utilizador, juntar_produtos, precos_do_utilizador, produtos_do_utilizador, separar_produtos
from perfil import atualizar_perfil, guardar_perfil_inicial, pode_escolher_brasil
from boas_vindas import apagar_respostas, guardar_respostas, ler_respostas
from orcamento import alertas_de_orcamento, guardar_limite, historico_para_sugestao, planeamento_do_mes
from models import (
    AlertasOrcamento,
    AnoSimulado,
    BoasVindasGuardadas,
    EstadoListaCompras,
    EstadoPlano,
    Categoria,
    Compra,
    ConfirmacaoApagarConta,
    Credenciais,
    NovaConta,
    GastoCategoria,
    InscricaoListaEspera,
    JuncaoProdutos,
    JuntarProdutos,
    LinhaOrcamento,
    MercadoDisponivel,
    NovaCompra,
    NovaMovimentacao,
    NovoLimite,
    NovoObjetivo,
    Objetivo,
    PerfilConta,
    PerfilGuardado,
    PedidoListaCompras,
    PerguntaChat,
    PlanoDisponivel,
    PlanoPoupanca,
    PoupadoAtualizar,
    PrecosDoProduto,
    ProdutoResumo,
    Recorrente,
    RelatorioAnual,
    TransacaoAtualizar,
    RespostaChat,
    RespostasBoasVindas,
    ResumoAnualIA,
    ResultadoImportacao,
    ResultadoListaCompras,
    ResumoMes,
    SugestaoOrcamento,
    ResumoMensal,
    Talao,
    Transacao,
    TransacaoCriar,
    TrocaGoogle,
    TransacaoImportada,
    metodo_do_pais,
)
from recorrentes import esquecer_recorrentes, recorrentes_do_utilizador
from relatorio import ano_valido, dados_para_ia, relatorio_do_ano, relatorio_em_csv
from resumo import assinatura_dos_dados, esquecer_resumos, guardar_resumo, recolher_dados, resumo_guardado
from simulador import simular_poupanca

app = FastAPI()

# Id de uma transação no caminho: dentro de um BIGINT, para um número enorme dar 422 e não 500 no PostgREST.
IdTransacao = Annotated[int, Path(ge=1, le=2**63 - 1)]


class SemIpNoRegisto(logging.Filter):
    """RGPD: tira o IP do visitante das linhas do access log do uvicorn (ficavam nos logs do Render).

    O uvicorn escreve '%s - "%s %s HTTP/%s" %d' com (cliente, método, caminho, versão, estado);
    o cliente ("1.2.3.4:0") passa a "-" e o resto da linha fica igual.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) == 5:
            record.args = ("-", *record.args[1:])
        return True


# Fica no logger (e não num handler): o uvicorn troca os handlers ao configurar os logs, mas mantém os filtros.
logging.getLogger("uvicorn.access").addFilter(SemIpNoRegisto())


class CacheDoPedido:
    """Em cada pedido, a assinatura da conta lê-se uma só vez (limites._ASSINATURAS_DO_PEDIDO): o plano,
    o "hoje", a moeda e o país (língua das mensagens e da IA) vêm todos da mesma leitura.

    Middleware ASGI simples: abre a memória antes da rota e esquece-a no fim. Cada pedido tem a sua.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        token = abrir_cache_do_pedido()
        try:
            await self.app(scope, receive, send)
        finally:
            fechar_cache_do_pedido(token)


app.add_middleware(CacheDoPedido)


def erro_no_pais(user_id: str, status: int, chave: str, **valores) -> HTTPException:
    """O HTTPException com a mensagem (mensagens.py) no país da conta. Para os caminhos de erro das rotas com sessão."""
    return HTTPException(status_code=status, detail=msg(chave, local_do_utilizador(user_id).pais, **valores))

# Os endereços do frontend (FRONTEND_URL); no deploy junta-se o da Vercel, separado por vírgula.
# Servem para o CORS e para validar o regresso do login com o Google.
ORIGENS_FRONTEND = [
    origem.strip().rstrip("/")
    for origem in os.getenv("FRONTEND_URL", "http://localhost:3000").split(",")
    # Só origens completas: uma entrada vazia ou "/" não pode virar uma origem aceite.
    if origem.strip().startswith(("http://", "https://"))
]

# CORS: diz ao browser que o frontend (noutro endereço) pode chamar esta API.
# Só os endereços do FRONTEND_URL são aceites.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS_FRONTEND,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def inicio():
    return {"message": "A API de finanças está funcionando!"}


# As rotas públicas de entrada e registo contam os pedidos por IP (e por /48 no IPv6) antes de falarem
# com o Supabase: acima do limite, 429 com o "detail" a explicar (ver limite_ip.py).
# Além do limite por IP, cada conta aguenta poucas tentativas falhadas (LIMITE_LOGIN_POR_EMAIL): por (email, rede)
# e por email num dia, contra quem experimenta palavras-passe na mesma conta. A tentativa conta-se antes de falar
# com o Supabase e só fica contada se o Supabase responder "invalid_credentials" (email ou palavra-passe
# errados): login certo, email por confirmar, limites e erros do próprio Supabase devolvem-na.
@app.post("/login", dependencies=[Depends(LIMITE_LOGIN)])
def login(credenciais: Credenciais, request: Request):
    reserva = LIMITE_LOGIN_POR_EMAIL.reservar(credenciais.email, ip_do_pedido(request))
    try:
        token = fazer_login(credenciais.email, credenciais.password)
    except AuthApiError as erro:
        # Conta criada no registo, mas o link do email de confirmação ainda não foi aberto.
        if erro.code != "invalid_credentials":
            LIMITE_LOGIN_POR_EMAIL.devolver(reserva)
        if erro.code == "email_not_confirmed":
            raise HTTPException(
                status_code=401,
                detail="Ainda não confirmaste o email. Abre o link que te enviámos para ativar a conta.",
            )
        raise HTTPException(status_code=401, detail="Email ou palavra-passe errados")
    except Exception:
        LIMITE_LOGIN_POR_EMAIL.devolver(reserva)
        raise
    LIMITE_LOGIN_POR_EMAIL.devolver(reserva)
    return {"access_token": token, "token_type": "bearer"}


# Login com o Google (pública): devolve o endereço do Supabase para onde o browser deve ir.
# O destino tem de ser a página /login/google de um dos endereços do FRONTEND_URL,
# senão qualquer site podia usar este link para receber o código de quem faz login.
# code_challenge: o SHA-256 do segredo PKCE que ficou no browser (ver auth.py); sem ele não há login.
@app.get("/login/google", dependencies=[Depends(LIMITE_GOOGLE_INICIO)])
def login_google(destino: str | None = None, code_challenge: str | None = None):
    if not destino or not destino_google_valido(destino, ORIGENS_FRONTEND):
        raise HTTPException(status_code=400, detail="Destino do login inválido")
    if not code_challenge or not re.fullmatch(FORMATO_CODE_CHALLENGE, code_challenge):
        raise HTTPException(status_code=400, detail="Pedido de login inválido")
    return {"url": url_login_google(destino, code_challenge)}


# Regresso do Google (pública): troca o ?code= pelo token, com o segredo PKCE guardado no browser.
# Responde como o login com email. Erros sempre genéricos: os detalhes do Supabase ficam só nos logs.
MENSAGEM_ERRO_GOOGLE = "Não foi possível entrar com o Google. Tenta outra vez."
CAMINHO_TROCA_GOOGLE = "/login/google/troca"


# Nas rotas que recebem segredos (palavra-passe, código e segredo do Google), um corpo inválido responde 422
# com uma mensagem genérica: o 422 normal do FastAPI repetia o que foi enviado (incluindo a palavra-passe)
# e mostrava os formatos aceites. As outras rotas continuam com o 422 normal.
MENSAGEM_LOGIN_INVALIDO = "Confirma o email e a palavra-passe."
MENSAGEM_REGISTO_INVALIDO = "Confirma que o email está bem escrito e que a palavra-passe tem entre 8 e 72 caracteres."
# A lista de espera não recebe segredos, mas recebe um email: o 422 também não o repete.
# Os textos da lista de espera estão em português do Brasil (página /brasil), aprovados pelo copywriter.
MENSAGEM_LISTA_ESPERA_INVALIDA = "Confira se o email está correto e se você marcou a caixa de consentimento."
CAMINHO_LISTA_ESPERA = "/lista-espera"
MENSAGENS_422_GENERICAS = {
    CAMINHO_TROCA_GOOGLE: MENSAGEM_ERRO_GOOGLE,
    "/login": MENSAGEM_LOGIN_INVALIDO,
    "/registo": MENSAGEM_REGISTO_INVALIDO,
    CAMINHO_LISTA_ESPERA: MENSAGEM_LISTA_ESPERA_INVALIDA,
}


@app.exception_handler(RequestValidationError)
async def erro_de_validacao(request: Request, erro: RequestValidationError):
    mensagem = MENSAGENS_422_GENERICAS.get(request.url.path)
    if mensagem is not None:
        return JSONResponse(status_code=422, content={"detail": mensagem})
    try:
        return await request_validation_exception_handler(request, erro)
    except ValueError:
        # Um valor que o JSON não aceita (NaN, Infinity) no "input" do erro: devolve-se o erro sem o valor,
        # em vez de um 500 sem CORS.
        sem_valores = [{k: v for k, v in e.items() if k not in ("input", "ctx")} for e in erro.errors()]
        return JSONResponse(status_code=422, content={"detail": sem_valores})


@app.post(CAMINHO_TROCA_GOOGLE, dependencies=[Depends(LIMITE_GOOGLE_TROCA)])
def login_google_troca(troca: TrocaGoogle):
    try:
        sessao = trocar_codigo_google(troca.code, troca.code_verifier)
    except AuthApiError as erro:
        # Código já usado, expirado, inventado ou segredo errado: o Supabase recusa com 4xx.
        print(f"AVISO: troca do código do Google recusada pelo Supabase ({erro.code or erro.status}).")
        raise HTTPException(status_code=401, detail=MENSAGEM_ERRO_GOOGLE)
    except AuthError as erro:
        # Supabase em baixo ou resposta sem sessão: não é culpa do utilizador.
        print(f"AVISO: troca do código do Google falhou ({type(erro).__name__}).")
        raise HTTPException(status_code=503, detail=MENSAGEM_ERRO_GOOGLE)
    except Exception as erro:
        # Qualquer outra falha (ex.: erro de rede do httpx): 503 genérico, nunca um 500 com detalhes.
        print(f"AVISO: troca do código do Google falhou ({type(erro).__name__}).")
        raise HTTPException(status_code=503, detail=MENSAGEM_ERRO_GOOGLE)
    # Origem e perfil do registo: só no primeiro login (a conta Google acabou de ser criada).
    # A origem só se escreve se ainda estiver vazia; o perfil (país, bancos, moeda) só se vier no pedido.
    if sessao.conta_nova:
        guardar_origem(sessao.user_id, troca.origem)
        guardar_perfil_inicial(sessao.user_id, troca.perfil_pedido())
    return {"access_token": sessao.token, "token_type": "bearer"}


# Demo para recrutadores (pública): entrega um token da conta de demo, só de leitura (ver demo.py).
# No primeiro pedido de cada semana, os dados inventados voltam ao estado inicial; se isso falhar, entra na mesma.


@app.post("/demo")
def entrar_na_demo(request: Request):
    config = config_demo()
    if not config.ligada:
        raise HTTPException(status_code=503, detail=MENSAGEM_DEMO_DESLIGADA)
    registar_forma_do_ip(request)
    registar_entrada_demo(ip_do_pedido(request))
    garantir_dados_da_semana(config)
    return {"access_token": criar_token_demo(config), "token_type": "bearer"}


# Registo público: qualquer pessoa cria conta e entra no plano Free (gatilho no Supabase).
# A conta só fica ativa depois de a pessoa carregar no link do email de confirmação.
@app.post("/registo", status_code=201, dependencies=[Depends(LIMITE_REGISTO)])
def registo(conta: NovaConta):
    try:
        user_id = fazer_registo(conta.email, conta.password)
    except AuthApiError as erro:
        # Só o código do erro: a mensagem do Supabase pode trazer o email.
        print(f"AVISO: registo recusado pelo Supabase ({erro.code or erro.status}).")
        raise HTTPException(status_code=400, detail="Não foi possível criar a conta. Confirma o email e a palavra-passe.")
    except Exception as erro:
        # Supabase em baixo ou erro de rede: 503 genérico, nunca um 500 com detalhes (só o tipo no log).
        print(f"AVISO: registo falhou ({type(erro).__name__}).")
        raise HTTPException(status_code=503, detail="Não foi possível criar a conta agora. Tenta mais tarde.")
    # O canal de onde a pessoa veio (utm_source). Se falhar, o registo segue (só um aviso no log).
    guardar_origem(user_id, conta.origem)
    # O perfil escolhido no registo (país, países dos bancos, moeda). Só em conta acabada de criar (o user_id
    # vem None nas outras, ver fazer_registo). Se falhar, a conta fica PT/EUR e muda-se nas definições.
    guardar_perfil_inicial(user_id, conta.perfil_pedido())
    # A mesma resposta exista ou não uma conta com este email: assim ninguém usa o registo
    # para descobrir quem tem conta na app.
    return {"mensagem": "Enviámos um email de confirmação. Abre o link para ativar a conta."}


# Lista de espera do Brasil (pública, página /brasil): só com consentimento (caixa não pré-marcada).
# Como o /registo, não lê token nenhum (nem o da demo): é igual para toda a gente.
# A mesma resposta esteja ou não o email já inscrito, para ninguém usar a rota para descobrir quem se inscreveu.
# O email nunca vai para os logs (só o tipo do erro).
MENSAGEM_LISTA_ESPERA_OK = "Inscrição feita. Avisaremos você por email quando a Control Prices estiver disponível no Brasil."
MENSAGEM_LISTA_ESPERA_FALHOU = "Não foi possível salvar seu email agora. Tente novamente em alguns minutos."


@app.post(CAMINHO_LISTA_ESPERA, status_code=201, dependencies=[Depends(LIMITE_LISTA_ESPERA)])
def lista_de_espera(inscricao: InscricaoListaEspera):
    try:
        inscrever(inscricao.email, inscricao.pais, inscricao.paises_cartoes, inscricao.origem)
    except Exception as erro:
        print(f"AVISO: inscrição na lista de espera falhou ({type(erro).__name__}).")
        raise HTTPException(status_code=503, detail=MENSAGEM_LISTA_ESPERA_FALHOU)
    return {"mensagem": MENSAGEM_LISTA_ESPERA_OK}


# Rota de teste: mostra quem é o utilizador do token enviado.
@app.get("/eu")
def quem_sou_eu(user_id: str = Depends(obter_utilizador_atual)):
    return {"user_id": user_id}


# O que o utilizador tem de escrever para apagar a conta (o frontend pede o mesmo).
CONFIRMACAO_APAGAR_CONTA = "APAGAR"
# Em PT; a resposta vai no país da conta (mensagens.py).
MENSAGEM_SEM_CONFIRMACAO = msg("apagar_conta_sem_confirmacao", "PT")
MENSAGEM_APAGAR_CONTA_FALHOU = msg("apagar_conta_falhou", "PT")


# Apaga a conta de quem está autenticado (só a própria: o id vem do token, nunca do pedido).
# A conta de demo nunca chega aqui: o obter_utilizador_atual responde 423 (fora de PERMISSOES_DEMO).
# obter_utilizador_confirmado: além do token válido, pergunta ao Supabase se a sessão ainda vale (get_user).
@app.delete("/conta", status_code=204)
def apagar_conta(
    pedido: ConfirmacaoApagarConta | None = None, user_id: str = Depends(obter_utilizador_confirmado)
) -> None:
    if pedido is None or pedido.confirmacao != CONFIRMACAO_APAGAR_CONTA:
        raise erro_no_pais(user_id, 400, "apagar_conta_sem_confirmacao")
    # Segunda barreira: mesmo que a lista da demo mude por engano, a conta de demo não se apaga.
    id_demo = config_demo().user_id
    if id_demo is not None and str(user_id).lower() == id_demo:
        raise HTTPException(status_code=423, detail=MENSAGEM_BLOQUEIO_DEMO)
    try:
        apagar_utilizador(user_id)
    except Exception as erro:
        # Só o tipo no log: a mensagem do Supabase pode trazer dados da conta.
        print(f"AVISO: apagar conta falhou ({type(erro).__name__}).")
        raise erro_no_pais(user_id, 502, "apagar_conta_falhou")
    # O que ficava na memória do servidor sobre esta conta.
    esquecer_recorrentes(user_id)
    esquecer_resumos(user_id)


# Muda o perfil da conta: país onde vive e países dos cartões e contas (livremente) e a moeda principal
# (só com a conta sem dados: 409). Só os campos enviados mudam. Na demo: 423 (fora de PERMISSOES_DEMO).
# Até 10 pedidos por hora por conta (429 acima disso, antes de ler a base de dados): ver limite_ip.py.
@app.put("/conta/perfil")
def mudar_perfil(pedido: PerfilConta, user_id: str = Depends(obter_utilizador_atual)) -> PerfilGuardado:
    contar_mudanca_de_perfil(user_id, pedido.pais)
    perfil = atualizar_perfil(user_id, pedido.pais, pedido.paises_bancos, pedido.moeda)
    return PerfilGuardado(pais=perfil.pais, paises_bancos=list(perfil.paises_bancos), moeda=perfil.moeda)


def contar_mudanca_de_perfil(user_id: str, pais: str | None) -> None:
    """O limite do PUT /conta/perfil (10 por hora por conta), partilhado com as rotas das boas-vindas.
    O 429 vem antes de ler a base de dados: a língua vem do país pedido, se vier."""
    try:
        registar_mudanca_de_perfil(user_id)
    except HTTPException as erro:
        raise HTTPException(status_code=erro.status_code, detail=msg("perfil_muitas_mudancas", pais), headers=erro.headers)


# Questionário de boas-vindas (sql/021) e "O teu perfil" nas definições. A IA não usa estas respostas.
# PUT: grava o país, os bancos e a moeda (como o PUT /conta/perfil; se a moeda não puder mudar, grava o resto
# e devolve um aviso), o motivo e os objetivos, e marca o questionário como feito.
# GET: o perfil e as respostas. DELETE: apaga o motivo e os objetivos.
# O PUT e o DELETE partilham o limite do perfil (10 por hora por conta); o GET só lê e não conta.
# Na demo: 423 nos três (fora de PERMISSOES_DEMO).
# Antes da sql/021: 503, sem gravar nada.
@app.put("/conta/boas-vindas")
def responder_boas_vindas(pedido: RespostasBoasVindas, user_id: str = Depends(obter_utilizador_atual)) -> BoasVindasGuardadas:
    contar_mudanca_de_perfil(user_id, pedido.pais)
    return guardar_respostas(user_id, pedido)


@app.get("/conta/boas-vindas")
def ver_boas_vindas(user_id: str = Depends(obter_utilizador_atual)) -> BoasVindasGuardadas:
    return ler_respostas(user_id)


@app.delete("/conta/boas-vindas", status_code=204)
def apagar_boas_vindas(user_id: str = Depends(obter_utilizador_atual)) -> None:
    contar_mudanca_de_perfil(user_id, None)
    apagar_respostas(user_id)


# A API usa a chave secreta (ignora o RLS), por isso cada rota filtra pelo user_id do token.
# Lista as transações, das mais recentes para as mais antigas. Com ?mes=2026-10, só as desse mês.
@app.get("/transacoes")
def listar_transacoes(
    mes: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    user_id: str = Depends(obter_utilizador_atual),
) -> list[Transacao]:
    def nova_consulta():
        # A consulta monta-se aos bocados, como um WP_Query com argumentos opcionais.
        consulta = supabase.table("transacoes").select("*").eq("user_id", user_id)
        if mes:
            inicio, fim = limites_do_mes(mes)
            consulta = consulta.gte("data", inicio.isoformat()).lt("data", fim.isoformat())
        # O id desempata as transações do mesmo dia, para a ordem ser sempre igual entre páginas.
        return consulta.order("data", desc=True).order("id", desc=True)

    return ler_todas(nova_consulta)


def campos_de_moeda(user_id: str) -> dict[str, str]:
    """{"moeda": ...} com a moeda principal da conta, para juntar a cada movimento ou compra novos.

    Nunca vem do pedido. Vazio antes da sql/020 (a coluna ainda não existe). Depois da 020, um gatilho
    na base de dados põe a mesma moeda de qualquer forma.
    """
    moeda = moeda_da_conta(user_id)
    return {"moeda": moeda} if moeda else {}


def contar_transacoes(user_id: str) -> int:
    """Quantas movimentações o utilizador tem. head=True: o Supabase devolve só o número, sem linhas."""
    resposta = supabase.table("transacoes").select("id", count="exact", head=True).eq("user_id", user_id).execute()
    return resposta.count or 0


# Quantas movimentações estão sem categoria (para o botão "Categorizar"). Só o número, sem as linhas.
@app.get("/transacoes/sem-categoria/contagem")
def contar_sem_categoria(user_id: str = Depends(obter_utilizador_atual)) -> dict[str, int]:
    resposta = (
        supabase.table("transacoes")
        .select("id", count="exact", head=True)
        .eq("user_id", user_id)
        .is_("categoria", "null")
        .execute()
    )
    return {"total": resposta.count or 0}


@app.get("/transacoes/{transacao_id}")
def obter_transacao(transacao_id: IdTransacao, user_id: str = Depends(obter_utilizador_atual)) -> Transacao:
    def nova_consulta():
        return supabase.table("transacoes").select("*").eq("id", transacao_id).eq("user_id", user_id)

    linhas = ler_todas(nova_consulta)
    if not linhas:
        raise erro_no_pais(user_id, 404, "transacao_nao_encontrada")
    return linhas[0]


def exigir_metodo_do_pais(metodo: str, user_id: str) -> None:
    """422 se o método só existe no outro país (MB Way só em PT; Pix e boleto só no BR). Antes de gastar a IA."""
    pais = local_do_utilizador(user_id).pais
    if not metodo_do_pais(metodo, pais):
        raise HTTPException(status_code=422, detail=msg("metodo_de_outro_pais", pais))


# Cria uma movimentação à mão (dinheiro, MB Way...). Sem categoria, a IA escolhe uma.
@app.post("/transacoes", status_code=201)
def criar_transacao(nova: NovaMovimentacao, user_id: str = Depends(obter_utilizador_atual)) -> Transacao:
    exigir_metodo_do_pais(nova.metodo_pagamento, user_id)
    # Antes de gastar um pedido à IA: a conta tem de ter espaço para mais uma.
    exigir_espaco_na_conta(contar_transacoes(user_id), 1, user_id)
    categoria = nova.categoria
    if not categoria and pode_usar_ia(user_id, "categorizar"):
        try:
            # O país dos bancos (contexto da IA) vem da moeda da conta.
            local = local_do_utilizador(user_id)
            categoria = categorizar([TransacaoCriar(**nova.model_dump())], user_id=user_id, local=local)[0]
        except ErroIA as erro:
            # Sem raise: a movimentação grava-se sem categoria, para o utilizador não perder o que escreveu.
            # Fica para o POST /transacoes/categorizar tratar mais tarde.
            print(erro)

    # mode="json" converte a date em texto ("2026-09-20"), que é o que o Supabase aceita.
    # O dono vem sempre do token, nunca do corpo do pedido; a moeda é sempre a principal da conta.
    # Sem nota, a chave nem vai: assim o insert funciona também antes da sql/025.
    dados = (
        nova.model_dump(mode="json", exclude={"nota"} if nova.nota is None else set())
        | {"categoria": categoria, "user_id": user_id}
        | campos_de_moeda(user_id)
    )
    resposta = inserir_movimentacao(dados)
    # As movimentações mudaram: os pagamentos que se repetem voltam a ser calculados.
    esquecer_recorrentes(user_id)
    return resposta.data[0]


def inserir_movimentacao(dados: dict):
    """Grava a movimentação. Antes da sql/025 (sem a coluna nota), grava-a sem a nota e deixa um aviso nos logs:
    perder a nota é melhor do que perder a movimentação que a pessoa escreveu."""
    try:
        return supabase.table("transacoes").insert(dados).execute()
    except APIError as erro:
        if "nota" not in dados or erro.code not in COLUNA_NAO_EXISTE:
            raise
    print("AVISO: coluna transacoes.nota não encontrada (sql/025); movimentação gravada sem a nota.")
    return supabase.table("transacoes").insert({chave: valor for chave, valor in dados.items() if chave != "nota"}).execute()


# O utilizador corrige a categoria escolhida pela IA (ou preenche uma que ficou vazia) e/ou escreve,
# muda ou apaga a nota pessoal (sql/025). A descrição do banco nunca muda (entra no hash_importacao).
# Na demo: 423 (fora de PERMISSOES_DEMO).
@app.patch("/transacoes/{transacao_id}")
def atualizar_transacao(
    transacao_id: IdTransacao, alteracao: TransacaoAtualizar, user_id: str = Depends(obter_utilizador_atual)
) -> Transacao:
    alteracoes = alteracao.alteracoes()
    try:
        resposta = (
            supabase.table("transacoes")
            .update(alteracoes)
            .eq("id", transacao_id)
            .eq("user_id", user_id)
            .execute()
        )
    except APIError as erro:
        # Antes da sql/025 a coluna nota não existe: não se grava nada (nem a categoria que viesse junto).
        if "nota" not in alteracoes or erro.code not in COLUNA_NAO_EXISTE:
            raise
        print("AVISO: coluna transacoes.nota não encontrada (sql/025); a nota não foi guardada.")
        raise erro_no_pais(user_id, 503, "notas_indisponiveis")
    if not resposta.data:
        raise erro_no_pais(user_id, 404, "transacao_nao_encontrada")
    if "categoria" in alteracoes:
        esquecer_recorrentes(user_id)  # a categoria aparece nos pagamentos que se repetem
    return resposta.data[0]


# Apaga uma movimentação do utilizador. Se tiver um talão ligado, a base de dados apaga também
# a compra e os produtos (ON DELETE CASCADE, sql/009_compras.sql).
# De outro utilizador ou inexistente: o mesmo 404, para não revelar que existe.
@app.delete("/transacoes/{transacao_id}", status_code=204)
def apagar_transacao(transacao_id: IdTransacao, user_id: str = Depends(obter_utilizador_atual)) -> None:
    resposta = supabase.table("transacoes").delete().eq("id", transacao_id).eq("user_id", user_id).execute()
    if not resposta.data:
        raise erro_no_pais(user_id, 404, "transacao_nao_encontrada")
    esquecer_recorrentes(user_id)


# Pendentes máximas por clique em "Categorizar": cabem numa chamada à IA sem um prompt enorme.
# Quem tiver mais carrega outra vez (cada clique gasta um pedido).
MAX_PENDENTES_POR_PEDIDO = 300


# Categoriza com IA as transações que ficaram sem categoria (antigas, ou de uma importação em que a IA falhou).
@app.post("/transacoes/categorizar")
def categorizar_pendentes(user_id: str = Depends(obter_utilizador_atual)) -> list[Transacao]:
    # .is_("categoria", "null") é o "WHERE categoria IS NULL" do SQL (o .eq não serve para NULL).
    # Vão as mais recentes primeiro (são as que aparecem no dashboard), no máximo MAX_PENDENTES_POR_PEDIDO.
    resposta = (
        supabase.table("transacoes")
        .select("*")
        .eq("user_id", user_id)
        .is_("categoria", "null")
        .order("data", desc=True)
        .order("id", desc=True)
        .limit(MAX_PENDENTES_POR_PEDIDO)
        .execute()
    )
    pendentes = [Transacao(**linha) for linha in resposta.data]
    if not pendentes:
        return []

    # O lote inteiro vai numa só chamada à IA, por isso conta como uma pergunta.
    registar_pergunta(user_id, "categorizar_pendentes")
    local = local_do_utilizador(user_id)  # a assinatura já foi lida para o limite: sem consulta a mais
    try:
        categorias = categorizar(pendentes, user_id=user_id, local=local)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail=msg("categorizacao_falhou", local.pais))

    atualizadas = []
    for transacao, categoria in zip(pendentes, categorias):
        transacao.categoria = categoria
        dados = {"categoria": categoria}
        resposta = (
            supabase.table("transacoes")
            .update(dados)
            .eq("id", transacao.id)
            .eq("user_id", user_id)
            .execute()
        )
        atualizadas.append(resposta.data[0])
    esquecer_recorrentes(user_id)
    return atualizadas


# Tamanho máximo de um extrato em PDF. Um extrato normal tem bem menos do que isto.
TAMANHO_MAXIMO_PDF = 10 * 1024 * 1024

# Tamanho máximo de um extrato em CSV. Um ano de movimentos em CSV tem uns 100 KB.
TAMANHO_MAXIMO_CSV = 1 * 1024 * 1024

def ler_csv_enviado(csv: bytes, user_id: str) -> list[TransacaoImportada]:
    """Lê o extrato em CSV, sem IA. Responde 422 se for grande demais ou tiver linhas inválidas."""
    if len(csv) > TAMANHO_MAXIMO_CSV:
        raise erro_no_pais(user_id, 422, "csv_grande")
    try:
        # "utf-8-sig" ignora a marca invisível (BOM) que o Excel põe no início dos CSV.
        return ler_extrato(csv.decode("utf-8-sig"))
    except ExtratoGrandeDemais:
        raise erro_no_pais(user_id, 422, "csv_movimentos_a_mais", maximo=MAX_MOVIMENTOS_CSV)
    except UnicodeDecodeError:
        raise erro_no_pais(user_id, 422, "csv_codificacao")
    except ErroImportacao as erro:
        # Nada é gravado: o utilizador corrige o ficheiro e volta a importar.
        raise HTTPException(status_code=422, detail={"mensagem": str(erro), "erros": erro.erros})


def ler_pdf_enviado(pdf: bytes, user_id: str, local: Local = Local()) -> tuple[list[TransacaoImportada], int]:
    """A IA lê o extrato em PDF. Devolve os movimentos lidos e as movimentações que a conta já tinha.

    Todos os planos importam PDF (o Free só 1 por mês, LIMITES_PDF_POR_PLANO em limites.py).
    As verificações vêm por esta ordem, todas antes de gastar o pedido e de chamar a IA:
    422 se for grande demais ou ilegível; 400 se tiver páginas a mais;
    422 se a conta estiver no teto de movimentações; 429 se já chegou ao limite de PDF do mês.
    Só então conta o pedido à IA (e, com ele, o PDF do mês). 503 se a IA falhar.
    local: o país e a moeda da conta (língua das mensagens; o país dos bancos para a IA vem da moeda).
    """
    if len(pdf) > TAMANHO_MAXIMO_PDF:
        raise HTTPException(status_code=422, detail=msg("pdf_grande", local.pais))

    # As páginas contam-se antes de chamar a IA e antes de gastar o pedido: um PDF recusado não custa nada.
    try:
        paginas = contar_paginas_pdf(pdf)
    except PdfIlegivel as erro:
        print(erro)
        raise HTTPException(status_code=422, detail=msg("pdf_ilegivel", local.pais))
    if paginas > MAX_PAGINAS_PDF:
        # Acima do teto a contagem para a meio, por isso não sabemos o número exato.
        quantas = f"mais de {MAX_ENTRADAS_ARVORE_PDF}" if paginas > MAX_ENTRADAS_ARVORE_PDF else str(paginas)
        raise HTTPException(
            status_code=400, detail=msg("pdf_paginas", local.pais, quantas=quantas, maximo=MAX_PAGINAS_PDF)
        )

    # Ainda não se sabe quantos movimentos tem (só a IA o diz), mas uma conta já no teto
    # é recusada antes de gastar o pedido e de pagar a leitura do PDF.
    atuais = contar_transacoes(user_id)
    exigir_espaco_na_conta(atuais, 1, user_id)

    # O PDF foi aceite: só agora se veem o limite de PDF do mês e o de pedidos. Um PDF recusado acima não conta.
    # Ler um PDF é a chamada mais cara da importação: gasta um pedido à IA, registado como "importar_pdf",
    # e é essa linha que conta para o limite de PDF do mês (as duas coisas de uma vez, ver limites.registar_pdf).
    registar_pdf(user_id)
    try:
        extrato = ler_extrato_pdf(pdf, user_id=user_id, local=local)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail=msg("pdf_ia_falhou", local.pais))
    if not extrato.movimentos:
        raise HTTPException(status_code=422, detail=msg("pdf_sem_movimentos", local.pais))
    return transacoes_do_pdf(extrato), atuais


@app.post("/transacoes/importar", status_code=201)
def importar_extrato(ficheiro: UploadFile, user_id: str = Depends(obter_utilizador_atual)) -> ResultadoImportacao:
    # Lê no máximo o limite + 1 byte: um ficheiro enorme não chega a entrar todo na memória.
    conteudo = ficheiro.file.read(TAMANHO_MAXIMO_PDF + 1)

    # Todos os PDF começam por "%PDF": é mais seguro do que confiar no nome do ficheiro.
    eh_pdf = conteudo.startswith(b"%PDF")
    if eh_pdf:
        # O PDF lê sempre a assinatura (plano): o país e a moeda vêm da mesma leitura.
        local = local_do_utilizador(user_id)
        # Plano, tamanho, páginas, teto da conta e limite de PDF: tudo antes de gastar o pedido (ver a função).
        novas, atuais = ler_pdf_enviado(conteudo, user_id, local)
    else:
        novas = ler_csv_enviado(conteudo, user_id)
        atuais = contar_transacoes(user_id)
    if not novas:
        raise erro_no_pais(user_id, 422, "ficheiro_sem_transacoes")

    # Antes de categorizar (no CSV, antes de gastar o pedido). As duplicadas também contam:
    # só se sabe quais são ao gravar.
    exigir_espaco_na_conta(atuais, len(novas), user_id)

    # No PDF o pedido já contou ao ler o ficheiro (ler e categorizar fazem parte da mesma importação).
    # No CSV, a categorização do ficheiro inteiro é uma só chamada à IA: conta como uma pergunta.
    # Sem pedidos, o CSV importa-se na mesma, sem categorias: os dados são do utilizador.
    aviso = None
    if eh_pdf or pode_usar_ia(user_id, "importar_csv"):
        # A assinatura já foi lida (plano e limites): o país e a moeda não custam outra consulta.
        local = local_do_utilizador(user_id)
        try:
            categorias = categorizar(novas, user_id=user_id, local=local)
        except ErroIA as erro:
            print(erro)
            if eh_pdf:
                raise HTTPException(status_code=503, detail=msg("categorizacao_falhou_importar", local.pais))
            # No CSV os dados já estão lidos: gravam-se sem categoria (o pedido fica gasto).
            categorias = [None] * len(novas)
            aviso = msg("importacao_ia_em_baixo", local.pais)
        for nova, categoria in zip(novas, categorias):
            nova.categoria = categoria
    else:
        # Ficam com categoria vazia (NULL): o POST /transacoes/categorizar trata-as mais tarde.
        aviso = msg("importacao_sem_ia", local_do_utilizador(user_id).pais)

    moeda = campos_de_moeda(user_id)
    dados = [nova.model_dump(mode="json") | {"user_id": user_id} | moeda for nova in novas]
    # upsert com ignore_duplicates: as linhas cuja impressão digital já existe são saltadas
    # (ON CONFLICT DO NOTHING), e a resposta traz só as que entraram mesmo.
    resposta = (
        supabase.table("transacoes")
        .upsert(dados, on_conflict="user_id,hash_importacao", ignore_duplicates=True)
        .execute()
    )
    esquecer_recorrentes(user_id)
    return ResultadoImportacao(
        importadas=len(resposta.data),
        duplicadas=len(dados) - len(resposta.data),
        transacoes=resposta.data,
        aviso=aviso,
    )

# Gastos de um mês por categoria, para o gráfico do dashboard. Exemplo: /dashboard/categorias?mes=2026-10
# O pattern faz o FastAPI recusar (422) qualquer coisa que não seja AAAA-MM.
@app.get("/dashboard/categorias")
def dashboard_categorias(
    mes: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), user_id: str = Depends(obter_utilizador_atual)
) -> list[GastoCategoria]:
    return gastos_do_mes(user_id, mes)


# Receitas e despesas de cada mês, para o gráfico da evolução.
@app.get("/dashboard/mensal")
def dashboard_mensal(user_id: str = Depends(obter_utilizador_atual)) -> list[ResumoMensal]:
    linhas = ler_todas(lambda: supabase.table("transacoes").select("data, valor").eq("user_id", user_id).order("id"))
    return resumo_mensal(linhas)


# Chat sobre as finanças: a IA responde usando as ferramentas, sempre com os dados deste utilizador.
@app.post("/chat")
def chat(pedido: PerguntaChat, user_id: str = Depends(obter_utilizador_atual)) -> RespostaChat:
    # Antes de gastar uma chamada à IA: conta a pergunta, ou responde 429 se o limite do plano acabou.
    registar_pergunta(user_id, "chat")
    # O plano vem do servidor: decide a memória, o histórico das ferramentas, o esforço e os tokens.
    plano, config = plano_e_config_ia(user_id)
    # O "hoje" do país onde a pessoa vive: vai nas instruções da IA e decide os meses que as ferramentas veem.
    hoje = hoje_do_utilizador(user_id)
    # A língua (país onde vive) e a moeda: da mesma assinatura já lida no pedido.
    local = local_do_utilizador(user_id)

    # As propostas da IA (criar, alterar, apagar) ficam só nesta lista: a IA nunca grava, quem grava é a pessoa
    # ao confirmar no cartão. Na demo não há propostas (o chat é só de leitura e poupa tokens).
    propostas = None if e_conta_demo(user_id) else PropostasDoPedido(pais=local.pais)

    # Closure: uma função que "lembra" o user_id, o plano e o dia deste pedido. A IA só lhe passa o nome e os argumentos.
    def executar(nome: str, argumentos: dict) -> str:
        return executar_ferramenta(nome, argumentos, user_id, plano, hoje, propostas)

    try:
        # O histórico vem do browser: o conversar() corta-o para a memória do plano (0 no Free).
        resposta = conversar(
            pedido.pergunta,
            ferramentas_para(local, com_propostas=propostas is not None),
            executar,
            user_id=user_id,
            config=config,
            historico=pedido.historico,
            hoje=hoje,
            local=local,
        )
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail=msg("chat_falhou", local.pais))
    return RespostaChat(resposta=resposta, propostas=propostas.lista if propostas else [])


# Resumo do mês escrito pela IA, com alertas. Exemplo: /resumo?mes=2026-10
@app.get("/resumo")
def resumo_do_mes(
    mes: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), user_id: str = Depends(obter_utilizador_atual)
) -> ResumoMes:
    dados = recolher_dados(user_id, mes)
    # Sem transações não há nada para resumir: não vale a pena pagar uma chamada à IA.
    # O texto é o mesmo em PT e BR (assim este caminho não precisa de ler o país da conta).
    if dados["transacoes_no_mes"] == 0:
        return ResumoMes(resumo="Ainda não há transações neste mês.", alertas=[])

    # O dashboard pede o resumo sempre que abre. Se os números não mudaram, o resumo também não:
    # devolve-se o que já foi escrito (tabela resumos_ia), sem pagar outra chamada nem gastar uma pergunta.
    # O país e a moeda entram na impressão digital (o resumo vem na língua e na moeda da conta): mudar de país
    # pede um resumo novo. Em PT/EUR ficam de fora, para os resumos já guardados continuarem a servir.
    local = local_do_utilizador(user_id)
    perfil = {} if (local.pais, local.moeda) == ("PT", "EUR") else {"_pais": local.pais, "_moeda": local.moeda}
    assinatura = assinatura_dos_dados({**dados, **perfil})
    guardado = resumo_guardado(user_id, mes, assinatura)
    if guardado is not None:
        return guardado

    if not pode_usar_ia(user_id, "resumo"):
        return ResumoMes(resumo=aviso_resumo_sem_pedidos(user_id), alertas=[])
    try:
        resumo = resumir_mes(dados, user_id=user_id, config=plano_e_config_ia(user_id)[1], local=local)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail=msg("resumo_falhou", local.pais))
    guardar_resumo(user_id, mes, assinatura, resumo)
    return resumo


# Planeamento do mês: cada categoria com o orçamento (se tiver) e quanto já se gastou.
@app.get("/orcamentos")
def listar_orcamentos(
    mes: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), user_id: str = Depends(obter_utilizador_atual)
) -> list[LinhaOrcamento]:
    return planeamento_do_mes(user_id, mes)


# Alertas de orçamento do mês atual (no país onde a pessoa vive): categorias com 90% ou mais do orçamento gasto.
# Só contas, sem IA: não gasta pedidos. O Planeamento e o dashboard mostram-nos.
@app.get("/orcamentos/alertas")
def alertas_orcamento(user_id: str = Depends(obter_utilizador_atual)) -> AlertasOrcamento:
    # O mês vai na resposta: o frontend só mostra os alertas quando o mês escolhido é este.
    mes_atual = hoje_do_utilizador(user_id).strftime("%Y-%m")
    return AlertasOrcamento(mes=mes_atual, alertas=alertas_de_orcamento(planeamento_do_mes(user_id, mes_atual)))


# Define (ou muda) o orçamento mensal de uma categoria. A categoria no URL tem de ser uma das permitidas.
@app.put("/orcamentos/{categoria}")
def definir_orcamento(
    categoria: Categoria, novo: NovoLimite, user_id: str = Depends(obter_utilizador_atual)
) -> NovoLimite:
    guardar_limite(user_id, categoria, novo.limite)
    return novo


# A IA propõe um orçamento a partir dos últimos 3 meses. Não guarda nada: o utilizador escolhe o que aceita.
@app.post("/orcamentos/sugestao")
def sugestao_orcamento(
    mes: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), user_id: str = Depends(obter_utilizador_atual)
) -> SugestaoOrcamento:
    historico = historico_para_sugestao(user_id, mes)
    if not historico:
        return SugestaoOrcamento(sugestoes=[])
    # Conta para o limite do plano, como as perguntas do chat (cada sugestão é uma chamada à IA).
    registar_pergunta(user_id, "orcamento")
    local = local_do_utilizador(user_id)
    try:
        return sugerir_orcamento(historico, user_id=user_id, config=plano_e_config_ia(user_id)[1], local=local)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail=msg("sugestao_falhou", local.pais))


# Pagamentos que se repetem todos os meses (assinaturas, ginásio...). Só contas, sem IA:
# não gasta pedidos e é de todos os planos. O Planeamento e o dashboard mostram-nos.
@app.get("/recorrentes")
def pagamentos_recorrentes(user_id: str = Depends(obter_utilizador_atual)) -> list[Recorrente]:
    return recorrentes_do_utilizador(user_id, hoje_do_utilizador(user_id))


# Os formatos de imagem que a IA aceita, e o tamanho máximo de cada imagem na API (5 MB).
TIPOS_IMAGEM = {"image/jpeg", "image/png", "image/webp"}
TAMANHO_MAXIMO = 5 * 1024 * 1024


def eh_imagem_suportada(imagem: bytes) -> str | None:
    """O tipo da imagem pelos primeiros bytes ("image/jpeg", "image/png" ou "image/webp"), ou None.

    O content_type vem do browser e pode mentir: é este tipo que vai para a IA.
    """
    if imagem.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if imagem.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if imagem[:4] == b"RIFF" and imagem[8:12] == b"WEBP":  # WebP: RIFF, 4 bytes de tamanho, WEBP
        return "image/webp"
    return None


# A IA lê a fotografia de um talão. Não grava nada: o utilizador revê os produtos antes de guardar.
@app.post("/compras/ler")
def ler_compra(foto: UploadFile, user_id: str = Depends(obter_utilizador_atual)) -> Talao:
    # Ler talões é só dos planos pagos: 402 antes de ler a foto e de gastar um pedido.
    exigir_funcao(user_id, "ler_talao")
    # O plano já leu a assinatura: o país (talão ou nota fiscal) vem da mesma leitura.
    local = local_do_utilizador(user_id)
    imagem = foto.file.read(TAMANHO_MAXIMO + 1)

    if foto.content_type not in TIPOS_IMAGEM:
        raise HTTPException(status_code=422, detail=msg("imagem_formato", local.pais))
    if len(imagem) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=422, detail=msg("imagem_grande", local.pais))
    elif len(imagem) < 1024:
        raise HTTPException(status_code=422, detail=msg("imagem_pequena", local.pais))
    tipo = eh_imagem_suportada(imagem)
    if tipo is None:
        raise HTTPException(status_code=422, detail=msg("imagem_formato", local.pais))

    # Só depois de a foto ser válida é que conta para o limite do plano (uma foto errada não gasta perguntas).
    registar_pergunta(user_id, "talao")
    try:
        talao = ler_talao(imagem, tipo, user_id=user_id, local=local)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail=msg("talao_falhou", local.pais))
    # Pelas regras do prompt, uma foto que não é um talão (ou ilegível) volta sem itens.
    if not talao.itens:
        raise HTTPException(status_code=422, detail=msg("talao_ilegivel", local.pais))
    return talao


# Grava o talão depois de o utilizador o rever: cria a transação com o total, a compra e os produtos.
@app.post("/compras", status_code=201)
def criar_compra(nova: NovaCompra, user_id: str = Depends(obter_utilizador_atual)) -> Compra:
    exigir_metodo_do_pais(nova.metodo_pagamento, user_id)
    # Guardar um talão cria uma transação: conta para o teto de movimentações da conta.
    exigir_espaco_na_conta(contar_transacoes(user_id), 1, user_id)
    compra = gravar_compra(user_id, nova, moeda_da_conta(user_id))
    esquecer_recorrentes(user_id)
    return compra


# As compras guardadas, com os produtos, para a página Minhas compras.
@app.get("/compras")
def lista_de_compras(user_id: str = Depends(obter_utilizador_atual)) -> list[Compra]:
    return listar_compras(user_id)


# Preço de um produto por loja (a partir dos talões). Só nos planos pagos: 402 no Free.
# Os produtos comprados, com pesquisa sem acentos (?q=leite). Máx. 50.
@app.get("/compras/produtos")
def produtos_comprados(
    q: str | None = Query(default=None, max_length=100), user_id: str = Depends(obter_utilizador_atual)
) -> list[ProdutoResumo]:
    exigir_funcao(user_id, "precos_por_loja")
    return produtos_do_utilizador(user_id, q)


# As junções do utilizador, das mais recentes para as mais antigas (para o ecrã as poder desfazer).
# Declarada ANTES de /compras/produtos/{chave}: senão o FastAPI lia "juntar" como a chave de um produto.
@app.get("/compras/produtos/juntar")
def lista_de_juncoes(user_id: str = Depends(obter_utilizador_atual)) -> list[JuncaoProdutos]:
    exigir_funcao(user_id, "precos_por_loja")
    return juncoes_do_utilizador(user_id)


# Os preços unitários de um produto em cada loja e o histórico. 404 se o produto não estiver nas compras.
@app.get("/compras/produtos/{chave}")
def precos_de_um_produto(chave: str, user_id: str = Depends(obter_utilizador_atual)) -> PrecosDoProduto:
    exigir_funcao(user_id, "precos_por_loja")
    if len(chave) > 100:
        raise erro_no_pais(user_id, 404, "produto_nao_encontrado")
    # A mesma normalização das chaves: "Leite Meio-Gordo" encontra "leite meio gordo".
    precos = precos_do_utilizador(user_id, chave_do_produto(chave))
    if precos is None:
        raise erro_no_pais(user_id, 404, "produto_nao_encontrado")
    return precos


# Junta dois produtos que são o mesmo (ex.: "leite meio gordo" e "leite uht meio gordo").
@app.post("/compras/produtos/juntar", status_code=204)
def juntar_dois_produtos(pedido: JuntarProdutos, user_id: str = Depends(obter_utilizador_atual)) -> None:
    exigir_funcao(user_id, "precos_por_loja")
    # O plano já leu a assinatura: o país das mensagens vem da mesma leitura.
    juntar_produtos(user_id, pedido.chave_origem, pedido.chave_destino, local_do_utilizador(user_id).pais)


# Desfaz uma junção: os itens de chave_origem voltam a ser um produto à parte.
@app.delete("/compras/produtos/juntar/{chave_origem}", status_code=204)
def separar_dois_produtos(chave_origem: str, user_id: str = Depends(obter_utilizador_atual)) -> None:
    exigir_funcao(user_id, "precos_por_loja")
    pais = local_do_utilizador(user_id).pais  # da assinatura já lida para o plano
    if len(chave_origem) > 100:
        raise HTTPException(status_code=404, detail=msg("juncao_nao_existe", pais))
    # A chave exata e depois a normalizada (ver separar_produtos).
    separar_produtos(user_id, chave_origem, pais)


# --- Fazer as minhas compras (lista_compras.py, sql/024) ---
# A pessoa dá o orçamento, 1 a 3 mercados e a lista; a IA procura os preços nos sites oficiais e a API calcula
# o plano (o mais barato de cada produto, o total por mercado e o orçamento). Só planos pagos (402 no Free) e
# contas em Portugal (422 nas outras). Limite próprio por mês (429), à parte dos pedidos à IA normais.
# Na demo: um exemplo fixo (dados_demo.py), sem IA, sem pesquisas e sem contar.


def mercados_disponiveis() -> list[MercadoDisponivel]:
    return [MercadoDisponivel(chave=chave, nome=mercado.nome) for chave, mercado in MERCADOS.items()]


@app.get("/compras/lista/estado")
def estado_lista_compras(user_id: str = Depends(obter_utilizador_atual)) -> EstadoListaCompras:
    disponivel, usadas, limite = estado_listas_compras(user_id, contar=not e_conta_demo(user_id))
    return EstadoListaCompras(disponivel=disponivel, usadas=usadas, limite=limite, mercados=mercados_disponiveis())


def exemplo_lista_compras_demo(user_id: str) -> ResultadoListaCompras:
    """O exemplo fixo da demo, pelo mesmo cálculo das listas a sério. Não conta nem chama a IA."""
    _, _, limite = estado_listas_compras(user_id, contar=False)
    itens = limpar_itens(achados_compras_demo(), MERCADOS_COMPRAS_DEMO)
    plano = calcular_plano(itens, MERCADOS_COMPRAS_DEMO, ORCAMENTO_COMPRAS_DEMO)
    return ResultadoListaCompras(**plano, usadas=0, limite=limite, exemplo=True)


@app.post("/compras/lista")
def fazer_lista_compras(pedido: PedidoListaCompras, user_id: str = Depends(obter_utilizador_atual)) -> ResultadoListaCompras:
    # O corpo já foi validado (422) antes de chegar aqui, também na demo.
    if e_conta_demo(user_id):
        return exemplo_lista_compras_demo(user_id)
    exigir_funcao(user_id, "fazer_compras")
    local = local_do_utilizador(user_id)  # da assinatura já lida para o plano
    if local.pais != "PT":
        raise HTTPException(status_code=422, detail=msg("fazer_compras_so_portugal", local.pais))
    # Conta a lista ANTES de chamar a IA (429 no limite; 503 sem a sql/024). Conta mesmo que a IA falhe a seguir.
    limite = registar_lista_compras(user_id)
    try:
        achados = fazer_compras(pedido.lista, pedido.mercados, pedido.orcamento, user_id=user_id, local=local)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail=msg("fazer_compras_indisponivel", local.pais))
    plano = calcular_plano(limpar_itens(achados, pedido.mercados), pedido.mercados, pedido.orcamento)
    return ResultadoListaCompras(**plano, usadas=listas_no_mes(user_id), limite=limite)


# Minha reserva: os objetivos de poupança do utilizador, do prazo mais próximo para o mais distante.
@app.get("/objetivos")
def lista_de_objetivos(user_id: str = Depends(obter_utilizador_atual)) -> list[Objetivo]:
    return listar_objetivos(user_id)


@app.post("/objetivos", status_code=201)
def novo_objetivo(novo: NovoObjetivo, user_id: str = Depends(obter_utilizador_atual)) -> Objetivo:
    return criar_objetivo(user_id, novo)


# "+ Juntei dinheiro": o frontend envia o novo total poupado.
@app.patch("/objetivos/{objetivo_id}")
def mudar_poupado(
    objetivo_id: int, alteracao: PoupadoAtualizar, user_id: str = Depends(obter_utilizador_atual)
) -> Objetivo:
    objetivo = atualizar_poupado(user_id, objetivo_id, alteracao.valor_poupado)
    if objetivo is None:
        raise erro_no_pais(user_id, 404, "objetivo_nao_encontrado")
    return objetivo


# 204 No Content: apagou, e não há nada para devolver.
@app.delete("/objetivos/{objetivo_id}", status_code=204)
def remover_objetivo(objetivo_id: int, user_id: str = Depends(obter_utilizador_atual)) -> None:
    if not apagar_objetivo(user_id, objetivo_id):
        raise erro_no_pais(user_id, 404, "objetivo_nao_encontrado")


# A IA avalia o objetivo (as contas já vêm feitas do objetivos.py). Não guarda nada.
@app.post("/objetivos/{objetivo_id}/plano")
def plano_do_objetivo(objetivo_id: int, user_id: str = Depends(obter_utilizador_atual)) -> PlanoPoupanca:
    objetivo = obter_objetivo(user_id, objetivo_id)
    if objetivo is None:
        raise erro_no_pais(user_id, 404, "objetivo_nao_encontrado")
    dados = dados_do_plano(user_id, objetivo, hoje_do_utilizador(user_id))
    # O "hoje" já leu a assinatura: o país e a moeda vêm da mesma leitura.
    local = local_do_utilizador(user_id)

    # Casos em que a resposta é sempre a mesma: não vale a pena pagar uma chamada à IA.
    if dados["falta"] == 0:
        return PlanoPoupanca(viavel=True, explicacao=msg("objetivo_atingido", local.pais), cortes=[])
    if dados["necessario_por_mes"] is None:
        return PlanoPoupanca(viavel=False, explicacao=msg("objetivo_prazo_terminou", local.pais), cortes=[])
    if not dados["meses_do_saldo_medio"]:
        return PlanoPoupanca(viavel=False, explicacao=msg("objetivo_sem_mes_completo", local.pais), cortes=[])

    registar_pergunta(user_id, "poupanca")
    try:
        return planear_poupanca(dados, user_id=user_id, config=plano_e_config_ia(user_id)[1], local=local)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail=msg("poupanca_falhou", local.pais))


# Simulador de poupança: só contas, sem IA. Exemplo: /simulador?mensal=50&anos=10&taxa=3
# Os limites evitam pedidos sem sentido (e simulações enormes).
@app.get("/simulador")
def simulador(
    mensal: float = Query(gt=0, le=10_000),
    anos: int = Query(ge=1, le=40),
    taxa: float = Query(ge=0, le=15),
    user_id: str = Depends(obter_utilizador_atual),
) -> list[AnoSimulado]:
    return simular_poupanca(mensal, anos, taxa)


# --- Resumo anual (nada fiscal: só as contas das movimentações gravadas) ---


def relatorio_pedido(ano: int, user_id: str) -> RelatorioAnual:
    """O relatório do ano para este utilizador, ou 422 se o ano não for de 2000 até ao ano atual (no seu país).

    Título, aviso, etiquetas e mensagens no país onde a pessoa vive (da assinatura já lida para o "hoje").
    """
    hoje = hoje_do_utilizador(user_id)
    pais = local_do_utilizador(user_id).pais
    if not ano_valido(ano, hoje):
        raise HTTPException(status_code=422, detail=msg("ano_invalido", pais, ano=hoje.year))
    return relatorio_do_ano(user_id, ano, hoje, pais)


# O resumo do ano em JSON, para a página do relatório. Todos os planos; sem IA. Exemplo: /relatorio?ano=2026
# Dados financeiros: nem o browser nem um proxy os guardam em cache.
SEM_CACHE = {"Cache-Control": "no-store"}


@app.get("/relatorio")
def relatorio(ano: int, response: Response, user_id: str = Depends(obter_utilizador_atual)) -> RelatorioAnual:
    response.headers.update(SEM_CACHE)
    return relatorio_pedido(ano, user_id)


# O mesmo relatório em CSV para o Excel (só nos planos pagos: 402 no Free, como os talões).
@app.get("/relatorio/csv")
def relatorio_csv(ano: int, user_id: str = Depends(obter_utilizador_atual)) -> Response:
    exigir_funcao(user_id, "exportar_relatorio")
    local = local_do_utilizador(user_id)  # da assinatura já lida para o plano
    conteudo = relatorio_em_csv(relatorio_pedido(ano, user_id), local.pais, local.moeda)
    return Response(
        content=conteudo,
        media_type="text/csv; charset=utf-8",
        headers=SEM_CACHE
        | {
            "Content-Disposition": f'attachment; filename="relatorio-{ano}.csv"',
            # O browser não tenta adivinhar outro tipo (ex.: abrir o CSV como HTML).
            "X-Content-Type-Options": "nosniff",
        },
    )


# A IA escreve um resumo do ano a partir dos números já calculados. Só no plano Completo (402 nos outros).
# Conta 1 pedido à IA, como as outras funções.
@app.post("/relatorio/resumo-ia")
def relatorio_resumo_ia(ano: int, user_id: str = Depends(obter_utilizador_atual)) -> ResumoAnualIA:
    exigir_funcao(user_id, "resumo_anual_ia")
    dados = relatorio_pedido(ano, user_id)
    local = local_do_utilizador(user_id)  # da assinatura já lida para o plano
    # Sem movimentações no ano não há nada para resumir: não se gasta um pedido.
    if not any(mes.com_dados for mes in dados.meses):
        return ResumoAnualIA(resumo=msg("ano_sem_movimentos", local.pais))
    registar_pergunta(user_id, "resumo_anual")
    try:
        return resumir_ano(dados_para_ia(dados), user_id=user_id, config=plano_e_config_ia(user_id)[1], local=local)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail=msg("resumo_anual_falhou", local.pais))


# O plano do utilizador e quantos pedidos à IA já fez no dia (ou no mês, no Free). O menu lateral mostra-o.
# Só lê: não conta como pergunta.
@app.get("/plano")
def plano(user_id: str = Depends(obter_utilizador_atual)) -> EstadoPlano:
    estado = estado_do_plano(user_id)
    # A demo nunca vê o questionário de boas-vindas (a sql/021 já a marca; isto é a segunda barreira).
    if estado.boas_vindas_pendente and e_conta_demo(user_id):
        estado = estado.model_copy(update={"boas_vindas_pendente": False})
    # Brasil fechado (perfil.py): o frontend só mostra "vivo no Brasil" a quem o pode escolher.
    return estado.model_copy(update={"brasil_disponivel": pode_escolher_brasil(user_id, estado.pais)})


# Os planos à venda e os seus limites (para a página de preços). Público: não precisa de login
# e não mostra dados de ninguém, só o que está em LIMITES_POR_PLANO.
@app.get("/planos")
def planos() -> list[PlanoDisponivel]:
    return planos_disponiveis()
