from datetime import date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from database import supabase

app = FastAPI()


# Dados que o cliente envia para criar uma transação (sem id: quem o gera é a base de dados).
class TransacaoCriar(BaseModel):
    data: date
    descricao: str
    valor: float
    categoria: str | None = None


# Transação completa, tal como fica guardada: herda os campos acima e junta o id.
class Transacao(TransacaoCriar):
    id: int


@app.get("/")
def inicio():
    return {"message": "A API de finanças está funcionando!"}


@app.get("/transacoes")
def listar_transacoes() -> list[Transacao]:
    resposta = supabase.table("transacoes").select("*").order("data").execute()
    return resposta.data


@app.get("/transacoes/{transacao_id}")
def obter_transacao(transacao_id: int) -> Transacao:
    resposta = supabase.table("transacoes").select("*").eq("id", transacao_id).execute()
    if not resposta.data:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    return resposta.data[0]


@app.post("/transacoes", status_code=201)
def criar_transacao(nova: TransacaoCriar) -> Transacao:
    # mode="json" converte a date em texto ("2026-09-20"), que é o que o Supabase aceita.
    resposta = supabase.table("transacoes").insert(nova.model_dump(mode="json")).execute()
    return resposta.data[0]
