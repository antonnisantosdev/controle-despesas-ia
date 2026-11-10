"""Ferramentas do chat: histórico por plano, vários meses, orçamentos e objetivos (dados inventados)."""

import json
from datetime import date, datetime, timezone

import pytest

import consultas
import ferramentas
import limites
from ferramentas import MAX_MESES_POR_CHAMADA, executar_ferramenta, meses_entre
from ia import PedidoInvalido
from models import GastoCategoria, LinhaOrcamento, Objetivo


@pytest.fixture
def dados(monkeypatch):
    """Hoje é 9 de novembro de 2026. As consultas devolvem dados inventados e guardam quem as pediu."""
    pedidos = []
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc))

    def gastos_do_mes(user_id, mes):
        pedidos.append(("mes", user_id, mes))
        return [GastoCategoria(categoria="lazer", total=12.5)]

    def gastos_de_varios_meses(user_id, meses):
        pedidos.append(("varios", user_id, meses))
        return {mes: [GastoCategoria(categoria="casa", total=100.0)] for mes in meses}

    def planeamento_do_mes(user_id, mes):
        pedidos.append(("orcamentos", user_id, mes))
        return [LinhaOrcamento(categoria="restaurantes", limite=50.0, gasto=42.0)]

    def listar_objetivos(user_id):
        pedidos.append(("objetivos", user_id))
        return [Objetivo(id=1, nome="Férias", valor_alvo=900.0, data_alvo=date(2027, 7, 1), valor_poupado=150.0)]

    monkeypatch.setattr(ferramentas, "gastos_do_mes", gastos_do_mes)
    monkeypatch.setattr(ferramentas, "gastos_de_varios_meses", gastos_de_varios_meses)
    monkeypatch.setattr(ferramentas, "planeamento_do_mes", planeamento_do_mes)
    monkeypatch.setattr(ferramentas, "listar_objetivos", listar_objetivos)
    return pedidos


def correr(nome, argumentos, plano):
    return json.loads(executar_ferramenta(nome, argumentos, "utilizador-teste", plano))


# --- Histórico em meses de calendário ---


@pytest.mark.parametrize(
    ("plano", "mes", "dentro"),
    [
        ("free", "2026-09", True),  # o mês atual e os 2 anteriores
        ("free", "2026-08", False),
        ("essencial", "2025-12", True),  # o mês atual e os 11 anteriores
        ("essencial", "2025-11", False),
        ("completo", "2019-01", True),  # sem limite
    ],
)
def test_cada_plano_ve_o_seu_historico(dados, plano, mes, dentro):
    resultado = correr("gastos_por_categoria", {"mes": mes}, plano)

    if dentro:
        assert resultado == [{"categoria": "lazer", "total": 12.5}]
    else:
        assert resultado["fora_do_historico"] is True
        assert dados == []  # nem se chega a ler a base de dados


def test_fora_do_historico_diz_desde_quando_e_sugere_mudar_de_plano(dados):
    resultado = correr("gastos_por_categoria", {"mes": "2026-01"}, "free")

    assert "plano Free" in resultado["mensagem"]
    assert "desde 2026-09" in resultado["mensagem"]
    assert "mudar para um plano" in resultado["mensagem"]


def test_um_plano_pago_que_terminou_ve_so_o_historico_do_free(dados):
    # O plano chega aqui já como "free" (plano_efetivo): é o que o main passa.
    assert correr("orcamentos_do_mes", {"mes": "2026-05"}, "free")["fora_do_historico"] is True


def test_plano_desconhecido_ve_so_o_historico_do_free(dados):
    assert correr("gastos_por_categoria", {"mes": "2026-08"}, None)["fora_do_historico"] is True


# --- Vários meses ---


def test_varios_meses_numa_so_consulta(dados):
    resultado = correr("gastos_de_varios_meses", {"mes_inicio": "2026-09", "mes_fim": "2026-11"}, "free")

    assert list(resultado["meses"]) == ["2026-09", "2026-10", "2026-11"]
    assert "aviso" not in resultado
    assert dados == [("varios", "utilizador-teste", ["2026-09", "2026-10", "2026-11"])]


