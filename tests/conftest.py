"""Preparação partilhada por todos os testes (o pytest lê este ficheiro sozinho).

Os testes nunca falam com o Supabase nem com a Anthropic verdadeiros: as chaves são falsas,
e a base de dados e a IA são substituídas por imitações. Assim os testes são rápidos,
não gastam créditos e podem correr no GitHub, onde não existe o .env.
"""

import copy
import os
from datetime import datetime, timezone
from types import SimpleNamespace

# Têm de vir antes de importar a API: o database.py lê-as logo ao arrancar.
# Ao contrário do .env, estas ganham sempre (o load_dotenv não substitui variáveis que já existem).
os.environ["SUPABASE_URL"] = "https://exemplo.supabase.co"
os.environ["SUPABASE_KEY"] = "chave-falsa"
os.environ["ANTHROPIC_API_KEY"] = "chave-falsa"
# A demo fica desligada por omissão (mesmo que o .env local a tenha): o test_demo.py liga-a quando precisa.
os.environ["DEMO_TOKEN_SEGREDO"] = ""
os.environ["DEMO_USER_ID"] = ""
os.environ["DEMO_EMAIL"] = ""

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import auth  # noqa: E402
import ia  # noqa: E402
import limite_ip  # noqa: E402
import limites  # noqa: E402
import main  # noqa: E402
import recorrentes  # noqa: E402
import resumo  # noqa: E402
from postgrest.exceptions import APIError  # noqa: E402
from auth import obter_utilizador_atual, obter_utilizador_confirmado  # noqa: E402
from fastapi import Depends  # noqa: E402


class BaseDadosFalsa:
    """Imita o cliente do Supabase: guarda o que se grava e devolve-o como se tivesse entrado.

    contagem é o que as consultas com count="exact" devolvem (as movimentações que a conta já tem).
    """

    def __init__(self):
        self.gravado: list[dict] = []
        self._dados = None
        self.contagem = 0

    def table(self, nome):
        self._dados = None
        return self

    def insert(self, dados, **opcoes):
        self._dados = dados
        return self

    upsert = insert

    def __getattr__(self, nome):
        # select, eq, order, update...: não interessam aqui, só devolvem a própria consulta.
        return lambda *args, **opcoes: self

    def execute(self):
        if isinstance(self._dados, list):
            dados = self._dados
        else:
            dados = [self._dados] if self._dados else []
        linhas = [{"id": i + 1, "categoria": None, "metodo_pagamento": None, **linha} for i, linha in enumerate(dados)]
        self.gravado.extend(linhas)
        contagem = self.contagem

        class Resposta:
            data = linhas
            count = contagem

        return Resposta


class Limite:
    """Imita o limite de pedidos à IA, o limite de PDF do mês e o plano, sem tocar nas tabelas uso_ia e assinaturas.

    O plano é "essencial" por omissão: tem todas as funções (PDF e talões incluídos).
    funcoes guarda a funcao de cada pedido registado; os PDF contam-se pelos pedidos "importar_pdf",
    como na base de dados.
    """

    def __init__(self, maximo=30, plano="essencial", maximo_pdf=15):
        self.maximo = maximo
        self.perguntas = 0
        self.plano = plano
        self.maximo_pdf = maximo_pdf
        self.funcoes: list[str] = []

    @property
    def pdfs(self) -> int:
        return self.funcoes.count("importar_pdf")

    def registar(self, user_id, funcao):
        if self.perguntas >= self.maximo:
            raise HTTPException(status_code=429, detail="Limite diário atingido")
        self.perguntas += 1
        self.funcoes.append(funcao)

    def exigir_pdf(self, user_id):
        if self.pdfs >= self.maximo_pdf:
            raise HTTPException(status_code=429, detail=limites.mensagem_do_limite_pdf(self.maximo_pdf))

    def registar_pdf(self, user_id):
        """Como limites.registar_pdf: primeiro o limite de PDF, depois o pedido "importar_pdf"."""
        self.exigir_pdf(user_id)
        self.registar(user_id, "importar_pdf")


@pytest.fixture(autouse=True)
def limites_por_ip_limpos():
    """Cada teste começa com os contadores por IP do login e do registo a zero (todos os pedidos
    dos testes vêm do mesmo IP, e os contadores ficam na memória entre testes), e com o limite
    do PUT /conta/perfil a zero (todos os testes usam a mesma conta)."""
    limite_ip.limpar_limites_das_rotas_publicas()
    limite_ip.limpar_limite_do_perfil()
    yield
    limite_ip.limpar_limites_das_rotas_publicas()
    limite_ip.limpar_limite_do_perfil()


