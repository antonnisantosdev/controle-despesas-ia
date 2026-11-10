import os

from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from supabase import AuthApiError

from auth import destino_google_valido, fazer_login, fazer_registo, obter_utilizador_atual, url_login_google
from compras import gravar_compra, listar_compras
from dashboard import limites_do_mes, resumo_mensal
from consultas import gastos_do_mes
from database import ler_todas, supabase
from ferramentas import FERRAMENTAS, executar_ferramenta
from ia import ErroIA, categorizar, conversar, ler_extrato_pdf, ler_talao, planear_poupanca, resumir_mes, sugerir_orcamento
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
from limites import (
    MAX_PAGINAS_PDF,
    aviso_resumo_sem_pedidos,
    estado_do_plano,
    exigir_espaco_na_conta,
    exigir_funcao,
    exigir_limite_pdf,
    hoje_em_lisboa,
    plano_e_config_ia,
    planos_disponiveis,
    pode_usar_ia,
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
from orcamento import alertas_de_orcamento, guardar_limite, historico_para_sugestao, planeamento_do_mes
from models import (
    AlertasOrcamento,
    AnoSimulado,
    EstadoPlano,
    Categoria,
    CategoriaAtualizar,
    Compra,
    Credenciais,
    NovaConta,
    GastoCategoria,
    LinhaOrcamento,
    NovaCompra,
    NovaMovimentacao,
    NovoLimite,
    NovoObjetivo,
    Objetivo,
    PerguntaChat,
    PlanoDisponivel,
    PlanoPoupanca,
    PoupadoAtualizar,
    Recorrente,
    RespostaChat,
    ResultadoImportacao,
    ResumoMes,
    SugestaoOrcamento,
    ResumoMensal,
    Talao,
    Transacao,
    TransacaoCriar,
    TransacaoImportada,
)
from recorrentes import esquecer_recorrentes, recorrentes_do_utilizador
from resumo import assinatura_dos_dados, guardar_resumo, recolher_dados, resumo_guardado
from simulador import simular_poupanca

app = FastAPI()

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


@app.post("/login")
def login(credenciais: Credenciais):
    try:
        token = fazer_login(credenciais.email, credenciais.password)
    except AuthApiError as erro:
        # Conta criada no registo, mas o link do email de confirmação ainda não foi aberto.
        if erro.code == "email_not_confirmed":
            raise HTTPException(
                status_code=401,
                detail="Ainda não confirmaste o email. Abre o link que te enviámos para ativar a conta.",
            )
        raise HTTPException(status_code=401, detail="Email ou palavra-passe errados")
    return {"access_token": token, "token_type": "bearer"}


# Login com o Google (pública): devolve o endereço do Supabase para onde o browser deve ir.
# O destino tem de ser a página /login/google de um dos endereços do FRONTEND_URL,
# senão qualquer site podia usar este link para receber o token de quem faz login.
@app.get("/login/google")
def login_google(destino: str | None = None):
    if not destino or not destino_google_valido(destino, ORIGENS_FRONTEND):
        raise HTTPException(status_code=400, detail="Destino do login inválido")
    return {"url": url_login_google(destino)}


# Registo público: qualquer pessoa cria conta e entra no plano Free (gatilho no Supabase).
# A conta só fica ativa depois de a pessoa carregar no link do email de confirmação.
@app.post("/registo", status_code=201)
def registo(conta: NovaConta):
    try:
        fazer_registo(conta.email, conta.password)
    except AuthApiError as erro:
        print(erro)
        raise HTTPException(status_code=400, detail="Não foi possível criar a conta. Confirma o email e a palavra-passe.")
    # A mesma resposta exista ou não uma conta com este email: assim ninguém usa o registo
    # para descobrir quem tem conta na app.
    return {"mensagem": "Enviámos um email de confirmação. Abre o link para ativar a conta."}


# Rota de teste: mostra quem é o utilizador do token enviado.
@app.get("/eu")
def quem_sou_eu(user_id: str = Depends(obter_utilizador_atual)):
    return {"user_id": user_id}


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
def obter_transacao(transacao_id: int, user_id: str = Depends(obter_utilizador_atual)) -> Transacao:
    def nova_consulta():
        return supabase.table("transacoes").select("*").eq("id", transacao_id).eq("user_id", user_id)

    linhas = ler_todas(nova_consulta)
    if not linhas:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    return linhas[0]


# Cria uma movimentação à mão (dinheiro, MB Way...). Sem categoria, a IA escolhe uma.
@app.post("/transacoes", status_code=201)
def criar_transacao(nova: NovaMovimentacao, user_id: str = Depends(obter_utilizador_atual)) -> Transacao:
    # Antes de gastar um pedido à IA: a conta tem de ter espaço para mais uma.
    exigir_espaco_na_conta(contar_transacoes(user_id), 1)
    categoria = nova.categoria
    if not categoria and pode_usar_ia(user_id, "categorizar"):
        try:
            categoria = categorizar([TransacaoCriar(**nova.model_dump())], user_id=user_id)[0]
        except ErroIA as erro:
            # Sem raise: a movimentação grava-se sem categoria, para o utilizador não perder o que escreveu.
            # Fica para o POST /transacoes/categorizar tratar mais tarde.
            print(erro)

    # mode="json" converte a date em texto ("2026-09-20"), que é o que o Supabase aceita.
    # O dono vem sempre do token, nunca do corpo do pedido.
    dados = nova.model_dump(mode="json") | {"categoria": categoria, "user_id": user_id}
    resposta = supabase.table("transacoes").insert(dados).execute()
    # As movimentações mudaram: os pagamentos que se repetem voltam a ser calculados.
    esquecer_recorrentes(user_id)
    return resposta.data[0]


# O utilizador corrige a categoria escolhida pela IA (ou preenche uma que ficou vazia).
@app.patch("/transacoes/{transacao_id}")
def corrigir_categoria(
    transacao_id: int, alteracao: CategoriaAtualizar, user_id: str = Depends(obter_utilizador_atual)
) -> Transacao:
    resposta = (
        supabase.table("transacoes")
        .update({"categoria": alteracao.categoria})
        .eq("id", transacao_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resposta.data:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    esquecer_recorrentes(user_id)  # a categoria aparece nos pagamentos que se repetem
    return resposta.data[0]


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
    try:
        categorias = categorizar(pendentes, user_id=user_id)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail="A categorização automática falhou. Tenta mais tarde.")

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

AVISO_IMPORTACAO_SEM_IA = (
    "Importámos as movimentações sem categorias porque chegaste ao limite de pedidos à IA. "
    "Podes categorizá-las mais tarde."
)

AVISO_IMPORTACAO_IA_EM_BAIXO = (
    "Importámos as movimentações sem categorias porque a IA não respondeu. Podes categorizá-las mais tarde."
)


def ler_csv_enviado(csv: bytes) -> list[TransacaoImportada]:
    """Lê o extrato em CSV, sem IA. Responde 422 se for grande demais ou tiver linhas inválidas."""
    if len(csv) > TAMANHO_MAXIMO_CSV:
        raise HTTPException(status_code=422, detail="CSV demasiado grande. Máx. 1 MB.")
    try:
        # "utf-8-sig" ignora a marca invisível (BOM) que o Excel põe no início dos CSV.
        return ler_extrato(csv.decode("utf-8-sig"))
    except ExtratoGrandeDemais:
        raise HTTPException(
            status_code=422,
            detail=f"Este extrato tem mais de {MAX_MOVIMENTOS_CSV} movimentos. Divide-o em partes mais pequenas.",
        )
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422,
            detail="Não consegui ler o CSV. Grava-o com a codificação UTF-8 e tenta outra vez.",
        )
    except ErroImportacao as erro:
        # Nada é gravado: o utilizador corrige o ficheiro e volta a importar.
        raise HTTPException(status_code=422, detail={"mensagem": str(erro), "erros": erro.erros})


def ler_pdf_enviado(pdf: bytes, user_id: str) -> tuple[list[TransacaoImportada], int]:
    """A IA lê o extrato em PDF. Devolve os movimentos lidos e as movimentações que a conta já tinha.

    As verificações vêm por esta ordem, todas antes de gastar o pedido e de chamar a IA:
    402 no Free; 422 se for grande demais ou ilegível; 400 se tiver páginas a mais;
    422 se a conta estiver no teto de movimentações; 429 se já chegou ao limite de PDF do mês.
    Só então conta o pedido à IA (e, com ele, o PDF do mês). 503 se a IA falhar.
    """
    # Primeiro o plano: o Free nem chega a ter o ficheiro analisado.
    exigir_funcao(user_id, "importar_pdf")
    if len(pdf) > TAMANHO_MAXIMO_PDF:
        raise HTTPException(status_code=422, detail="PDF demasiado grande. Máx. 10 MB.")

    # As páginas contam-se antes de chamar a IA e antes de gastar o pedido: um PDF recusado não custa nada.
    try:
        paginas = contar_paginas_pdf(pdf)
    except PdfIlegivel as erro:
        print(erro)
        raise HTTPException(status_code=422, detail="Não consegui ler o PDF. Se tiver palavra-passe, tira-a.")
    if paginas > MAX_PAGINAS_PDF:
        # Acima do teto a contagem para a meio, por isso não sabemos o número exato.
        quantas = f"mais de {MAX_ENTRADAS_ARVORE_PDF}" if paginas > MAX_ENTRADAS_ARVORE_PDF else str(paginas)
        raise HTTPException(
            status_code=400,
            detail=(
                f"Este PDF tem {quantas} páginas. O máximo é {MAX_PAGINAS_PDF}. "
                "Divide o extrato em partes mais pequenas."
            ),
        )

    # Ainda não se sabe quantos movimentos tem (só a IA o diz), mas uma conta já no teto
    # é recusada antes de gastar o pedido e de pagar a leitura do PDF.
    atuais = contar_transacoes(user_id)
    exigir_espaco_na_conta(atuais, 1)

    # O PDF foi aceite: só agora se vê o limite de PDF do mês. Um PDF recusado acima não conta.
    exigir_limite_pdf(user_id)

    # Ler um PDF é a chamada mais cara da importação: gasta um pedido à IA, registado como "importar_pdf",
    # e é essa linha que conta para o limite de PDF do mês.
    registar_pergunta(user_id, "importar_pdf")
    try:
        extrato = ler_extrato_pdf(pdf, user_id=user_id)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(
            status_code=503, detail="Não consegui ler o PDF. Se tiver palavra-passe, tira-a. Senão, tenta mais tarde."
        )
    if not extrato.movimentos:
        raise HTTPException(status_code=422, detail="Não encontrei movimentos neste PDF. Confirma que é um extrato bancário.")
    return transacoes_do_pdf(extrato), atuais


@app.post("/transacoes/importar", status_code=201)
def importar_extrato(ficheiro: UploadFile, user_id: str = Depends(obter_utilizador_atual)) -> ResultadoImportacao:
    # Lê no máximo o limite + 1 byte: um ficheiro enorme não chega a entrar todo na memória.
    conteudo = ficheiro.file.read(TAMANHO_MAXIMO_PDF + 1)

    # Todos os PDF começam por "%PDF": é mais seguro do que confiar no nome do ficheiro.
    eh_pdf = conteudo.startswith(b"%PDF")
    if eh_pdf:
        # Plano, tamanho, páginas, teto da conta e limite de PDF: tudo antes de gastar o pedido (ver a função).
        novas, atuais = ler_pdf_enviado(conteudo, user_id)
    else:
        novas = ler_csv_enviado(conteudo)
        atuais = contar_transacoes(user_id)
    if not novas:
        raise HTTPException(status_code=422, detail="O ficheiro não tem transações")

    # Antes de categorizar (no CSV, antes de gastar o pedido). As duplicadas também contam:
    # só se sabe quais são ao gravar.
    exigir_espaco_na_conta(atuais, len(novas))

    # No PDF o pedido já contou ao ler o ficheiro (ler e categorizar fazem parte da mesma importação).
    # No CSV, a categorização do ficheiro inteiro é uma só chamada à IA: conta como uma pergunta.
    # Sem pedidos, o CSV importa-se na mesma, sem categorias: os dados são do utilizador.
    aviso = None
    if eh_pdf or pode_usar_ia(user_id, "importar_csv"):
        try:
            categorias = categorizar(novas, user_id=user_id)
        except ErroIA as erro:
            print(erro)
            if eh_pdf:
                raise HTTPException(
                    status_code=503, detail="A categorização automática falhou. Tenta importar mais tarde."
                )
            # No CSV os dados já estão lidos: gravam-se sem categoria (o pedido fica gasto).
            categorias = [None] * len(novas)
            aviso = AVISO_IMPORTACAO_IA_EM_BAIXO
        for nova, categoria in zip(novas, categorias):
            nova.categoria = categoria
    else:
        # Ficam com categoria vazia (NULL): o POST /transacoes/categorizar trata-as mais tarde.
        aviso = AVISO_IMPORTACAO_SEM_IA

    dados = [nova.model_dump(mode="json") | {"user_id": user_id} for nova in novas]
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

    # Closure: uma função que "lembra" o user_id e o plano deste pedido. A IA só lhe passa o nome e os argumentos.
    def executar(nome: str, argumentos: dict) -> str:
        return executar_ferramenta(nome, argumentos, user_id, plano)

    try:
        # O histórico vem do browser: o conversar() corta-o para a memória do plano (0 no Free).
        resposta = conversar(
            pedido.pergunta, FERRAMENTAS, executar, user_id=user_id, config=config, historico=pedido.historico
        )
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail="O chat falhou. Tenta mais tarde.")
    return RespostaChat(resposta=resposta)


