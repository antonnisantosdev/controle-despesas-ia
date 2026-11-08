from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# As únicas categorias permitidas, tanto para a IA como para as correções do utilizador.
# Com Literal, o Pydantic rejeita qualquer outra palavra.
Categoria = Literal[
    "alimentação",
    "restaurantes",
    "transporte",
    "casa",
    "saúde",
    "lazer",
    "compras",
    "telecomunicações",
    "rendimento",
    "transferências",
    "levantamentos",
    "outros",
]


# Como foi paga uma transação. Os nomes são códigos simples; o frontend mostra-os por extenso.
MetodoPagamento = Literal[
    "dinheiro",
    "cartao_debito",
    "cartao_credito",
    "cartao_refeicao",
    "mbway",
    "transferencia",
    "debito_direto",
]


# Dados que o cliente envia para criar uma transação (sem id: quem o gera é a base de dados).
class TransacaoCriar(BaseModel):
    data: date
    descricao: str
    valor: float
    categoria: str | None = None


# Transação completa, tal como fica guardada: herda os campos acima e junta o id.
class Transacao(TransacaoCriar):
    id: int
    metodo_pagamento: str | None = None


# Movimentação criada à mão no ecrã. Mais rigorosa do que TransacaoCriar: o método é obrigatório,
# a categoria (se vier) tem de ser uma das permitidas, e sem categoria quem escolhe é a IA.
class NovaMovimentacao(BaseModel):
    data: date
    descricao: str = Field(min_length=1, max_length=200)
    valor: float
    metodo_pagamento: MetodoPagamento
    categoria: Categoria | None = None

    # O Pydantic não tem uma regra pronta para "diferente de zero", por isso escreve-se à mão.
    @field_validator("valor")
    @classmethod
    def valor_diferente_de_zero(cls, valor: float) -> float:
        if valor == 0:
            raise ValueError("o valor não pode ser 0")
        return valor


# Transação lida de um extrato: leva a impressão digital da linha, para detetar repetidas.
class TransacaoImportada(TransacaoCriar):
    hash_importacao: str


# Um movimento lido pela IA de um extrato em PDF. Nem todos os bancos mostram o saldo em cada linha.
class MovimentoPdf(BaseModel):
    data: date
    descricao: str
    valor: float
    saldo: float | None


# O que a IA leu de um extrato em PDF (saída estruturada).
class ExtratoPdf(BaseModel):
    movimentos: list[MovimentoPdf]


# Resposta da importação: quantas entraram, quantas já existiam, e as que entraram.
class ResultadoImportacao(BaseModel):
    importadas: int
    duplicadas: int
    transacoes: list[Transacao]


# Uma fatia do gráfico do dashboard: quanto se gastou numa categoria.
class GastoCategoria(BaseModel):
    categoria: str
    total: float


# Um ponto do gráfico da evolução: o que entrou e o que saiu num mês.
class ResumoMensal(BaseModel):
    mes: str
    receitas: float
    despesas: float


# Corpo do PATCH: o utilizador só pode mudar a categoria, e só para uma das permitidas.
class CategoriaAtualizar(BaseModel):
    categoria: Categoria


class Credenciais(BaseModel):
    email: str
    password: str


# Pergunta enviada ao chat. O limite de tamanho evita pedidos enormes (que a IA cobraria).
class PerguntaChat(BaseModel):
    pergunta: str = Field(min_length=1, max_length=500)


class RespostaChat(BaseModel):
    resposta: str


# Um alerta do resumo mensal: "atencao" para coisas a corrigir, "info" para o resto.
class Alerta(BaseModel):
    nivel: Literal["info", "atencao"]
    mensagem: str


# Resumo do mês escrito pela IA (saída estruturada) e devolvido tal e qual pela API.
class ResumoMes(BaseModel):
    resumo: str
    alertas: list[Alerta]


# Uma linha do Planeamento: quanto se quer gastar numa categoria (limite) e quanto já se gastou no mês.
# O limite fica vazio quando a categoria tem gastos mas ainda não tem orçamento.
class LinhaOrcamento(BaseModel):
    categoria: str
    limite: float | None
    gasto: float


# Sugestão da IA para uma categoria (saída estruturada): o valor e uma frase a explicar porquê.
class SugestaoCategoria(BaseModel):
    categoria: Categoria
    limite: float
    explicacao: str


class SugestaoOrcamento(BaseModel):
    sugestoes: list[SugestaoCategoria]


# Corpo do PUT /orcamentos/{categoria}.
class NovoLimite(BaseModel):
    limite: float = Field(gt=0)


# Um produto lido do talão. O preço é o da linha (quantidade x preço unitário, já com descontos).
class ItemTalao(BaseModel):
    descricao: str
    quantidade: float
    preco: float


# O que a IA leu de uma fotografia de talão (saída estruturada). A data fica vazia se não for legível.
class Talao(BaseModel):
    loja: str
    data: date | None
    itens: list[ItemTalao]
    total: float
    categoria: Categoria


# Corpo do POST /compras: o talão depois de o utilizador o rever no ecrã.
# Mais rigoroso do que o Talao: aqui a data e o método de pagamento são obrigatórios.
class NovaCompra(BaseModel):
    loja: str = Field(min_length=1, max_length=200)
    data: date
    itens: list[ItemTalao] = Field(min_length=1)
    total: float = Field(gt=0)
    categoria: Categoria
    metodo_pagamento: MetodoPagamento


# Compra gravada, com os produtos e a transação a que ficou ligada.
class Compra(BaseModel):
    id: int
    transacao_id: int
    loja: str
    data: date
    total: float
    itens: list[ItemTalao]


# Corpo do POST /objetivos: um objetivo de poupança novo. O valor poupado começa a 0 (DEFAULT do SQL).
class NovoObjetivo(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    valor_alvo: float = Field(gt=0)
    data_alvo: date


# Objetivo guardado, tal como está na tabela objetivos.
class Objetivo(NovoObjetivo):
    id: int
    valor_poupado: float


# Corpo do PATCH /objetivos/{id}: o novo total poupado (o frontend soma o que se juntou).
class PoupadoAtualizar(BaseModel):
    valor_poupado: float = Field(ge=0)


# Um corte sugerido pela IA: numa categoria de gasto, quanto se pode poupar por mês e porquê.
class CorteSugerido(BaseModel):
    categoria: Categoria
    valor_mensal: float
    motivo: str


# Plano de poupança escrito pela IA (saída estruturada). Não se guarda: muda sempre que o saldo muda.
class PlanoPoupanca(BaseModel):
    viavel: bool
    explicacao: str
    cortes: list[CorteSugerido]


# Um ano da simulação de poupança: quanto se depositou até aí e quanto vale com os juros.
class AnoSimulado(BaseModel):
    ano: int
    depositado: float
    valor: float
