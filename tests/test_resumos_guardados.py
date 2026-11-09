"""Resumo do mês guardado na tabela resumos_ia (sql/016): se os números não mudaram, não gasta outro pedido."""

import pytest

import main
import resumo
from models import ResumoMes


class TabelaResumosFalsa:
    """Imita a tabela resumos_ia: uma linha por (user_id, mes); o upsert substitui a do mesmo mês."""

    def __init__(self):
        self.linhas: dict[tuple[str, str], dict] = {}
        self.upserts = 0
        self._filtros: dict = {}
        self._gravar: dict | None = None

    def table(self, nome):
        assert nome == "resumos_ia"
        self._filtros, self._gravar = {}, None
        return self

    def select(self, *args, **opcoes):
        return self

    def eq(self, campo, valor):
        self._filtros[campo] = valor
        return self

    def upsert(self, linha, on_conflict=None):
        assert on_conflict == "user_id,mes"
        self._gravar = linha
        return self

    def execute(self):
        if self._gravar is not None:
            self.upserts += 1
            self.linhas[(self._gravar["user_id"], self._gravar["mes"])] = self._gravar
            self.data = [self._gravar]
            return self
        linha = self.linhas.get((self._filtros["user_id"], self._filtros["mes"]))
        iguais = linha is not None and linha["assinatura"] == self._filtros["assinatura"]
        self.data = [linha] if iguais else []
        return self


@pytest.fixture
def tabela(cliente, monkeypatch):
    falsa = TabelaResumosFalsa()
    monkeypatch.setattr(resumo, "supabase", falsa)
    return falsa


@pytest.fixture
def ia(monkeypatch):
    chamadas = []

    def resumir_mes(dados, user_id=None):
        chamadas.append(dados["despesas"])
        return ResumoMes(resumo=f"Gastaste {dados['despesas']} €.", alertas=[{"nivel": "atencao", "mensagem": "Cuidado"}])

    monkeypatch.setattr(main, "resumir_mes", resumir_mes)
    return chamadas


def test_o_resumo_fica_na_tabela_e_sobrevive_a_um_reinicio(cliente, tabela, ia, limite, monkeypatch):
    monkeypatch.setattr(main, "recolher_dados", lambda user_id, mes: {"transacoes_no_mes": 2, "despesas": 40.0})

    primeiro = cliente.get("/resumo?mes=2026-10").json()
    resumo.RESUMOS_EM_MEMORIA.clear()  # como se o Render tivesse reiniciado
    segundo = cliente.get("/resumo?mes=2026-10").json()

    assert primeiro == segundo == {
        "resumo": "Gastaste 40.0 €.",
        "alertas": [{"nivel": "atencao", "mensagem": "Cuidado"}],
    }
    assert ia == [40.0]  # a IA só escreveu uma vez
    assert limite.funcoes == ["resumo"]  # e só se gastou um pedido
    assert resumo.RESUMOS_EM_MEMORIA == {}  # com a tabela, a memória não é usada


def test_numeros_novos_fazem_um_resumo_novo_que_substitui_o_antigo(cliente, tabela, ia, limite, monkeypatch):
    dados = {"transacoes_no_mes": 2, "despesas": 40.0}
    monkeypatch.setattr(main, "recolher_dados", lambda user_id, mes: dict(dados))

    cliente.get("/resumo?mes=2026-10")
    dados["despesas"] = 55.0  # entrou uma despesa nova
    resposta = cliente.get("/resumo?mes=2026-10")

    assert resposta.json()["resumo"] == "Gastaste 55.0 €."
    assert ia == [40.0, 55.0]
    assert limite.perguntas == 2
    assert len(tabela.linhas) == 1  # um só resumo por utilizador e mês
    assert tabela.linhas[("utilizador-teste", "2026-10")]["texto"] == "Gastaste 55.0 €."


def test_meses_diferentes_tem_resumos_diferentes(cliente, tabela, ia, limite, monkeypatch):
    monkeypatch.setattr(main, "recolher_dados", lambda user_id, mes: {"transacoes_no_mes": 2, "despesas": 40.0})

    cliente.get("/resumo?mes=2026-09")
    cliente.get("/resumo?mes=2026-10")

    assert len(tabela.linhas) == 2


def test_sem_a_tabela_o_resumo_fica_na_memoria(cliente, ia, limite, monkeypatch):
    # O fixture cliente imita o Supabase antes da 016 (a tabela resumos_ia não existe).
    monkeypatch.setattr(main, "recolher_dados", lambda user_id, mes: {"transacoes_no_mes": 2, "despesas": 40.0})

    cliente.get("/resumo?mes=2026-10")
    cliente.get("/resumo?mes=2026-10")

    assert ia == [40.0]
    assert len(resumo.RESUMOS_EM_MEMORIA) == 1


def test_a_assinatura_nao_depende_da_ordem_das_chaves():
    assert resumo.assinatura_dos_dados({"a": 1, "b": 2}) == resumo.assinatura_dos_dados({"b": 2, "a": 1})
    assert resumo.assinatura_dos_dados({"a": 1}) != resumo.assinatura_dos_dados({"a": 2})
    assert len(resumo.assinatura_dos_dados({"a": 1})) == 64  # SHA-256 em hexadecimal
