from fastapi import Depends, FastAPI, HTTPException, UploadFile
from supabase import AuthApiError

from auth import fazer_login, obter_utilizador_atual
from database import supabase
from importar_csv import ler_extrato
from models import Credenciais, Transacao, TransacaoCriar

app = FastAPI()


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


@app.post("/transacoes/importar", status_code=201)
def importar_extrato(ficheiro: UploadFile, user_id: str = Depends(obter_utilizador_atual)) -> list[Transacao]:
    # "utf-8-sig" ignora a marca invisível (BOM) que o Excel põe no início dos CSV.
    conteudo = ficheiro.file.read().decode("utf-8-sig")
    novas = ler_extrato(conteudo)

    novas = [nova.model_dump(mode="json") | {"user_id": user_id} for nova in novas]
    resposta = supabase.table("transacoes").insert(novas).execute()
    return resposta.data