"""Contadores de pedidos à IA e de PDF no fuso do país da conta (sql/022, pais_mudado_em).

Cada conta volta a zero à meia-noite do seu país. Só no período em que mudou de país se conta desde o
início mais antigo entre Lisboa e São Paulo: mudar de país nunca dá pedidos a mais.
"""

from datetime import datetime, timedelta, timezone

import pytest

import limites
from conftest import INICIO_DA_CONTA_REAL
from limites import Assinatura

UTC = timezone.utc
# 00:30 em Lisboa (inverno, UTC+0) = 21:30 do dia anterior em São Paulo (UTC-3).
DEPOIS_DA_MEIA_NOITE_EM_LISBOA = datetime(2026, 11, 13, 0, 30, tzinfo=UTC)
MEIA_NOITE_LISBOA = datetime(2026, 11, 13, 0, 0, tzinfo=UTC)
MEIA_NOITE_SAO_PAULO_ONTEM = datetime(2026, 11, 12, 3, 0, tzinfo=UTC)


def conta(pais="PT", mudado_em=None, com_022=True):
    return Assinatura("essencial", None, pais=pais, com_perfil=True, pais_mudado_em=mudado_em, com_mudanca_pais=com_022)


def test_conta_pt_volta_a_zero_a_meia_noite_de_lisboa():
    inicio = limites.inicio_dos_contadores("dia", DEPOIS_DA_MEIA_NOITE_EM_LISBOA, conta("PT"))

    assert inicio == MEIA_NOITE_LISBOA


def test_conta_br_conta_desde_a_meia_noite_de_sao_paulo():
    inicio = limites.inicio_dos_contadores("dia", DEPOIS_DA_MEIA_NOITE_EM_LISBOA, conta("BR"))

    assert inicio == MEIA_NOITE_SAO_PAULO_ONTEM


def test_o_mes_do_free_de_uma_conta_pt_comeca_no_dia_1_de_lisboa():
    agora = datetime(2026, 12, 1, 0, 30, tzinfo=UTC)

    assert limites.inicio_dos_contadores("mes", agora, conta("PT")) == datetime(2026, 12, 1, 0, 0, tzinfo=UTC)


def test_no_periodo_em_que_mudou_de_pais_conta_desde_o_mais_antigo():
    # Mudou de BR para PT ontem às 10:00 UTC, depois da meia-noite de São Paulo: os pedidos desse dia contam.
    mudou = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)

    inicio = limites.inicio_dos_contadores("dia", DEPOIS_DA_MEIA_NOITE_EM_LISBOA, conta("PT", mudou))

    assert inicio == MEIA_NOITE_SAO_PAULO_ONTEM


def test_mudanca_antiga_ja_nao_conta():
    mudou = DEPOIS_DA_MEIA_NOITE_EM_LISBOA - timedelta(days=3)

    inicio = limites.inicio_dos_contadores("dia", DEPOIS_DA_MEIA_NOITE_EM_LISBOA, conta("PT", mudou))

    assert inicio == MEIA_NOITE_LISBOA


@pytest.mark.parametrize("assinatura", [None, conta("PT", com_022=False)])
def test_sem_conta_ou_sem_a_022_conta_desde_o_mais_antigo(assinatura):
    inicio = limites.inicio_dos_contadores("dia", DEPOIS_DA_MEIA_NOITE_EM_LISBOA, assinatura)

    assert inicio == MEIA_NOITE_SAO_PAULO_ONTEM


def test_data_de_mudanca_ilegivel_conta_como_mudanca_recente():
    mudou = limites._mudanca_de_pais("isto-nao-e-uma-data")

    inicio = limites.inicio_dos_contadores("dia", DEPOIS_DA_MEIA_NOITE_EM_LISBOA, conta("PT", mudou))

    assert inicio == MEIA_NOITE_SAO_PAULO_ONTEM


def test_mudar_de_pais_nunca_abre_uma_janela_nova():
    # Fez pedidos no Brasil às 22:00 de Brasília (01:00 UTC) e muda para Portugal logo a seguir.
    # Se a conta passasse já ao dia de Lisboa (que começou às 00:00 UTC), esses pedidos ficavam de fora.
    agora = datetime(2026, 11, 13, 1, 5, tzinfo=UTC)
    pedidos_em = datetime(2026, 11, 13, 1, 0, tzinfo=UTC)
    mudou = datetime(2026, 11, 13, 1, 2, tzinfo=UTC)

    inicio = limites.inicio_dos_contadores("dia", agora, conta("PT", mudou))

    assert inicio <= pedidos_em
    assert inicio == MEIA_NOITE_SAO_PAULO_ONTEM


def test_os_contadores_usam_a_assinatura_da_conta(monkeypatch):
    monkeypatch.setattr(limites, "inicio_dos_contadores_da_conta", INICIO_DA_CONTA_REAL)
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: conta("PT"))

    inicio = limites.inicio_dos_contadores_da_conta("utilizador-teste", "dia", DEPOIS_DA_MEIA_NOITE_EM_LISBOA)

    assert inicio == MEIA_NOITE_LISBOA


def test_a_assinatura_le_a_data_da_mudanca(monkeypatch):
    linha = {
        "plano": "free",
        "ativo_ate": None,
        "pais": "PT",
        "paises_bancos": ["PT"],
        "moeda": "EUR",
        "boas_vindas_em": None,
        "pais_mudado_em": "2026-11-12T10:00:00+00:00",
    }

    class Assinaturas:
        def table(self, nome):
            return self

        def select(self, colunas):
            return self

        def eq(self, *args):
            return self

        def execute(self):
            return type("Resposta", (), {"data": [linha]})()

    monkeypatch.setattr(limites, "supabase", Assinaturas())

    lida = limites.assinatura_do_utilizador("utilizador-teste")

    assert lida.com_mudanca_pais is True
    assert lida.pais_mudado_em == datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
