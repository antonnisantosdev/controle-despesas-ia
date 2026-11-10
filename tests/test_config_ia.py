"""O que cada plano recebe da IA (limites.py, CONFIG_IA_POR_PLANO) e como isso chega às chamadas."""

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

import ia
import limites
from limites import CONFIG_IA_POR_PLANO, MAX_VOLTAS_CHAT, config_ia_do_plano, primeiro_mes_visivel

# 9 de novembro de 2026, ao meio-dia em Lisboa.
AGORA = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("plano", "effort", "max_tokens", "meses", "memoria", "cache"),
    [
        ("free", "low", 1024, 3, 0, False),
        ("essencial", "low", 2048, 12, 4, False),
        ("completo", "medium", 4096, None, 10, True),
    ],
)
def test_cada_plano_tem_a_sua_configuracao_de_ia(plano, effort, max_tokens, meses, memoria, cache):
    config = CONFIG_IA_POR_PLANO[plano]
    assert (config.effort, config.max_tokens, config.meses_historico, config.memoria_mensagens, config.cache) == (
        effort,
        max_tokens,
        meses,
        memoria,
        cache,
    )


def test_o_chat_tem_no_maximo_3_voltas():
    assert MAX_VOLTAS_CHAT == 3


@pytest.mark.parametrize("plano", [None, "", "premium"])
def test_plano_desconhecido_fica_com_a_configuracao_do_free(plano):
    assert config_ia_do_plano(plano) == CONFIG_IA_POR_PLANO["free"]


@pytest.mark.parametrize(
    ("plano", "hoje", "esperado"),
    [
        ("free", date(2026, 11, 9), "2026-09"),  # o mês atual e os 2 anteriores
        ("free", date(2027, 1, 31), "2026-11"),  # atravessa a mudança de ano
        ("essencial", date(2026, 11, 9), "2025-12"),  # o mês atual e os 11 anteriores
        ("completo", date(2026, 11, 9), None),  # sem limite
    ],
)
def test_primeiro_mes_que_o_plano_ve(plano, hoje, esperado):
    assert primeiro_mes_visivel(CONFIG_IA_POR_PLANO[plano], hoje) == esperado


def test_um_plano_pago_que_terminou_recebe_a_configuracao_do_free(monkeypatch):
    # O Completo acabou ontem: memória, histórico e tokens passam a ser os do Free.
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: ("completo", date(2026, 11, 8)))
    monkeypatch.setattr(limites, "agora_utc", lambda: AGORA)

    plano, config = limites.plano_e_config_ia("utilizador-teste")

    assert plano == "free"
    assert config == CONFIG_IA_POR_PLANO["free"]


def test_um_plano_pago_ativo_recebe_a_sua_configuracao(monkeypatch):
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: ("completo", date(2026, 12, 31)))
    monkeypatch.setattr(limites, "agora_utc", lambda: AGORA)

    assert limites.plano_e_config_ia("utilizador-teste") == ("completo", CONFIG_IA_POR_PLANO["completo"])


# --- As respostas em texto (resumo, orçamento, poupança) usam o esforço e os tokens do plano ---


@pytest.mark.parametrize(("plano", "max_tokens", "effort"), [("free", 1024, "low"), ("completo", 4096, "medium")])
def test_o_resumo_usa_os_tokens_e_o_esforco_do_plano(cliente_falso, plano, max_tokens, effort):
    falso = cliente_falso()

    ia.resumir_mes({"mes": "2026-11"}, config=CONFIG_IA_POR_PLANO[plano])

    assert falso.chamadas[0]["max_tokens"] == max_tokens
    assert falso.chamadas[0]["output_config"] == {"effort": effort}


def test_sem_config_o_resumo_usa_a_do_free(cliente_falso):
    falso = cliente_falso()

    ia.resumir_mes({"mes": "2026-11"})

    assert falso.chamadas[0]["max_tokens"] == 1024


def test_uma_resposta_cortada_vira_erro_ia_e_nao_500(monkeypatch):
    # Com 1024 tokens, uma resposta cortada a meio não passa na validação (ValueError): a rota responde 503.
    def parse_cortado(**argumentos):
        raise ValueError("JSON cortado")

    falso = SimpleNamespace(messages=SimpleNamespace(parse=parse_cortado))
    monkeypatch.setattr(ia.anthropic, "Anthropic", lambda: falso)

    with pytest.raises(ia.ErroIA):
        ia.sugerir_orcamento({"casa": {}}, config=CONFIG_IA_POR_PLANO["free"])


@pytest.mark.parametrize("plano", ["free", "essencial", "completo"])
def test_a_rota_do_resumo_passa_a_config_do_plano(cliente, limite, monkeypatch, plano):
    import main
    from models import ResumoMes

    limite.plano = plano
    recebidas = []
    monkeypatch.setattr(main, "recolher_dados", lambda user_id, mes: {"transacoes_no_mes": 1, "mes": mes})
    monkeypatch.setattr(
        main, "resumir_mes", lambda dados, user_id=None, config=None: recebidas.append(config) or ResumoMes(resumo="ok", alertas=[])
    )

    assert cliente.get("/resumo?mes=2026-11").status_code == 200
    assert recebidas == [CONFIG_IA_POR_PLANO[plano]]