def test_intervalo_que_comeca_antes_do_plano_e_cortado_com_aviso(dados):
    resultado = correr("gastos_de_varios_meses", {"mes_inicio": "2026-01", "mes_fim": "2026-10"}, "free")

    assert list(resultado["meses"]) == ["2026-09", "2026-10"]
    assert "desde 2026-09" in resultado["aviso"]


def test_intervalo_todo_fora_do_plano(dados):
    resultado = correr("gastos_de_varios_meses", {"mes_inicio": "2026-01", "mes_fim": "2026-03"}, "free")

    assert resultado["fora_do_historico"] is True
    assert dados == []


def test_no_maximo_12_meses_por_chamada(dados):
    assert MAX_MESES_POR_CHAMADA == 12
    assert len(correr("gastos_de_varios_meses", {"mes_inicio": "2025-12", "mes_fim": "2026-11"}, "completo")["meses"]) == 12

    with pytest.raises(PedidoInvalido, match="no máximo 12 meses"):
        correr("gastos_de_varios_meses", {"mes_inicio": "2025-01", "mes_fim": "2026-11"}, "completo")


def test_intervalo_ao_contrario_da_erro(dados):
    with pytest.raises(PedidoInvalido):
        correr("gastos_de_varios_meses", {"mes_inicio": "2026-11", "mes_fim": "2026-10"}, "completo")


@pytest.mark.parametrize("mes", ["2026-13", "outubro", "2026-1", None, 202610])
def test_mes_invalido_da_erro_para_a_ia_corrigir(dados, mes):
    with pytest.raises(PedidoInvalido, match="AAAA-MM"):
        correr("gastos_por_categoria", {"mes": mes}, "completo")


def test_meses_entre_atravessa_o_ano():
    assert meses_entre("2026-11", "2027-02") == ["2026-11", "2026-12", "2027-01", "2027-02"]


# --- Orçamentos e objetivos ---


def test_orcamentos_do_mes(dados):
    resultado = correr("orcamentos_do_mes", {"mes": "2026-11"}, "essencial")

    assert resultado == [{"categoria": "restaurantes", "limite": 50.0, "gasto": 42.0}]
    assert dados == [("orcamentos", "utilizador-teste", "2026-11")]


def test_objetivos_de_poupanca(dados):
    resultado = correr("objetivos_de_poupanca", {}, "free")

    assert resultado[0]["nome"] == "Férias"
    assert resultado[0]["data_alvo"] == "2027-07-01"
    assert dados == [("objetivos", "utilizador-teste")]


def test_a_ia_nao_escolhe_o_user_id(dados):
    # Mesmo que a IA mande um user_id nos argumentos, vale sempre o do token.
    correr("gastos_por_categoria", {"mes": "2026-11", "user_id": "outra-pessoa"}, "completo")

    assert dados == [("mes", "utilizador-teste", "2026-11")]


def test_ferramenta_desconhecida(dados):
    with pytest.raises(PedidoInvalido, match="desconhecida"):
        correr("apagar_tudo", {}, "completo")


# --- A consulta de vários meses ---


def test_gastos_de_varios_meses_separa_por_mes(monkeypatch):
    linhas = [
        {"data": "2026-10-03", "categoria": "casa", "valor": -400.0},
        {"data": "2026-10-20", "categoria": "casa", "valor": -50.0},
        {"data": "2026-11-02", "categoria": "lazer", "valor": -9.99},
        {"data": "2026-11-05", "categoria": "rendimento", "valor": 1200.0},  # não é gasto
    ]
    monkeypatch.setattr(consultas, "ler_todas", lambda nova_consulta: linhas)

    resultado = consultas.gastos_de_varios_meses("utilizador-teste", ["2026-09", "2026-10", "2026-11"])

    assert resultado["2026-09"] == []
    assert resultado["2026-10"] == [GastoCategoria(categoria="casa", total=450.0)]
    assert resultado["2026-11"] == [GastoCategoria(categoria="lazer", total=9.99)]
