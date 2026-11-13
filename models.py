import math
import unicodedata
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StrictBool, StringConstraints, field_validator, model_validator

from auth import FORMATO_CODE_VERIFIER, FORMATO_CODIGO_GOOGLE
from limites import MAX_CARACTERES_HISTORICO, MAX_CARACTERES_PERGUNTA_HISTORICO, MAX_CARACTERES_RESPOSTA_HISTORICO
from lista_compras import MERCADOS
from perfil import Perfil, moedas_possiveis, perfil_inicial

# As categorias que a IA pode escolher (categorizar extratos, ler talões). Com Literal, o Pydantic rejeita
# qualquer outra palavra, por isso a IA nunca consegue devolver uma categoria só humana.
CategoriaIA = Literal[
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

# Todas as categorias permitidas nas escolhas do utilizador: as da IA mais as que só uma pessoa escolhe.
# "compras extra": gastos que a pessoa marca como fora do habitual. A IA nunca a escolhe.
CATEGORIAS_SO_HUMANAS = ("compras extra",)
Categoria = Literal[CategoriaIA, "compras extra"]


# Como foi paga uma transação. Os nomes são códigos simples; o frontend mostra-os por extenso.
MetodoPagamento = Literal[
    "dinheiro",
    "cartao_debito",
    "cartao_credito",
    "cartao_refeicao",
    "mbway",
    "transferencia",
    "debito_direto",
    # Brasil (só aparecem para escolher nas contas BR; o frontend decide em opcoes.ts).
    "pix",
    "boleto",
]

# Métodos que só existem num país: a API recusa-os nas movimentações e compras novas das contas do outro país
# (igual a METODOS_POR_PAIS em frontend/src/lib/opcoes.ts). As movimentações antigas ficam como estão.
METODOS_SO_DO_PAIS: dict[str, str] = {"mbway": "PT", "pix": "BR", "boleto": "BR"}


def metodo_do_pais(metodo: str, pais: str) -> bool:
    """True se o método se pode escolher numa conta que vive em pais."""
    return METODOS_SO_DO_PAIS.get(metodo, pais) == pais


# Teto dos valores em dinheiro: as colunas são NUMERIC(12, 2) e um valor maior dava erro 500 na base de dados
# (sem CORS). allow_inf_nan=False recusa NaN e Infinity, que passavam no gt/ge e rebentavam no JSON.
VALOR_MAXIMO = 1_000_000_000
# A quantidade de um produto é NUMERIC(10, 3) (máximo 9 999 999,999).
QUANTIDADE_MAXIMA = 1_000_000


# Dados que o cliente envia para criar uma transação (sem id: quem o gera é a base de dados).
class TransacaoCriar(BaseModel):
    data: date
    descricao: str
    valor: float
    categoria: str | None = None


# Nota pessoal de uma movimentação (sql/025), ex. "jantar de anos da Rita". A descrição do banco nunca muda
# (entra no hash_importacao); a nota é à parte e opcional.
MAX_CARACTERES_NOTA = 300


def numa_linha(texto: str) -> str:
    """O texto numa só linha: caracteres de controlo passam a espaço, espaços e mudanças de linha seguidos
    ficam um só espaço, e saem os das pontas."""
    # Cc (controlo) passa a espaço; Cf (invisíveis: U+202E que vira o texto ao contrário, larguras zero) sai.
    sem_controlo = "".join(
        " " if unicodedata.category(letra) == "Cc" else "" if unicodedata.category(letra) == "Cf" else letra
        for letra in texto
    )
    return " ".join(sem_controlo.split())


def limpar_nota(valor: str | None) -> str | None:
    """A nota numa só linha: tira caracteres de controlo, junta espaços e mudanças de linha seguidos num só
    espaço e tira os das pontas. Vazia passa a None (sem nota). Mais de MAX_CARACTERES_NOTA: erro (422)."""
    if valor is None:
        return None
    texto = numa_linha(valor)
    if len(texto) > MAX_CARACTERES_NOTA:
        raise ValueError(f"a nota pode ter no máximo {MAX_CARACTERES_NOTA} caracteres")
    return texto or None


Nota = Annotated[str | None, AfterValidator(limpar_nota)]


# Transação completa, tal como fica guardada: herda os campos acima e junta o id.
# nota fica None antes da sql/025 (a coluna ainda não existe e o select("*") não a traz).
class Transacao(TransacaoCriar):
    id: int
    metodo_pagamento: str | None = None
    nota: str | None = None


VALOR_MAXIMO_MOVIMENTACAO = VALOR_MAXIMO


# Movimentação criada à mão no ecrã. Mais rigorosa do que TransacaoCriar: o método é obrigatório,
# a categoria (se vier) tem de ser uma das permitidas, e sem categoria quem escolhe é a IA.
class NovaMovimentacao(BaseModel):
    # Entre 2000 e 2099: um ano 0001 ou 9999 (escrito à mão ou proposto pela IA) é quase de certeza um erro.
    data: Annotated[date, Field(ge=date(2000, 1, 1), le=date(2099, 12, 31))]
    descricao: str = Field(min_length=1, max_length=200)
    valor: float
    metodo_pagamento: MetodoPagamento
    categoria: Categoria | None = None
    # Opcional; texto vazio ou só espaços fica sem nota.
    nota: Nota = None

    # O Pydantic não tem uma regra pronta para "diferente de zero", por isso escreve-se à mão.
    # Teto de mil milhões: a coluna é NUMERIC(12, 2) e um valor maior dava erro 500 na base de dados (sem CORS).
    @field_validator("valor")
    @classmethod
    def valor_diferente_de_zero(cls, valor: float) -> float:
        if valor == 0:
            raise ValueError("o valor não pode ser 0")
        # NaN passava nas duas regras (NaN não é 0 nem maior do que nada) e rebentava na base de dados.
        if not math.isfinite(valor) or abs(valor) > VALOR_MAXIMO_MOVIMENTACAO:
            raise ValueError("o valor é demasiado grande")
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


# Corpo do PATCH /transacoes/{id}: a categoria (só uma das permitidas) e/ou a nota. Pelo menos uma das duas.
# A descrição, o valor e a data não mudam por aqui. {"nota": ""} (ou null) apaga a nota.
class TransacaoAtualizar(BaseModel):
    categoria: Categoria | None = None
    nota: Nota = None

    @model_validator(mode="after")
    def pelo_menos_um_campo(self) -> "TransacaoAtualizar":
        if not self.model_fields_set & {"categoria", "nota"}:
            raise ValueError("indica a categoria e/ou a nota")
        # Uma movimentação pode ficar sem nota, mas não volta a ficar sem categoria por aqui.
        if "categoria" in self.model_fields_set and self.categoria is None:
            raise ValueError("a categoria não pode ficar vazia")
        return self

    def alteracoes(self) -> dict:
        """Só os campos que vieram no pedido, prontos para o update (a nota vazia vai como None = NULL)."""
        return {campo: getattr(self, campo) for campo in ("categoria", "nota") if campo in self.model_fields_set}


# Para apagar a conta, o corpo tem de trazer {"confirmacao": "APAGAR"} (evita apagar por engano).
# Opcional aqui: a falta ou um valor errado respondem 400 na rota, não 422.
class ConfirmacaoApagarConta(BaseModel):
    confirmacao: str | None = Field(default=None, max_length=20)


# --- Origem do registo (o utm_source dos links das redes, sem cookies) ---
# Lista fechada: o que vier de fora desta lista conta como "outro"; vazio ou ausente fica None.
CANAIS_DE_ORIGEM = ("instagram", "youtube", "tiktok", "linkedin")
Origem = Literal["instagram", "youtube", "tiktok", "linkedin", "outro"]


def normalizar_origem(valor: object) -> str | None:
    """O canal de origem na lista fechada: um canal conhecido (sem espaços, em minúsculas) fica igual,
    qualquer outro valor passa a "outro". None ou texto vazio ficam None (sem origem).
    Nunca falha: uma origem estranha não pode recusar um registo."""
    if valor is None:
        return None
    if not isinstance(valor, str):
        return "outro"
    texto = valor.strip().lower()
    if not texto:
        return None
    return texto if texto in CANAIS_DE_ORIGEM else "outro"


class ComOrigem(BaseModel):
    """Base dos pedidos que trazem a origem do registo (opcional)."""

    origem: Origem | None = None

    @field_validator("origem", mode="before")
    @classmethod
    def origem_na_lista_fechada(cls, valor: object) -> str | None:
        return normalizar_origem(valor)


# --- Perfil da conta (sql/020): país onde vive, países dos cartões e contas, moeda principal ---
Pais = Literal["PT", "BR"]
Moeda = Literal["EUR", "BRL"]
# 1 ou 2 países, sem repetidos (validado em paises_sem_repetidos).
def paises_sem_repetidos(paises: list[str]) -> list[str]:
    if len(set(paises)) != len(paises):
        raise ValueError("países repetidos")
    return paises


PaisesBancos = Annotated[list[Pais], Field(min_length=1, max_length=2), AfterValidator(paises_sem_repetidos)]


class ComPerfil(ComOrigem):
    """Base do registo e do 1.º login com o Google: o perfil escolhido no registo (tudo opcional).

    Sem nenhum dos três, a conta fica com o de sempre (PT, {PT}, EUR: DEFAULT da sql/020).
    Com algum, o perfil completo resolve-se já aqui (perfil.perfil_inicial): uma moeda que não é
    de um dos países das contas dá 422. Só se grava em conta acabada de criar (ver main.py).
    """

    pais: Pais | None = None
    paises_bancos: PaisesBancos | None = None
    moeda: Moeda | None = None

    @model_validator(mode="after")
    def moeda_coerente(self) -> "ComPerfil":
        perfil_inicial(self.pais, self.paises_bancos, self.moeda)  # ValueError se for incoerente
        return self

    def perfil_pedido(self) -> Perfil | None:
        """O perfil completo a gravar, ou None se o pedido não trouxe nenhum dos três campos."""
        return perfil_inicial(self.pais, self.paises_bancos, self.moeda)


# Corpo do PUT /conta/perfil: muda o que vier (o resto fica). A moeda só muda com a conta sem dados (409).
class PerfilConta(BaseModel):
    pais: Pais | None = None
    paises_bancos: PaisesBancos | None = None
    moeda: Moeda | None = None


# Resposta do PUT /conta/perfil: o perfil como ficou.
class PerfilGuardado(BaseModel):
    pais: Pais
    paises_bancos: list[Pais]
    moeda: Moeda


# --- Questionário de boas-vindas (sql/021): só opções fechadas, sem texto livre ---
# As listas têm de ser iguais às do CHECK da sql/021 e às do frontend (lib/textosBoasVindas.ts).
MotivoBoasVindas = Literal["nao_sei", "fim_mes", "supermercado", "folhas", "poupar", "experimentar", "outro"]
ObjetivoBoasVindas = Literal["importar", "categorias", "orcamento", "chat", "resumo", "reserva", "taloes"]


def objetivos_sem_repetidos(objetivos: list[str]) -> list[str]:
    if len(set(objetivos)) != len(objetivos):
        raise ValueError("objetivos repetidos")
    return objetivos


# 0 a 7 objetivos, sem repetidos. Uma lista vazia é o mesmo que saltar (grava-se NULL).
ObjetivosBoasVindas = Annotated[list[ObjetivoBoasVindas], Field(max_length=7), AfterValidator(objetivos_sem_repetidos)]


# Corpo do PUT /conta/boas-vindas (o questionário e as definições). O país e os bancos são obrigatórios;
# a moeda só é precisa com bancos dos dois países (com um só país, é a desse país).
# O motivo e os objetivos substituem os que havia: None (ou []) apaga a resposta.
class RespostasBoasVindas(BaseModel):
    pais: Pais
    paises_bancos: PaisesBancos
    moeda: Moeda | None = None
    motivo: MotivoBoasVindas | None = None
    objetivos: ObjetivosBoasVindas | None = None

    @model_validator(mode="after")
    def moeda_coerente(self) -> "RespostasBoasVindas":
        if self.moeda is not None and self.moeda not in moedas_possiveis(self.paises_bancos):
            raise ValueError("a moeda tem de ser a de um dos países das contas")
        return self


# Resposta do GET e do PUT /conta/boas-vindas: o perfil e as respostas como ficaram.
# aviso: no PUT, se a moeda não pôde mudar (a conta já tem dados): o resto ficou gravado e a moeda ficou a de antes.
class BoasVindasGuardadas(BaseModel):
    pais: Pais
    paises_bancos: list[Pais]
    moeda: Moeda
    motivo: MotivoBoasVindas | None = None
    objetivos: list[ObjetivoBoasVindas] | None = None
    aviso: str | None = None


# Tetos de tamanho antes de falar com o Supabase (e de calcular o HMAC do limite por email): acima, 422.
# 254 é o máximo de um endereço de email (RFC 5321); 256 chega para qualquer palavra-passe real.
class Credenciais(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


# O que a página /login/google manda no regresso do Google (PKCE): o código que o Supabase pôs no endereço
# e o segredo que ficou guardado no browser. Formato e tamanho validados antes de falar com o Supabase.
# origem: o canal do utm_source (só se guarda se a conta for nova, ver main.py).
class TrocaGoogle(ComPerfil):
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


# --- Propostas do chat: a IA propõe criar, alterar ou apagar uma movimentação; quem grava é a pessoa,
# ao carregar "Confirmar" no cartão (com as rotas de sempre: POST, PATCH e DELETE /transacoes). ---


# A movimentação como está na base de dados, lida pelo servidor (nunca o que a IA escreveu).
class MovimentoNaProposta(BaseModel):
    id: int
    data: date
    descricao: str
    valor: float
    categoria: str | None = None
    metodo_pagamento: str | None = None
    nota: str | None = None


# O que muda numa proposta de alteração. categoria None: a categoria não muda.
# muda_nota: se a nota muda; com muda_nota, nota None quer dizer apagar a nota.
class AlteracaoProposta(BaseModel):
    categoria: Categoria | None = None
    muda_nota: bool = False
    nota: str | None = None


# Uma proposta. criar: nova (os campos já validados, com categoria, para confirmar sem chamar a IA).
# alterar: movimento (da base de dados) e alteracao. apagar: só movimento (da base de dados).
class PropostaChat(BaseModel):
    tipo: Literal["criar", "alterar", "apagar"]
    movimento: MovimentoNaProposta | None = None
    nova: NovaMovimentacao | None = None
    alteracao: AlteracaoProposta | None = None


# propostas: vazia quando a IA não propôs nada (e sempre vazia na demo). Uma API antiga não a envia.
class RespostaChat(BaseModel):
    resposta: str
    propostas: list[PropostaChat] = Field(default_factory=list)


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
    # Categoria (e não CategoriaIA): sugerir um orçamento para "compras extra" que a pessoa já tem não é classificar.
    categoria: Categoria
    limite: float
    explicacao: str


class SugestaoOrcamento(BaseModel):
    sugestoes: list[SugestaoCategoria]


# Corpo do PUT /orcamentos/{categoria}.
class NovoLimite(BaseModel):
    limite: float = Field(gt=0, le=VALOR_MAXIMO, allow_inf_nan=False)


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
    categoria: CategoriaIA  # a IA nunca escolhe uma categoria só humana


# Um produto enviado pelo utilizador no POST /compras. Com tetos: a rota é pública para
# qualquer conta e, sem eles, um só pedido podia gravar milhares de linhas de texto livre.
class ItemCompra(BaseModel):
    descricao: str = Field(min_length=1, max_length=200)
    quantidade: float = Field(gt=0, le=QUANTIDADE_MAXIMA, allow_inf_nan=False)
    preco: float = Field(ge=0, le=VALOR_MAXIMO, allow_inf_nan=False)
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
    total: float = Field(gt=0, le=VALOR_MAXIMO, allow_inf_nan=False)
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


# --- Fazer as minhas compras (POST /compras/lista e GET /compras/lista/estado) ---

# Teto do orçamento de uma lista de compras (uma ida ao supermercado; acima disto é um engano).
ORCAMENTO_MAXIMO_LISTA = 10_000
MAX_MERCADOS_LISTA = 3


# Corpo do POST /compras/lista: o orçamento, 1 a 3 mercados (chaves de lista_compras.MERCADOS, sem repetidos)
# e a lista de produtos em texto livre. A lista vai para a IA: o teto de 600 caracteres limita o custo.
class PedidoListaCompras(BaseModel):
    orcamento: float = Field(gt=0, le=ORCAMENTO_MAXIMO_LISTA, allow_inf_nan=False)
    mercados: list[str] = Field(min_length=1, max_length=MAX_MERCADOS_LISTA)
    lista: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=600)]

    @field_validator("mercados")
    @classmethod
    def mercados_conhecidos_sem_repetidos(cls, mercados: list[str]) -> list[str]:
        if any(mercado not in MERCADOS for mercado in mercados):
            raise ValueError("mercado desconhecido")
        if len(set(mercados)) != len(mercados):
            raise ValueError("mercados repetidos")
        return mercados


