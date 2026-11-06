import os
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from supabase import AuthApiError

from auth import fazer_login, obter_utilizador_atual
from compras import gravar_compra, listar_compras
from dashboard import limites_do_mes, resumo_mensal
from consultas import gastos_do_mes
from database import supabase
from ferramentas import FERRAMENTAS, executar_ferramenta
from ia import ErroIA, categorizar, conversar, ler_extrato_pdf, ler_talao, planear_poupanca, resumir_mes, sugerir_orcamento
from importar_csv import ErroImportacao, ler_extrato, transacoes_do_pdf
from limites import registar_pergunta
from objetivos import (
    apagar_objetivo,
    atualizar_poupado,
    criar_objetivo,
    dados_do_plano,
    listar_objetivos,
    obter_objetivo,
)
from orcamento import guardar_limite, historico_para_sugestao, planeamento_do_mes
from models import (
    Categoria,
    CategoriaAtualizar,
    Compra,
    Credenciais,
    GastoCategoria,
    LinhaOrcamento,
    NovaCompra,
    NovaMovimentacao,
    NovoLimite,
    NovoObjetivo,
    Objetivo,
    PerguntaChat,
    PlanoPoupanca,
    PoupadoAtualizar,
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
from resumo import recolher_dados

app = FastAPI()

# CORS: diz ao browser que o frontend (noutro endereço) pode chamar esta API.
# Só os endereços do FRONTEND_URL são aceites; no deploy junta-se o da Vercel, separado por vírgula.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONTEND_URL", "http://localhost:3000").split(","),
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
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Email ou palavra-passe errados")
    return {"access_token": token, "token_type": "bearer"}


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
    # A consulta monta-se aos bocados, como um WP_Query com argumentos opcionais.
    consulta = supabase.table("transacoes").select("*").eq("user_id", user_id)

    if mes:
        inicio, fim = limites_do_mes(mes)
        consulta = consulta.gte("data", inicio.isoformat()).lt("data", fim.isoformat())

    resposta = consulta.order("data", desc=True).execute()
    return resposta.data


@app.get("/transacoes/{transacao_id}")
def obter_transacao(transacao_id: int, user_id: str = Depends(obter_utilizador_atual)) -> Transacao:
    resposta = supabase.table("transacoes").select("*").eq("id", transacao_id).eq("user_id", user_id).execute()
    if not resposta.data:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    return resposta.data[0]


# Cria uma movimentação à mão (dinheiro, MB Way...). Sem categoria, a IA escolhe uma.
@app.post("/transacoes", status_code=201)
def criar_transacao(nova: NovaMovimentacao, user_id: str = Depends(obter_utilizador_atual)) -> Transacao:
    categoria = nova.categoria
    if not categoria:
        try:
            categoria = categorizar([TransacaoCriar(**nova.model_dump())])[0]
        except ErroIA as erro:
            # Sem raise: a movimentação grava-se sem categoria, para o utilizador não perder o que escreveu.
            # Fica para o POST /transacoes/categorizar tratar mais tarde.
            print(erro)

    # mode="json" converte a date em texto ("2026-09-20"), que é o que o Supabase aceita.
    # O dono vem sempre do token, nunca do corpo do pedido.
    dados = nova.model_dump(mode="json") | {"categoria": categoria, "user_id": user_id}
    resposta = supabase.table("transacoes").insert(dados).execute()
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
    return resposta.data[0]


# Categoriza com IA as transações que ficaram sem categoria (antigas, ou de uma importação em que a IA falhou).
@app.post("/transacoes/categorizar")
def categorizar_pendentes(user_id: str = Depends(obter_utilizador_atual)) -> list[Transacao]:
    # .is_("categoria", "null") é o "WHERE categoria IS NULL" do SQL (o .eq não serve para NULL).
    resposta = (
        supabase.table("transacoes")
        .select("*")
        .eq("user_id", user_id)
        .is_("categoria", "null")
        .execute()
    )
    pendentes = [Transacao(**linha) for linha in resposta.data]
    if not pendentes:
        return []

    try:
        categorias = categorizar(pendentes)
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
    return atualizadas


# Tamanho máximo de um extrato em PDF. Um extrato normal tem bem menos do que isto.
TAMANHO_MAXIMO_PDF = 10 * 1024 * 1024


def ler_pdf_enviado(pdf: bytes, user_id: str) -> list[TransacaoImportada]:
    """A IA lê o extrato em PDF. Responde 422 se não for válido e 503 se a IA falhar."""
    if len(pdf) > TAMANHO_MAXIMO_PDF:
        raise HTTPException(status_code=422, detail="PDF demasiado grande. Máx. 10 MB.")

    # Ler um PDF é a chamada mais cara da importação, por isso conta para o limite diário.
    registar_pergunta(user_id)
    try:
        extrato = ler_extrato_pdf(pdf)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(
            status_code=503, detail="Não consegui ler o PDF. Se tiver palavra-passe, tira-a. Senão, tenta mais tarde."
        )
    if not extrato.movimentos:
        raise HTTPException(status_code=422, detail="Não encontrei movimentos neste PDF. Confirma que é um extrato bancário.")
    return transacoes_do_pdf(extrato)


@app.post("/transacoes/importar", status_code=201)
def importar_extrato(ficheiro: UploadFile, user_id: str = Depends(obter_utilizador_atual)) -> ResultadoImportacao:
    conteudo = ficheiro.file.read()

    # Todos os PDF começam por "%PDF": é mais seguro do que confiar no nome do ficheiro.
    if conteudo.startswith(b"%PDF"):
        novas = ler_pdf_enviado(conteudo, user_id)
    else:
        try:
            # "utf-8-sig" ignora a marca invisível (BOM) que o Excel põe no início dos CSV.
            novas = ler_extrato(conteudo.decode("utf-8-sig"))
        except ErroImportacao as erro:
            # Nada é gravado: o utilizador corrige o ficheiro e volta a importar.
            raise HTTPException(status_code=422, detail={"mensagem": str(erro), "erros": erro.erros})
    if not novas:
        raise HTTPException(status_code=422, detail="O ficheiro não tem transações")

    try:   
        categorias = categorizar(novas)
    except ErroIA as erro:
        raise HTTPException(status_code=503, detail="A categorização automática falhou. Tenta importar mais tarde. " )

    for nova, categoria in zip(novas, categorias):
        nova.categoria = categoria

    dados = [nova.model_dump(mode="json") | {"user_id": user_id} for nova in novas]
    # upsert com ignore_duplicates: as linhas cuja impressão digital já existe são saltadas
    # (ON CONFLICT DO NOTHING), e a resposta traz só as que entraram mesmo.
    resposta = (
        supabase.table("transacoes")
        .upsert(dados, on_conflict="user_id,hash_importacao", ignore_duplicates=True)
        .execute()
    )
    return ResultadoImportacao(
        importadas=len(resposta.data),
        duplicadas=len(dados) - len(resposta.data),
        transacoes=resposta.data,
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
    resposta = supabase.table("transacoes").select("data, valor").eq("user_id", user_id).execute()
    return resumo_mensal(resposta.data)


# Chat sobre as finanças: a IA responde usando as ferramentas, sempre com os dados deste utilizador.
@app.post("/chat")
def chat(pedido: PerguntaChat, user_id: str = Depends(obter_utilizador_atual)) -> RespostaChat:
    # Antes de gastar uma chamada à IA: conta a pergunta, ou responde 429 se o limite de hoje acabou.
    registar_pergunta(user_id)

    # Closure: uma função que "lembra" o user_id deste pedido. A IA só lhe passa o nome e os argumentos.
    def executar(nome: str, argumentos: dict) -> str:
        return executar_ferramenta(nome, argumentos, user_id)

    try:
        resposta = conversar(pedido.pergunta, FERRAMENTAS, executar)
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
    try:
        return resumir_mes(dados)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail="O resumo automático falhou. Tenta mais tarde.")


# Planeamento do mês: cada categoria com o orçamento (se tiver) e quanto já se gastou.
@app.get("/orcamentos")
def listar_orcamentos(
    mes: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), user_id: str = Depends(obter_utilizador_atual)
) -> list[LinhaOrcamento]:
    return planeamento_do_mes(user_id, mes)


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
    # Conta para o limite diário, como as perguntas do chat (cada sugestão é uma chamada à IA).
    registar_pergunta(user_id)
    try:
        return sugerir_orcamento(historico)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail="A sugestão automática falhou. Tenta mais tarde.")


