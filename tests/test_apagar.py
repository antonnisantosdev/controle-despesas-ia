"""Apagar uma movimentação (DELETE /transacoes/{id}) e apagar a conta (DELETE /conta).

Supabase a fingir: nada é apagado de verdade. A demo bloqueada (423) está em test_demo.py.
"""

import pytest
from supabase import AuthApiError

import main
import recorrentes
import resumo
from auth import obter_utilizador_atual

DEMO_USER_ID = "11111111-2222-4333-8444-555555555555"


class ApagarFalso:
    """Imita supabase.table(...).delete().eq(...).execute(): guarda os filtros e devolve as linhas apagadas."""

    def __init__(self, linhas):
        self.linhas = linhas
        self.filtros: dict[str, object] = {}
        self.apagou = False

    def table(self, nome):
        assert nome == "transacoes"
        return self

    def delete(self):
        self.apagou = True
        return self

    def eq(self, coluna, valor):
        self.filtros[coluna] = valor
        return self

    def execute(self):
        apagadas = [linha for linha in self.linhas if all(linha.get(c) == v for c, v in self.filtros.items())]

        class Resposta:
            data = apagadas

        return Resposta


# --- DELETE /transacoes/{id} ---


def test_apagar_transacao_do_proprio_da_204(cliente, monkeypatch):
    falso = ApagarFalso([{"id": 7, "user_id": "utilizador-teste"}])
    monkeypatch.setattr(main, "supabase", falso)
    recorrentes._CACHE["utilizador-teste"] = "antigo"

    resposta = cliente.delete("/transacoes/7")

    assert resposta.status_code == 204
    assert falso.apagou and falso.filtros == {"id": 7, "user_id": "utilizador-teste"}
    # As movimentações mudaram: os pagamentos que se repetem voltam a ser calculados.
    assert "utilizador-teste" not in recorrentes._CACHE


def test_apagar_transacao_de_outro_da_404_igual_a_inexistente(cliente, monkeypatch):
    # A transação 7 existe, mas é de outra pessoa: o filtro por user_id não a encontra.
    monkeypatch.setattr(main, "supabase", ApagarFalso([{"id": 7, "user_id": "outra-pessoa"}]))
    de_outro = cliente.delete("/transacoes/7")
    inexistente = cliente.delete("/transacoes/999")

    assert de_outro.status_code == inexistente.status_code == 404
    assert de_outro.json() == inexistente.json() == {"detail": "Transação não encontrada"}


# --- DELETE /conta ---


@pytest.fixture
def apagados(monkeypatch):
    """Substitui o apagar no Supabase Auth: guarda os ids que se pediram para apagar."""
    lista: list[str] = []
    monkeypatch.setattr(main, "apagar_utilizador", lista.append)
    return lista


def test_apagar_conta_com_confirmacao_da_204(cliente, apagados):
    recorrentes._CACHE["utilizador-teste"] = "antigo"
    resumo.RESUMOS_EM_MEMORIA["utilizador-teste:2026-11:abc"] = "antigo"
    resumo.RESUMOS_EM_MEMORIA["outra-pessoa:2026-11:abc"] = "fica"

    resposta = cliente.request("DELETE", "/conta", json={"confirmacao": "APAGAR"})

    assert resposta.status_code == 204
    # Só a conta do token, nunca outra.
    assert apagados == ["utilizador-teste"]
    assert "utilizador-teste" not in recorrentes._CACHE
    assert list(resumo.RESUMOS_EM_MEMORIA) == ["outra-pessoa:2026-11:abc"]


@pytest.mark.parametrize(
    "corpo",
    [None, {}, {"confirmacao": ""}, {"confirmacao": "apagar"}, {"confirmacao": "APAGAR "}, {"confirmacao": "sim"}],
)
def test_apagar_conta_sem_confirmacao_certa_da_400(cliente, apagados, corpo):
    resposta = cliente.request("DELETE", "/conta", json=corpo)

    assert resposta.status_code == 400
    assert resposta.json() == {"detail": main.MENSAGEM_SEM_CONFIRMACAO}
    assert apagados == []


def test_apagar_conta_nao_aceita_o_id_no_corpo(cliente, apagados):
    # Um user_id no corpo é ignorado: apaga-se sempre quem está no token.
    resposta = cliente.request("DELETE", "/conta", json={"confirmacao": "APAGAR", "user_id": "outra-pessoa"})

    assert resposta.status_code == 204
    assert apagados == ["utilizador-teste"]


@pytest.mark.parametrize("erro", [AuthApiError("detalhe interno com email@exemplo.pt", 500, "unexpected"), RuntimeError("rede")])
def test_apagar_conta_com_supabase_em_baixo_da_502_sem_detalhes(cliente, monkeypatch, capsys, erro):
    def falhar(user_id):
        raise erro

    monkeypatch.setattr(main, "apagar_utilizador", falhar)

    resposta = cliente.request("DELETE", "/conta", json={"confirmacao": "APAGAR"})

    assert resposta.status_code == 502
    assert resposta.json() == {"detail": main.MENSAGEM_APAGAR_CONTA_FALHOU}
    # No log só o tipo do erro, nunca a mensagem do Supabase.
    assert "email@exemplo.pt" not in capsys.readouterr().out


def test_conta_de_demo_nunca_e_apagada_mesmo_sem_a_lista_da_demo(cliente, apagados, monkeypatch):
    # Segunda barreira: mesmo que o obter_utilizador_atual deixasse passar, a rota recusa a conta de demo.
    monkeypatch.setenv("DEMO_USER_ID", DEMO_USER_ID)
    main.app.dependency_overrides[obter_utilizador_atual] = lambda: DEMO_USER_ID

    resposta = cliente.request("DELETE", "/conta", json={"confirmacao": "APAGAR"})

    assert resposta.status_code == 423
    assert apagados == []


def test_apagar_utilizador_usa_o_admin_do_supabase(monkeypatch):
    import auth

    pedidos = []

    class Admin:
        def delete_user(self, user_id):
            pedidos.append(user_id)

    class Auth:
        admin = Admin()

    class Supabase:
        auth = Auth()

    monkeypatch.setattr(auth, "supabase", Supabase())

    auth.apagar_utilizador("utilizador-teste")

    assert pedidos == ["utilizador-teste"]


@pytest.mark.parametrize("transacao_id", ["0", str(2**63)])
def test_id_fora_do_bigint_da_422_sem_chegar_a_base(cliente, transacao_id):
    assert cliente.delete(f"/transacoes/{transacao_id}").status_code == 422
    assert cliente.get(f"/transacoes/{transacao_id}").status_code == 422


def test_confirmacao_enorme_da_422(cliente, apagados):
    assert cliente.request("DELETE", "/conta", json={"confirmacao": "A" * 21}).status_code == 422
    assert apagados == []