# Resumo do mês escrito pela IA, com alertas. Exemplo: /resumo?mes=2026-10
@app.get("/resumo")
def resumo_do_mes(
    mes: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), user_id: str = Depends(obter_utilizador_atual)
) -> ResumoMes:
    dados = recolher_dados(user_id, mes)
    # Sem transações não há nada para resumir: não vale a pena pagar uma chamada à IA.
    if dados["transacoes_no_mes"] == 0:
        return ResumoMes(resumo="Ainda não há transações neste mês.", alertas=[])

    # O dashboard pede o resumo sempre que abre. Se os números não mudaram, o resumo também não:
    # devolve-se o que já foi escrito (tabela resumos_ia), sem pagar outra chamada nem gastar uma pergunta.
    assinatura = assinatura_dos_dados(dados)
    guardado = resumo_guardado(user_id, mes, assinatura)
    if guardado is not None:
        return guardado

    if not pode_usar_ia(user_id, "resumo"):
        return ResumoMes(resumo=aviso_resumo_sem_pedidos(user_id), alertas=[])
    try:
        resumo = resumir_mes(dados, user_id=user_id, config=plano_e_config_ia(user_id)[1])
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail="O resumo automático falhou. Tenta mais tarde.")
    guardar_resumo(user_id, mes, assinatura, resumo)
    return resumo


