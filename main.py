from datetime import date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


# Dados que o cliente envia para criar uma transação (sem id: quem o gera é a API).
class TransacaoCriar(BaseModel):
    data: date
    descricao: str
    valor: float
    categoria: str | None = None


# Transação completa, tal como fica guardada: herda os campos acima e junta o id.
class Transacao(TransacaoCriar):
    id: int


# Transações de teste guardadas em memória (perdem-se quando a API reinicia).
# Valores negativos são despesas, positivos são receitas.
transacoes = [
    Transacao(id=1, data="2026-09-01", descricao="Salário Empresa Fictícia", valor=1200.00, categoria="rendimento"),
    Transacao(id=2, data="2026-09-03", descricao="Supermercado Pingo Azul", valor=-45.30, categoria="alimentação"),
    Transacao(id=3, data="2026-09-05", descricao="Passe mensal metro", valor=-40.00, categoria="transporte"),
    Transacao(id=4, data="2026-09-12", descricao="Restaurante O Tasco Inventado", valor=-22.50, categoria="restaurantes"),
    # Esta ainda não tem categoria: no futuro será a IA a sugerir uma.
    Transacao(id=5, data="2026-09-15", descricao="Cinema Shopping Teste", valor=-8.90),
]


@app.get("/")
def inicio():
    return {"message": "A API de finanças está funcionando!"}


@app.get("/transacoes")
def listar_transacoes() -> list[Transacao]:
    return transacoes


@app.get("/transacoes/{transacao_id}")
def obter_transacao(transacao_id: int) -> Transacao:
    for transacao in transacoes:
        if transacao.id == transacao_id:
            return transacao
    raise HTTPException(status_code=404, detail="Transação não encontrada")


@app.post("/transacoes", status_code=201)
def criar_transacao(nova: TransacaoCriar) -> Transacao:
    novo_id = max(transacao.id for transacao in transacoes) + 1 if transacoes else 1
    transacao = Transacao(id=novo_id, data=nova.data, descricao=nova.descricao, valor=nova.valor, categoria=nova.categoria)
    transacoes.append(transacao)
    return transacao
