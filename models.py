from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator, model_validator

from auth import FORMATO_CODE_VERIFIER, FORMATO_CODIGO_GOOGLE
from limites import MAX_CARACTERES_HISTORICO, MAX_CARACTERES_PERGUNTA_HISTORICO, MAX_CARACTERES_RESPOSTA_HISTORICO

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
    # Texto para mostrar ao utilizador (ex.: importou sem categorias porque acabaram os pedidos à IA).
    aviso: str | None = None


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


# Para apagar a conta, o corpo tem de trazer {"confirmacao": "APAGAR"} (evita apagar por engano).
# Opcional aqui: a falta ou um valor errado respondem 400 na rota, não 422.
class ConfirmacaoApagarConta(BaseModel):
    confirmacao: str | None = Field(default=None, max_length=20)


class Credenciais(BaseModel):
    email: str
    password: str


# O que a página /login/google manda no regresso do Google (PKCE): o código que o Supabase pôs no endereço
# e o segredo que ficou guardado no browser. Formato e tamanho validados antes de falar com o Supabase.
class TrocaGoogle(BaseModel):
    code: Annotated[str, StringConstraints(pattern=FORMATO_CODIGO_GOOGLE)]
    code_verifier: Annotated[str, StringConstraints(pattern=FORMATO_CODE_VERIFIER)]


# Uma mensagem anterior da conversa, enviada pelo browser (memória só da sessão, não se guarda).
# Só texto, com teto: vem do cliente e pode ser falsificada, por isso a IA nunca tira números daqui.
# strip_whitespace tira os espaços das pontas antes de contar: "   " fica vazio e é recusado.
class MensagemHistorico(BaseModel):
    papel: Literal["utilizador", "ia"]
    texto: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_CARACTERES_RESPOSTA_HISTORICO)]

    # Uma pergunta antiga tem o mesmo teto de uma pergunta nova; só as respostas da IA podem ser maiores.
    @model_validator(mode="after")
    def tamanho_conforme_o_papel(self) -> "MensagemHistorico":
        if self.papel == "utilizador" and len(self.texto) > MAX_CARACTERES_PERGUNTA_HISTORICO:
            raise ValueError(f"cada pergunta do histórico tem no máximo {MAX_CARACTERES_PERGUNTA_HISTORICO} caracteres")
        return self


# Pergunta enviada ao chat. O limite de tamanho evita pedidos enormes (que a IA cobraria).
# historico é opcional (o frontend antigo não o envia); a API corta-o para a memória do plano.
# O teto de 20 é só contra pedidos enormes: nenhum plano usa mais de 10 (limites.py).
class PerguntaChat(BaseModel):
    pergunta: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    historico: list[MensagemHistorico] = Field(default_factory=list, max_length=20)

    @field_validator("historico")
    @classmethod
    def historico_nao_passa_o_total(cls, historico: list[MensagemHistorico]) -> list[MensagemHistorico]:
        if sum(len(mensagem.texto) for mensagem in historico) > MAX_CARACTERES_HISTORICO:
            raise ValueError(f"o histórico tem no máximo {MAX_CARACTERES_HISTORICO} caracteres no total")
        return historico


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


# Categoria do mês atual com o gasto perto (>= 90%) ou acima do orçamento (GET /orcamentos/alertas, sem IA).
class AlertaOrcamento(BaseModel):
    categoria: str
    gasto: float
    limite: float
    nivel: Literal["perto", "atingido"]


# Resposta de GET /orcamentos/alertas: o mês atual de Lisboa ("2026-11") e os alertas desse mês.
class AlertasOrcamento(BaseModel):
    mes: str
    alertas: list[AlertaOrcamento]


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


# Unidade em que se mede a quantidade de um produto: unidades, quilos ou litros.
# Os preços unitários só se comparam dentro da mesma unidade (1 € por kg não é 1 € por unidade).
Unidade = Literal["un", "kg", "l"]


# Um produto lido do talão. O preço é o da linha (quantidade x preço unitário, já com descontos).
# nome_generico e unidade servem para comparar o mesmo produto entre lojas (produtos.py). Têm valor
# por omissão: uma resposta da IA sem eles (formato antigo) continua válida.
class ItemTalao(BaseModel):
    descricao: str
    quantidade: float
    preco: float
    nome_generico: str | None = None
    unidade: Unidade = "un"