# Planeamento do mês: cada categoria com o orçamento (se tiver) e quanto já se gastou.
@app.get("/orcamentos")
def listar_orcamentos(
    mes: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), user_id: str = Depends(obter_utilizador_atual)
) -> list[LinhaOrcamento]:
    return planeamento_do_mes(user_id, mes)


# Alertas de orçamento do mês atual (de Lisboa): categorias com 90% ou mais do orçamento gasto.
# Só contas, sem IA: não gasta pedidos. O Planeamento e o dashboard mostram-nos.
@app.get("/orcamentos/alertas")
def alertas_orcamento(user_id: str = Depends(obter_utilizador_atual)) -> AlertasOrcamento:
    # O mês vai na resposta: o frontend só mostra os alertas quando o mês escolhido é este.
    mes_atual = hoje_em_lisboa().strftime("%Y-%m")
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
    try:
        return sugerir_orcamento(historico, user_id=user_id, config=plano_e_config_ia(user_id)[1])
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail="A sugestão automática falhou. Tenta mais tarde.")


# Pagamentos que se repetem todos os meses (assinaturas, ginásio...). Só contas, sem IA:
# não gasta pedidos e é de todos os planos. O Planeamento e o dashboard mostram-nos.
@app.get("/recorrentes")
def pagamentos_recorrentes(user_id: str = Depends(obter_utilizador_atual)) -> list[Recorrente]:
    return recorrentes_do_utilizador(user_id, hoje_em_lisboa())


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
    imagem = foto.file.read(TAMANHO_MAXIMO + 1)

    if foto.content_type not in TIPOS_IMAGEM:
        raise HTTPException(status_code=422, detail="Formato de imagem não suportado. Usa JPEG, PNG ou WebP.")
    if len(imagem) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=422, detail="Imagem demasiado grande. Máx. 5 MB.")
    elif len(imagem) < 1024:
        raise HTTPException(status_code=422, detail="Imagem demasiado pequena. Tenta outra fotografia.")
    tipo = eh_imagem_suportada(imagem)
    if tipo is None:
        raise HTTPException(status_code=422, detail="Formato de imagem não suportado. Usa JPEG, PNG ou WebP.")

    # Só depois de a foto ser válida é que conta para o limite do plano (uma foto errada não gasta perguntas).
    registar_pergunta(user_id, "talao")
    try:
        talao = ler_talao(imagem, tipo, user_id=user_id)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail="A leitura do talão falhou. Tenta mais tarde.")
    # Pelas regras do prompt, uma foto que não é um talão (ou ilegível) volta sem itens.
    if not talao.itens:
        raise HTTPException(status_code=422, detail="Não consegui ler o talão. Tenta outra fotografia, com mais luz.")
    return talao


