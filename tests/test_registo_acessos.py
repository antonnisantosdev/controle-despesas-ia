"""RGPD: o access log do uvicorn não guarda o IP de quem visita a API."""

import logging

from uvicorn.logging import AccessFormatter

import main  # noqa: F401  (importar a API liga o filtro no logger "uvicorn.access")

FORMATO_UVICORN = '%s - "%s %s HTTP/%s" %d'


def registar_acesso(caplog, ip="203.0.113.7:0", caminho="/recorrentes"):
    """Escreve uma linha como o uvicorn faz e devolve o registo que ficou."""
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        logging.getLogger("uvicorn.access").info(FORMATO_UVICORN, ip, "GET", caminho, "1.1", 200)
    assert len(caplog.records) == 1
    return caplog.records[0]


def test_access_log_sem_ip(caplog):
    registo = registar_acesso(caplog)
    assert "203.0.113.7" not in registo.getMessage()
    assert registo.getMessage() == '- - "GET /recorrentes HTTP/1.1" 200'


def test_access_log_mantem_caminho_com_query(caplog):
    registo = registar_acesso(caplog, ip="[2001:db8::1]:443", caminho="/resumo?mes=2026-10")
    assert "2001:db8" not in registo.getMessage()
    assert '"GET /resumo?mes=2026-10 HTTP/1.1" 200' in registo.getMessage()


def test_formato_do_uvicorn_continua_a_funcionar(caplog):
    # O formatador do uvicorn desempacota os 5 argumentos: o filtro tem de manter o número.
    registo = registar_acesso(caplog)
    linha = AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s', use_colors=False).format(registo)
    assert linha == '- - "GET /recorrentes HTTP/1.1" 200 OK'


def test_outras_mensagens_nao_mudam(caplog):
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        logging.getLogger("uvicorn.access").info("mensagem sem argumentos")
    assert caplog.records[0].getMessage() == "mensagem sem argumentos"