# O que a IA leu de uma fotografia de talão (saída estruturada). A data fica vazia se não for legível.
class Talao(BaseModel):
    loja: str
    data: date | None
    itens: list[ItemTalao]
    total: float
    categoria: Categoria


# Um produto enviado pelo utilizador no POST /compras. Com tetos: a rota é pública para
# qualquer conta e, sem eles, um só pedido podia gravar milhares de linhas de texto livre.
class ItemCompra(BaseModel):
    descricao: str = Field(min_length=1, max_length=200)
    quantidade: float = Field(gt=0)
    preco: float = Field(ge=0)
    # Vêm da leitura da IA (o frontend devolve-os tal como os recebeu). Opcionais: sem eles, a chave
    # do produto sai da descrição e a unidade fica "un".
    nome_generico: str | None = None
    unidade: Unidade = "un"

    @field_validator("nome_generico", mode="before")
    @classmethod
    def cortar_nome_generico(cls, valor):
        # Corta em vez de recusar: um nome da IA comprido demais não pode impedir de guardar o talão.
        return valor[:100] if isinstance(valor, str) else valor


# Corpo do POST /compras: o talão depois de o utilizador o rever no ecrã.
# Mais rigoroso do que o Talao: aqui a data e o método de pagamento são obrigatórios.
class NovaCompra(BaseModel):
    loja: str = Field(min_length=1, max_length=200)
    data: date
    # Um talão de supermercado grande tem umas dezenas de linhas; 200 dá folga.
    itens: list[ItemCompra] = Field(min_length=1, max_length=200)
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


# --- Preço de um produto por loja (GET /compras/produtos...) ---


# Um produto na lista da página de preços: a chave (já depois das junções) e o nome a mostrar.
class ProdutoResumo(BaseModel):
    chave: str
    nome: str
    # As unidades em que o produto foi comprado (normalmente só uma).
    unidades: list[Unidade]
    ultima_data: date
    n_lojas: int
    n_compras: int


# O preço de um produto numa loja (preços unitários: por unidade, kg ou litro).
class PrecoNaLoja(BaseModel):
    loja: str
    preco_recente: float
    data_recente: date
    preco_minimo: float
    preco_medio: float
    n_compras: int


# Uma compra do produto, para o histórico.
class PrecoHistorico(BaseModel):
    data: date
    loja: str
    preco_unitario: float


# Os preços de um produto numa unidade: por loja (do mais barato agora para o mais caro) e o histórico.
class PrecosPorUnidade(BaseModel):
    unidade: Unidade
    lojas: list[PrecoNaLoja]
    historico: list[PrecoHistorico]


class PrecosDoProduto(BaseModel):
    chave: str
    nome: str
    por_unidade: list[PrecosPorUnidade]


# Uma junção do utilizador (GET /compras/produtos/juntar), para o ecrã a poder desfazer.
# Os nomes são os mostrados de cada chave, ou a própria chave se já não houver itens com ela.
class JuncaoProdutos(BaseModel):
    chave_origem: str
    nome_origem: str
    chave_destino: str
    nome_destino: str
    criado_em: datetime | None = None


# Corpo do POST /compras/produtos/juntar: passa a contar os itens de chave_origem como chave_destino.
class JuntarProdutos(BaseModel):
    chave_origem: str = Field(min_length=1, max_length=100)
    chave_destino: str = Field(min_length=1, max_length=100)


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


# O plano do utilizador e as perguntas à IA que já fez hoje (GET /plano).
class EstadoPlano(BaseModel):
    plano: str | None
    limite: int
    # "dia" nos planos pagos, "mes" no Free: o período em que se contam os pedidos.
    periodo: Literal["dia", "mes"]
    # Pedidos à IA já feitos no período.
    usadas: int
    # O mesmo número que usadas. Nome antigo, mantido para o frontend antigo não partir durante o deploy.
    usadas_hoje: int
    # Último dia de acesso dos planos pagos; None no Free (não acaba).
    ativo_ate: date | None
    # Quando um plano pago chegou ao fim e a conta passou ao Free: o nome desse plano e o último dia dele.
    plano_terminado: str | None = None
    terminou_em: date | None = None
    # Extratos em PDF lidos pela IA neste mês, e quantos o plano permite (0 no Free: não importa PDF).
    pdf_usados: int = 0
    pdf_limite: int = 0
    # Mensagens anteriores que o chat recebe (0 no Free) e meses que o chat vê (None = sem limite).
    memoria_mensagens: int = 0
    meses_historico: int | None = None


