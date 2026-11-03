import os

from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from supabase import AuthApiError

from auth import fazer_login, obter_utilizador_atual
from dashboard import gastos_por_categoria, limites_do_mes, resumo_mensal
from database import supabase
from ferramentas import FERRAMENTAS, executar_ferramenta
from ia import ErroIA, categorizar, conversar, resumir_mes
from importar_csv import ErroImportacao, ler_extrato
from models import (
    CategoriaAtualizar,
    Credenciais,
    GastoCategoria,
    PerguntaChat,
    RespostaChat,
    ResultadoImportacao,
    ResumoMes,
    ResumoMensal,
    Transacao,
    TransacaoCriar,
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
@app.get("/transacoes")
def listar_transacoes(user_id: str = Depends(obter_utilizador_atual)) -> list[Transacao]:
    resposta = (
        supabase.table("transacoes")
        .select("*")
        .eq("user_id", user_id)
        .order("data")
        .execute()
    )
    return resposta.data


@app.get("/transacoes/{transacao_id}")
def obter_transacao(transacao_id: int, user_id: str = Depends(obter_utilizador_atual)) -> Transacao:
    resposta = supabase.table("transacoes").select("*").eq("id", transacao_id).eq("user_id", user_id).execute()
    if not resposta.data:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    return resposta.data[0]


@app.post("/transacoes", status_code=201)
def criar_transacao(nova: TransacaoCriar, user_id: str = Depends(obter_utilizador_atual)) -> Transacao:
    # mode="json" converte a date em texto ("2026-09-20"), que é o que o Supabase aceita.
    # O dono vem sempre do token, nunca do corpo do pedido.
    dados = nova.model_dump(mode="json") | {"user_id": user_id}
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


@app.post("/transacoes/importar", status_code=201)
def importar_extrato(ficheiro: UploadFile, user_id: str = Depends(obter_utilizador_atual)) -> ResultadoImportacao:
    # "utf-8-sig" ignora a marca invisível (BOM) que o Excel põe no início dos CSV.
    conteudo = ficheiro.file.read().decode("utf-8-sig")
    try:
        novas = ler_extrato(conteudo)
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
    inicio, fim = limites_do_mes(mes)
    resposta = (
        supabase.table("transacoes")
        .select("categoria, valor")
        .eq("user_id", user_id)
        .gte("data", inicio.isoformat())
        .lt("data", fim.isoformat())
        .execute()
    )
    return gastos_por_categoria(resposta.data)


# Receitas e despesas de cada mês, para o gráfico da evolução.
@app.get("/dashboard/mensal")
def dashboard_mensal(user_id: str = Depends(obter_utilizador_atual)) -> list[ResumoMensal]:
    resposta = supabase.table("transacoes").select("data, valor").eq("user_id", user_id).execute()
    return resumo_mensal(resposta.data)


# Chat sobre as finanças: a IA responde usando as ferramentas, sempre com os dados deste utilizador.
@app.post("/chat")
def chat(pedido: PerguntaChat, user_id: str = Depends(obter_utilizador_atual)) -> RespostaChat:
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