# Grava o talão depois de o utilizador o rever: cria a transação com o total, a compra e os produtos.
@app.post("/compras", status_code=201)
def criar_compra(nova: NovaCompra, user_id: str = Depends(obter_utilizador_atual)) -> Compra:
    # Guardar um talão cria uma transação: conta para o teto de movimentações da conta.
    exigir_espaco_na_conta(contar_transacoes(user_id), 1)
    compra = gravar_compra(user_id, nova)
    esquecer_recorrentes(user_id)
    return compra


# As compras guardadas, com os produtos, para a página Minhas compras.
@app.get("/compras")
def lista_de_compras(user_id: str = Depends(obter_utilizador_atual)) -> list[Compra]:
    return listar_compras(user_id)


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
        raise HTTPException(status_code=404, detail="Objetivo não encontrado")
    return objetivo


# 204 No Content: apagou, e não há nada para devolver.
@app.delete("/objetivos/{objetivo_id}", status_code=204)
def remover_objetivo(objetivo_id: int, user_id: str = Depends(obter_utilizador_atual)) -> None:
    if not apagar_objetivo(user_id, objetivo_id):
        raise HTTPException(status_code=404, detail="Objetivo não encontrado")


# A IA avalia o objetivo (as contas já vêm feitas do objetivos.py). Não guarda nada.
@app.post("/objetivos/{objetivo_id}/plano")
def plano_do_objetivo(objetivo_id: int, user_id: str = Depends(obter_utilizador_atual)) -> PlanoPoupanca:
    objetivo = obter_objetivo(user_id, objetivo_id)
    if objetivo is None:
        raise HTTPException(status_code=404, detail="Objetivo não encontrado")
    dados = dados_do_plano(user_id, objetivo, hoje_em_lisboa())

    # Casos em que a resposta é sempre a mesma: não vale a pena pagar uma chamada à IA.
    if dados["falta"] == 0:
        return PlanoPoupanca(viavel=True, explicacao="Já atingiste este objetivo. Parabéns!", cortes=[])
    if dados["necessario_por_mes"] is None:
        return PlanoPoupanca(
            viavel=False, explicacao="O prazo deste objetivo já terminou. Escolhe uma nova data para voltar a planear.", cortes=[]
        )
    if not dados["meses_do_saldo_medio"]:
        return PlanoPoupanca(
            viavel=False,
            explicacao="Ainda não tens um mês completo de movimentações, por isso não consigo calcular a tua poupança média.",
            cortes=[],
        )

    registar_pergunta(user_id, "poupanca")
    try:
        return planear_poupanca(dados, user_id=user_id, config=plano_e_config_ia(user_id)[1])
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail="O plano de poupança falhou. Tenta mais tarde.")


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


# O plano do utilizador e quantos pedidos à IA já fez no dia (ou no mês, no Free). O menu lateral mostra-o.
# Só lê: não conta como pergunta.
@app.get("/plano")
def plano(user_id: str = Depends(obter_utilizador_atual)) -> EstadoPlano:
    return estado_do_plano(user_id)


# Os planos à venda e os seus limites (para a página de preços). Público: não precisa de login
# e não mostra dados de ninguém, só o que está em LIMITES_POR_PLANO.
@app.get("/planos")
def planos() -> list[PlanoDisponivel]:
    return planos_disponiveis()
