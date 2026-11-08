"""Preparação partilhada por todos os testes (o pytest lê este ficheiro sozinho).

Os testes nunca falam com o Supabase nem com a Anthropic verdadeiros: as chaves são falsas,
e a base de dados e a IA são substituídas por imitações. Assim os testes são rápidos,
não gastam créditos e podem correr no GitHub, onde não existe o .env.
"""

import os

# Têm de vir antes de importar a API: o database.py lê-as logo ao arrancar.
# Ao contrário do .env, estas ganham sempre (o load_dotenv não substitui variáveis que já existem).
os.environ["SUPABASE_URL"] = "https://exemplo.supabase.co"
os.environ["SUPABASE_KEY"] = "chave-falsa"
os.environ["ANTHROPIC_API_KEY"] = "chave-falsa"

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import limites  # noqa: E402
import main  # noqa: E402
from auth import obter_utilizador_atual  # noqa: E402


class BaseDadosFalsa:
    """Imita o cliente do Supabase: guarda o que se grava e devolve-o como se tivesse entrado."""

    def __init__(self):
        self.gravado: list[dict] = []
        self._dados = None

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

        class Resposta:
            data = linhas

        return Resposta


class Limite:
    """Imita o limite diário de perguntas à IA, sem tocar na tabela uso_ia."""

    def __init__(self, maximo=30):
        self.maximo = maximo
        self.perguntas = 0

    def registar(self, user_id):
        if self.perguntas >= self.maximo:
            raise HTTPException(status_code=429, detail="Limite diário atingido")
        self.perguntas += 1


@pytest.fixture
def limite(monkeypatch):
    limite = Limite()
    # O main e o limites.py usam a mesma função: troca-se nos dois sítios.
    monkeypatch.setattr(main, "registar_pergunta", limite.registar)
    monkeypatch.setattr(limites, "registar_pergunta", limite.registar)
    return limite


@pytest.fixture
def base_dados(monkeypatch):
    falsa = BaseDadosFalsa()
    monkeypatch.setattr(main, "supabase", falsa)
    return falsa


@pytest.fixture
def cliente(base_dados, limite):
    """Um cliente da API já com login feito (como o utilizador "utilizador-teste")."""
    main.app.dependency_overrides[obter_utilizador_atual] = lambda: "utilizador-teste"
    main.RESUMOS_JA_FEITOS.clear()
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()