# Um mercado que se pode escolher (o nome é o que se mostra).
class MercadoDisponivel(BaseModel):
    chave: str
    nome: str


# GET /compras/lista/estado: se a pessoa pode usar (plano pago e conta em Portugal), as listas do mês e os mercados.
class EstadoListaCompras(BaseModel):
    disponivel: bool
    usadas: int
    limite: int
    mercados: list[MercadoDisponivel]


# Um produto da lista num mercado, tal como a IA o encontrou (já limpo: lista_compras.limpar_itens).
class ItemListaCompras(BaseModel):
    pedido: str
    mercado: str
    encontrado: bool
    produto: str
    preco_embalagem: float
    embalagens: int
    preco_total: float
    link: str
    nota: str


# O que comprar num mercado (o mais barato de cada produto).
class ItemPlanoCompras(BaseModel):
    pedido: str
    produto: str
    embalagens: int
    preco_total: float
    link: str


class MercadoPlanoCompras(BaseModel):
    mercado: str
    total: float
    itens: list[ItemPlanoCompras]
    mapa_url: str


# Resposta do POST /compras/lista. diferenca = orcamento - total (negativa quando passa o orçamento).
# exemplo: true só na demo (um exemplo fixo, sem IA).
class ResultadoListaCompras(BaseModel):
    itens: list[ItemListaCompras]
    plano: list[MercadoPlanoCompras]
    total: float
    orcamento: float
    diferenca: float
    sem_preco: list[str]
    usadas: int
    limite: int
    exemplo: bool = False