# Os formatos de imagem que a IA aceita, e o tamanho máximo de cada imagem na API (5 MB).
TIPOS_IMAGEM = {"image/jpeg", "image/png", "image/webp"}
TAMANHO_MAXIMO = 5 * 1024 * 1024


# A IA lê a fotografia de um talão. Não grava nada: o utilizador revê os produtos antes de guardar.
@app.post("/compras/ler")
def ler_compra(foto: UploadFile, user_id: str = Depends(obter_utilizador_atual)) -> Talao:
    imagem = foto.file.read()

    if foto.content_type not in TIPOS_IMAGEM:
        raise HTTPException(status_code=422, detail="Formato de imagem não suportado. Usa JPEG, PNG ou WebP.")
    if len(imagem) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=422, detail="Imagem demasiado grande. Máx. 5 MB.")
    elif len(imagem) < 1024:
        raise HTTPException(status_code=422, detail="Imagem demasiado pequena. Tenta outra fotografia.")

    # Só depois de a foto ser válida é que conta para o limite diário (uma foto errada não gasta perguntas).
    registar_pergunta(user_id)
    try:
        talao = ler_talao(imagem, foto.content_type)
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
    return gravar_compra(user_id, nova)


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
    dados = dados_do_plano(user_id, objetivo, date.today())

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

    registar_pergunta(user_id)
    try:
        return planear_poupanca(dados)
    except ErroIA as erro:
        print(erro)
        raise HTTPException(status_code=503, detail="O plano de poupança falhou. Tenta mais tarde.")