# Um plano à venda e o seu limite de pedidos à IA (GET /planos, público).
class PlanoDisponivel(BaseModel):
    plano: str
    # Pedidos à IA no período (o nome ficou de quando todos os planos contavam por dia).
    limite_diario: int
    periodo: Literal["dia", "mes"]
    # Extratos em PDF por mês (0 no Free, que não importa PDF).
    limite_pdf: int = 0
    # Mensagens anteriores que o chat recebe e meses que o chat vê (None = sem limite).
    memoria_mensagens: int = 0
    meses_historico: int | None = None


# Um pagamento que se repete todos os meses (GET /recorrentes, sem IA): assinaturas, ginásio, renda...
class Recorrente(BaseModel):
    descricao: str
    categoria: str | None
    # Valor do último pagamento, em positivo.
    valor_mensal: float
    # Se o preço mudou durante a sequência (ex.: a assinatura subiu), o valor de antes. None se não mudou.
    valor_anterior: float | None = None
    # Meses seguidos em que apareceu, até ao último pagamento.
    meses_seguidos: int
    ultimo_pagamento: date


# Registo público (POST /registo). O EmailStr recusa emails mal escritos antes de chegarem ao Supabase.
# 72 é o máximo que o Supabase aceita numa palavra-passe.
class NovaConta(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


# --- Resumo anual (GET /relatorio) ---
# Os valores das saídas vão sempre em positivo (34.2 e não -34.2), como no dashboard.
# "categoria" é o nome guardado na base de dados; "etiqueta" é o que se mostra (o "rendimento" aparece como "Entradas").


class TotaisAno(BaseModel):
    entradas: float
    saidas: float
    saldo: float


class MesRelatorio(BaseModel):
    mes: str  # "2026-03"
    entradas: float
    saidas: float
    saldo: float
    com_dados: bool  # False se o mês não tem nenhuma movimentação


class CategoriaRelatorio(BaseModel):
    categoria: str
    etiqueta: str
    total: float
    percentagem: float  # % das saídas do ano, com 1 casa decimal


class CategoriaComparada(BaseModel):
    categoria: str
    etiqueta: str
    total: float  # no ano do relatório
    total_anterior: float  # nos mesmos meses do ano anterior
    diferenca: float  # total - total_anterior


class ComparacaoAno(BaseModel):
    ano: int  # o ano anterior
    # Os meses comparados (os mesmos nos dois anos: "01" a "11" se o relatório for até novembro).
    meses_comparados: list[str]
    meses_com_dados: int  # meses do ano anterior, dentro dos comparados, com movimentações
    totais: TotaisAno  # do ano anterior, nesses meses
    categorias: list[CategoriaComparada]


class SaidaRelatorio(BaseModel):
    data: date
    descricao: str
    valor: float
    categoria: str | None
    etiqueta: str


class RecorrenteAno(BaseModel):
    descricao: str
    categoria: str | None
    etiqueta: str
    valor_mensal: float  # o último pagamento
    pagamentos_no_ano: int
    total_no_ano: float


class ObjetivoRelatorio(BaseModel):
    nome: str
    valor_alvo: float
    valor_poupado: float
    data_alvo: date
    percentagem: float  # do valor alvo já poupado, com 1 casa decimal


class RelatorioAnual(BaseModel):
    ano: int
    titulo: str
    aviso: str
    nota_categorias: str
    ate_mes: str  # o último mês contado ("2026-11" no ano corrente; "AAAA-12" nos anos que já acabaram)
    ano_incompleto: bool  # ano corrente, ou meses sem movimentações
    meses_sem_dados: list[str]
    totais: TotaisAno
    meses: list[MesRelatorio]
    categorias: list[CategoriaRelatorio]
    comparacao: ComparacaoAno | None  # None se o ano anterior não tem movimentações nesses meses
    maiores_saidas: list[SaidaRelatorio]
    recorrentes: list[RecorrenteAno]
    objetivos: list[ObjetivoRelatorio]


# Resposta da IA no POST /relatorio/resumo-ia (saída estruturada).
class ResumoAnualIA(BaseModel):
    resumo: str
