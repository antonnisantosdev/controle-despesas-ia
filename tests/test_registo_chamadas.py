"""Registo de cada chamada à IA na tabela chamadas_ia, com o user_id de quem a fez."""

import time
from types import SimpleNamespace

import pytest

import ia


class ChamadasIaFalsa:
    """Imita a tabela chamadas_ia. Com sem_coluna_user_id, faz como o Supabase antes da migração 014."""

    def __init__(self, sem_coluna_user_id=False, sempre_em_baixo=False):
        self.sem_coluna_user_id = sem_coluna_user_id
        self.sempre_em_baixo = sempre_em_baixo
        self.gravadas: list[dict] = []
        self._linha = None

    def table(self, nome):
        assert nome == "chamadas_ia"
        return self

    def insert(self, linha):
        self._linha = linha
        return self

    def execute(self):
        if self.sempre_em_baixo:
            raise RuntimeError("sem rede")
        if self.sem_coluna_user_id and "user_id" in self._linha:
            raise RuntimeError("Could not find the 'user_id' column of 'chamadas_ia' in the schema cache")
        self.gravadas.append(self._linha)
        return self


# Uma resposta inventada da Anthropic: só interessa o uso de tokens.
RESPOSTA = SimpleNamespace(usage=SimpleNamespace(input_tokens=2000, output_tokens=500), parsed_output="ok")


@pytest.fixture
def tabela(monkeypatch):
    falsa = ChamadasIaFalsa()
    monkeypatch.setattr(ia, "supabase", falsa)
    monkeypatch.delenv("IA_ORIGEM", raising=False)
    return falsa


def test_regista_o_user_id_de_quem_fez_a_chamada(tabela):
    ia._registar_chamada("chat", RESPOSTA, time.perf_counter(), "utilizador-teste")

    assert len(tabela.gravadas) == 1
    assert tabela.gravadas[0]["user_id"] == "utilizador-teste"
    assert tabela.gravadas[0]["tokens_entrada"] == 2000
    assert tabela.gravadas[0]["origem"] == "app"


def test_sem_user_id_a_linha_nao_leva_a_coluna(tabela):
    # O script de avaliação não tem utilizador: grava como antes.
    ia._registar_chamada("categorizar", RESPOSTA, time.perf_counter())

    assert len(tabela.gravadas) == 1
    assert "user_id" not in tabela.gravadas[0]


def test_sem_a_migracao_014_grava_na_mesma_sem_o_user_id(tabela):
    tabela.sem_coluna_user_id = True

    ia._registar_chamada("chat", RESPOSTA, time.perf_counter(), "utilizador-teste")

    # O registo não se perde: entra sem o user_id, com os tokens e o custo.
    assert len(tabela.gravadas) == 1
    assert "user_id" not in tabela.gravadas[0]
    assert tabela.gravadas[0]["tokens_saida"] == 500


def test_se_a_base_de_dados_falhar_o_pedido_nao_rebenta(tabela):
    tabela.sempre_em_baixo = True

    ia._registar_chamada("chat", RESPOSTA, time.perf_counter(), "utilizador-teste")  # não pode lançar erro

    assert tabela.gravadas == []
