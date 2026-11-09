"""Alertas de orçamento do mês atual: a partir de 90% do orçamento gasto, sem IA."""

from datetime import datetime, timezone

import pytest

import limites
import main
from models import LinhaOrcamento
from orcamento import alertas_de_orcamento


def linha(categoria, limite, gasto):
    return LinhaOrcamento(categoria=categoria, limite=limite, gasto=gasto)


@pytest.mark.parametrize(
    ("gasto", "nivel"),
    [
        (89.99, None),  # abaixo dos 90%: sem alerta
        (90.0, "perto"),  # 90% certos já avisa
        (99.99, "perto"),
        (100.0, "atingido"),  # chegou ao orçamento
        (150.0, "atingido"),
    ],
)
def test_os_limiares_de_90_e_100_por_cento(gasto, nivel):
    alertas = alertas_de_orcamento([linha("lazer", 100.0, gasto)])

    assert [alerta.nivel for alerta in alertas] == ([nivel] if nivel else [])


def test_categorias_sem_orcamento_nao_dao_alerta():
    assert alertas_de_orcamento([linha("outros", None, 500.0), linha("casa", 0.0, 10.0)]) == []


def test_primeiro_os_atingidos_depois_os_mais_perto():
    alertas = alertas_de_orcamento(
        [
            linha("lazer", 100.0, 91.0),
            linha("casa", 100.0, 120.0),
            linha("restaurantes", 50.0, 49.0),  # 98%
            linha("transporte", 100.0, 10.0),
        ]
    )

    assert [(alerta.categoria, alerta.nivel) for alerta in alertas] == [
        ("casa", "atingido"),
        ("restaurantes", "perto"),
        ("lazer", "perto"),
    ]


def test_a_rota_usa_o_mes_atual_de_lisboa_e_nao_gasta_pedidos(cliente, limite, monkeypatch):
    meses = []

    def planeamento(user_id, mes):
        meses.append(mes)
        return [linha("lazer", 100.0, 95.5)]

    monkeypatch.setattr(main, "planeamento_do_mes", planeamento)
    # 23:30 UTC de 31 de julho já é 1 de agosto em Lisboa (verão, UTC+1): o mês atual é agosto.
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 7, 31, 23, 30, tzinfo=timezone.utc))

    resposta = cliente.get("/orcamentos/alertas")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "mes": "2026-08",
        "alertas": [{"categoria": "lazer", "gasto": 95.5, "limite": 100.0, "nivel": "perto"}],
    }
    assert meses == ["2026-08"]  # 00:30 de 1 de agosto em Lisboa
    assert limite.perguntas == 0
