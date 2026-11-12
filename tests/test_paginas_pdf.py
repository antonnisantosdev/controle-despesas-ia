"""Limite de páginas de um extrato em PDF: conta-se antes de chamar a IA e antes de gastar um pedido."""

import pytest

import main
from importar_csv import PdfIlegivel, contar_paginas_pdf
from limites import MAX_PAGINAS_PDF
from models import ExtratoPdf, MovimentoPdf


def pdf_com_paginas(n: int) -> bytes:
    """Um PDF mínimo, inventado, com n páginas em branco (escrito à mão, sem bibliotecas)."""
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [" + b" ".join(f"{3 + i} 0 R".encode() for i in range(n)) + f"] /Count {n} >>".encode(),
    ]
    objetos += [b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>"] * n

    pdf = b"%PDF-1.4\n"
    posicoes = []
    for numero, corpo in enumerate(objetos, start=1):
        posicoes.append(len(pdf))
        pdf += f"{numero} 0 obj\n".encode() + corpo + b"\nendobj\n"
    inicio_xref = len(pdf)
    pdf += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    pdf += b"".join(f"{posicao:010d} 00000 n \n".encode() for posicao in posicoes)
    pdf += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n".encode()
    return pdf


@pytest.fixture
def ia(monkeypatch):
    """Substitui a IA: lê sempre um movimento e categoriza como "outros". Guarda o user_id de cada chamada."""
    chamadas = []

    def ler_extrato_pdf(pdf, user_id=None, local=None):
        chamadas.append(("ler_extrato_pdf", user_id))
        return ExtratoPdf(movimentos=[MovimentoPdf(data="2026-10-01", descricao="CAFE", valor=-1.2, saldo=None)])

    def categorizar(transacoes, user_id=None, local=None):
        chamadas.append(("categorizar", user_id))
        return ["outros"] * len(transacoes)

    monkeypatch.setattr(main, "ler_extrato_pdf", ler_extrato_pdf)
    monkeypatch.setattr(main, "categorizar", categorizar)
    return chamadas


def importar_pdf(cliente, conteudo):
    return cliente.post("/transacoes/importar", files={"ficheiro": ("extrato.pdf", conteudo, "application/pdf")})


@pytest.mark.parametrize("paginas", [1, MAX_PAGINAS_PDF])
def test_pdf_dentro_do_limite_e_importado(cliente, monkeypatch, ia, limite, paginas):
    monkeypatch.setattr(main, "contar_paginas_pdf", lambda pdf: paginas)

    resposta = importar_pdf(cliente, b"%PDF-1.4 extrato inventado")

    assert resposta.status_code == 201
    assert limite.perguntas == 1
    # A IA recebe o user_id, para o custo ficar registado em nome de quem importou.
    assert ia == [("ler_extrato_pdf", "utilizador-teste"), ("categorizar", "utilizador-teste")]


def test_pdf_acima_do_limite_e_recusado_sem_gastar_pedido(cliente, monkeypatch, ia, limite):
    monkeypatch.setattr(main, "contar_paginas_pdf", lambda pdf: MAX_PAGINAS_PDF + 1)

    resposta = importar_pdf(cliente, b"%PDF-1.4 extrato inventado")

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == (
        f"Este PDF tem {MAX_PAGINAS_PDF + 1} páginas. O máximo é {MAX_PAGINAS_PDF}. "
        "Divide o extrato em partes mais pequenas."
    )
    assert limite.perguntas == 0
    assert ia == []


def test_pdf_ilegivel_e_recusado_sem_gastar_pedido(cliente, monkeypatch, ia, limite):
    def estragado(pdf):
        raise PdfIlegivel("EOF marker not found")

    monkeypatch.setattr(main, "contar_paginas_pdf", estragado)

    resposta = importar_pdf(cliente, b"%PDF-1.4 estragado")

    assert resposta.status_code == 422
    assert limite.perguntas == 0
    assert ia == []


def test_o_maximo_de_paginas_e_10():
    assert MAX_PAGINAS_PDF == 10


# --- Com o pypdf verdadeiro (saltam se o pypdf ainda não estiver instalado no .venv) ---


@pytest.mark.parametrize("paginas", [1, 11])
def test_conta_as_paginas_de_um_pdf_verdadeiro(paginas):
    pytest.importorskip("pypdf")
    assert contar_paginas_pdf(pdf_com_paginas(paginas)) == paginas


def test_um_pdf_estragado_da_pdf_ilegivel():
    pytest.importorskip("pypdf")
    with pytest.raises(PdfIlegivel):
        contar_paginas_pdf(b"%PDF-1.4 receita de bolo")


def test_pdf_verdadeiro_com_11_paginas_e_recusado(cliente, ia, limite):
    pytest.importorskip("pypdf")

    resposta = importar_pdf(cliente, pdf_com_paginas(11))

    assert resposta.status_code == 400
    assert limite.perguntas == 0
    assert ia == []


def test_pdf_verdadeiro_com_1_pagina_e_aceite(cliente, ia, limite):
    pytest.importorskip("pypdf")

    resposta = importar_pdf(cliente, pdf_com_paginas(1))

    assert resposta.status_code == 201
    assert limite.perguntas == 1


def test_pdf_com_milhares_de_paginas_para_de_contar_no_teto():
    # Um PDF feito de propósito com milhares de páginas vazias não pode prender o servidor a contá-las.
    pytest.importorskip("pypdf")
    from importar_csv import MAX_ENTRADAS_ARVORE_PDF

    assert contar_paginas_pdf(pdf_com_paginas(5000)) == MAX_ENTRADAS_ARVORE_PDF + 1


def test_pdf_com_milhares_de_paginas_e_recusado_sem_numero_exato(cliente, ia, limite):
    pytest.importorskip("pypdf")

    resposta = importar_pdf(cliente, pdf_com_paginas(5000))

    assert resposta.status_code == 400
    assert "mais de" in resposta.json()["detail"]
    assert limite.perguntas == 0
    assert ia == []
