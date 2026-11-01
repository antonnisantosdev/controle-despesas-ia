from datetime import date

from pydantic import BaseModel


# Dados que o cliente envia para criar uma transação (sem id: quem o gera é a base de dados).
class TransacaoCriar(BaseModel):
    data: date
    descricao: str
    valor: float
    categoria: str | None = None


# Transação completa, tal como fica guardada: herda os campos acima e junta o id.
class Transacao(TransacaoCriar):
    id: int


# Transação lida de um extrato: leva a impressão digital da linha, para detetar repetidas.
class TransacaoImportada(TransacaoCriar):
    hash_importacao: str


# Resposta da importação: quantas entraram, quantas já existiam, e as que entraram.
class ResultadoImportacao(BaseModel):
    importadas: int
    duplicadas: int
    transacoes: list[Transacao]


class Credenciais(BaseModel):
    email: str
    password: str