# Corpo do POST /objetivos: um objetivo de poupança novo. O valor poupado começa a 0 (DEFAULT do SQL).
class NovoObjetivo(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    valor_alvo: float = Field(gt=0, le=VALOR_MAXIMO, allow_inf_nan=False)
    data_alvo: date


# Objetivo guardado, tal como está na tabela objetivos.
class Objetivo(NovoObjetivo):
    id: int
    valor_poupado: float


# Corpo do PATCH /objetivos/{id}: o novo total poupado (o frontend soma o que se juntou).
class PoupadoAtualizar(BaseModel):
    valor_poupado: float = Field(ge=0, le=VALOR_MAXIMO, allow_inf_nan=False)


# Um corte sugerido pela IA: numa categoria de gasto, quanto se pode poupar por mês e porquê.
class CorteSugerido(BaseModel):
    # Categoria (e não CategoriaIA): um corte em "compras extra" que a pessoa já tem é uma sugestão válida.
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
    # Extratos em PDF lidos pela IA neste mês, e quantos o plano permite (1 no Free).
    pdf_usados: int = 0
    pdf_limite: int = 0
    # Mensagens anteriores que o chat recebe (0 no Free) e meses que o chat vê (None = sem limite).
    memoria_mensagens: int = 0
    meses_historico: int | None = None
    # Perfil da conta (sql/020): onde vive, de que países são os cartões e contas, e a moeda principal.
    # Com valores por omissão (os de todas as contas até aqui), para o frontend atual não partir.
    pais: Pais = "PT"
    paises_bancos: list[Pais] = Field(default_factory=lambda: ["PT"])
    moeda: Moeda = "EUR"
    # Questionário de boas-vindas (sql/021): true numa conta nova que ainda não o fez (o frontend abre-o).
    # Sempre false antes da 021, nas contas antigas e na demo.
    boas_vindas_pendente: bool = False
    # Interruptor do Brasil (perfil.pode_escolher_brasil): se a conta pode escolher "vivo no Brasil".
    brasil_disponivel: bool = False


# Um plano à venda e o seu limite de pedidos à IA (GET /planos, público).
class PlanoDisponivel(BaseModel):
    plano: str
    # Pedidos à IA no período (o nome ficou de quando todos os planos contavam por dia).
    limite_diario: int
    periodo: Literal["dia", "mes"]
    # Extratos em PDF por mês (1 no Free).
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
class NovaConta(ComPerfil):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


# POST /lista-espera (pública): avisar quando a app abrir no Brasil.
# consentimento tem de vir true (caixa não pré-marcada na página /brasil).
# pais: onde a pessoa vive; paises_cartoes: de que países são os cartões e contas que vai usar (1 a 3, sem repetidos).
PaisListaEspera = Literal["BR", "PT", "outro"]


class InscricaoListaEspera(ComOrigem):
    email: EmailStr
    pais: PaisListaEspera
    paises_cartoes: list[PaisListaEspera] = Field(min_length=1, max_length=3)

    @field_validator("paises_cartoes")
    @classmethod
    def paises_sem_repetidos(cls, paises: list[str]) -> list[str]:
        if len(set(paises)) != len(paises):
            raise ValueError("países repetidos")
        return paises
    consentimento: StrictBool

    @field_validator("consentimento")
    @classmethod
    def consentimento_dado(cls, consentimento: bool) -> bool:
        # Só true (o booleano): false, 1 ou "true" não contam como consentimento.
        if consentimento is not True:
            raise ValueError("é preciso aceitar")
        return consentimento

    @field_validator("email")
    @classmethod
    def email_normalizado(cls, email: str) -> str:
        email = email.strip().lower()
        if len(email) > 254:
            raise ValueError("email demasiado comprido")
        return email


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
    nota: str | None = None  # a nota pessoal (sql/025), se houver


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
    # O ano da movimentação mais antiga da conta (None sem movimentações ou se a leitura falhar).
    # O seletor de anos do frontend só mostra os anos a partir deste.
    primeiro_ano: int | None = None


# Resposta da IA no POST /relatorio/resumo-ia (saída estruturada).
class ResumoAnualIA(BaseModel):
    resumo: str