@pytest.fixture(autouse=True)
def sem_proxies_a_frente(monkeypatch):
    """Nos testes, o X-Forwarded-For simula só o último proxy: o visitante é a entrada mais à direita.
    A forma do Render (2 proxies a frente) tem testes próprios em test_limite_ip.py."""
    monkeypatch.setattr(limite_ip, "PROXIES_A_FRENTE", 0)


@pytest.fixture(autouse=True)
def jwks_sem_rede(monkeypatch):
    """Os testes nunca vão buscar o JWKS ao Supabase: por omissão o JWKS vem vazio (como num projeto
    ainda com o segredo HS256), e os tokens seguem para o get_user imitado. O test_token_supabase.py
    dá-lhe chaves geradas no próprio teste."""
    auth.CHAVES_SUPABASE.limpar()
    monkeypatch.setattr(auth.CHAVES_SUPABASE, "pedir", lambda url: {"keys": []})
    yield
    auth.CHAVES_SUPABASE.limpar()


@pytest.fixture
def limite(monkeypatch):
    limite = Limite()
    # O main e o limites.py usam a mesma função: troca-se nos dois sítios.
    monkeypatch.setattr(main, "registar_pergunta", limite.registar)
    monkeypatch.setattr(limites, "registar_pergunta", limite.registar)
    monkeypatch.setattr(main, "registar_pdf", limite.registar_pdf)
    # O plano lê-se sempre pelo limites.py (exigir_funcao, aviso do resumo): troca-se lá.
    monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: limite.plano)
    return limite


@pytest.fixture
def base_dados(monkeypatch):
    falsa = BaseDadosFalsa()
    monkeypatch.setattr(main, "supabase", falsa)
    return falsa


class SemTabelaResumos:
    """Imita o Supabase antes da sql/016: a tabela resumos_ia não existe (o resumo fica na memória)."""

    def __getattr__(self, nome):
        return lambda *args, **opcoes: self

    def execute(self):
        raise APIError({"code": "PGRST205", "message": "Could not find the table 'public.resumos_ia' in the schema cache"})


@pytest.fixture
def cliente(base_dados, limite, monkeypatch):
    """Um cliente da API já com login feito (como o utilizador "utilizador-teste")."""
    main.app.dependency_overrides[obter_utilizador_atual] = lambda: "utilizador-teste"
    # O DELETE /conta confirma no Supabase: aqui passa o id do obter_utilizador_atual (o que o teste escolher).
    main.app.dependency_overrides[obter_utilizador_confirmado] = lambda user_id=Depends(obter_utilizador_atual): user_id
    # Por omissão, os resumos ficam na memória (como antes da 016); test_resumos_guardados.py testa a tabela.
    monkeypatch.setattr(resumo, "supabase", SemTabelaResumos())
    resumo.RESUMOS_EM_MEMORIA.clear()
    recorrentes._CACHE.clear()  # a cache dos pagamentos que se repetem não passa de um teste para outro
    # Por omissão a conta é PT (sql/020): hoje em Lisboa e moeda EUR, sem ler a tabela assinaturas.
    # O test_perfil.py testa as contas BR.
    monkeypatch.setattr(main, "hoje_do_utilizador", lambda user_id: limites.hoje_em_lisboa())
    monkeypatch.setattr(main, "moeda_da_conta", lambda user_id: "EUR")
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


class ClienteFalso:
    """Imita anthropic.Anthropic(): guarda os argumentos de cada chamada e devolve as respostas dadas."""

    def __init__(self, respostas=None):
        self.chamadas: list[dict] = []
        self.respostas = list(respostas or [])
        self.messages = self

    def __call__(self):
        return self

    def create(self, **argumentos):
        # Cópia: o chat continua a mexer na lista de mensagens depois da chamada.
        self.chamadas.append(copy.deepcopy(argumentos))
        return self.respostas.pop(0)

    def parse(self, **argumentos):
        self.chamadas.append(argumentos)
        return SimpleNamespace(parsed_output=argumentos["output_format"](resumo="ok", alertas=[]), stop_reason="end_turn")


@pytest.fixture
def cliente_falso(monkeypatch):
    def _criar(respostas=None):
        falso = ClienteFalso(respostas)
        monkeypatch.setattr(ia.anthropic, "Anthropic", falso)
        monkeypatch.setattr(ia, "_registar_chamada", lambda *args, **opcoes: None)
        # 9 de novembro de 2026, ao meio-dia em Lisboa: o "hoje" das instruções e do histórico.
        monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc))
        return falso

    return _criar
