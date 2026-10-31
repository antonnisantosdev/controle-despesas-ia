from datetime import date

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Transacao(BaseModel):
    id: int
    data: date
    descricao: str
    valor: float
    categoria: str | None = None


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
