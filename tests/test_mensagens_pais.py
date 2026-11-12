"""Mensagens da API por país (Fase 1 Brasil, passo 8): PT-PT e PT-BR, escolhidas pelo país da conta.

Também a memória da assinatura em cada pedido (limites._ASSINATURAS_DO_PEDIDO): o país não custa leituras a mais.
Dados inventados; sem Supabase nem IA verdadeiros.
"""

import re
from datetime import date
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

import limites
import main
import produtos
import relatorio
from limites import Assinatura
from mensagens import MENSAGENS, Local, msg

BR = Local(pais="BR", moeda="BRL")
FRONTEND = Path(__file__).parent.parent / "frontend" / "src" / "lib"


@pytest.fixture
def conta_br(monkeypatch):
    """A conta do pedido vive no Brasil, com a moeda em reais (o main e o limites.py leem-na pela mesma função)."""
    monkeypatch.setattr(limites, "local_do_utilizador", lambda user_id: BR)
    monkeypatch.setattr(main, "local_do_utilizador", lambda user_id: BR)


# --- msg() e o dicionário ---


def test_msg_escolhe_o_pais_e_troca_os_valores():
    assert msg("limite_pedidos_dia", "PT", limite=20).startswith("Chegaste ao limite de hoje. Já usaste os 20 ")
    assert msg("limite_pedidos_dia", "BR", limite=20).startswith("Você chegou ao limite de hoje. Você já usou os 20 ")


@pytest.mark.parametrize("pais", [None, "", "ES", "pt"])
def test_pais_desconhecido_fica_em_pt(pais):
    assert msg("chat_falhou", pais) == "O chat falhou. Tenta mais tarde."


def test_todas_as_mensagens_tem_pt_e_br_com_os_mesmos_valores():
    for chave, textos in MENSAGENS.items():
        assert set(textos) == {"PT", "BR"}, chave
        assert set(re.findall(r"\{(\w+)\}", textos["PT"])) == set(re.findall(r"\{(\w+)\}", textos["BR"])), chave


# Palavras do PT-PT que não podem aparecer nos textos BR (tratar por "tu" e vocabulário de Portugal).
PALAVRAS_SO_PT = (
    "Chegaste", "podes", "Tenta ", "teu ", "tua ", "tuas ", "Escolhe ", "Usa ", "Divide", "Confirma ", "Grava",
    "palavra-passe", "ficheiro", "fotografia", "talão", "definições", "Importámos", "connosco", "precisares",
)  # fmt: skip


def test_textos_br_tratam_por_voce_e_usam_palavras_do_brasil():
    for chave, textos in MENSAGENS.items():
        for palavra in PALAVRAS_SO_PT:
            assert palavra not in textos["BR"], (chave, palavra)


def test_o_limite_de_pdf_continua_a_ser_detetado_pelo_frontend():
    # api.ts (eLimitePdf) distingue este 429 do dos pedidos por "extratos PDF".
    api = (FRONTEND / "api.ts").read_text(encoding="utf-8")
    assert 'erro.detalhe.includes("extratos PDF")' in api
    for pais in ("PT", "BR"):
        assert "extratos PDF" in limites.mensagem_do_limite_pdf(15, pais)
        assert "extratos PDF" not in limites.mensagem_do_limite(20, "dia", pais)
        assert "extratos PDF" not in limites.mensagem_do_limite(30, "mes", pais)


def test_o_pt_continua_igual_ao_de_sempre():
    assert limites.mensagem_do_limite_pdf(15) == (
        "Chegaste ao limite de 15 extratos PDF este mês. O contador volta a zero no dia 1. "
        "Até lá, podes importar o extrato em CSV."
    )
    assert limites.mensagem_do_limite(30, "mes") == (
        "Chegaste ao limite deste mês. Já usaste os 30 pedidos à IA deste mês. O contador volta a zero no dia 1."
    )
    assert limites.FUNCOES_PAGAS["ler_talao"] == "A leitura de talões está disponível nos planos Essencial e Completo."
    assert main.MENSAGEM_SEM_CONFIRMACAO == 'Para apagar a conta, escreve "APAGAR" na confirmação.'


def _texto_br_do_frontend(ficheiro: str, chave: str) -> str:
    """O texto da chave no bloco BR de um textos*.ts (linha "chave: "...")."""
    conteudo = (FRONTEND / ficheiro).read_text(encoding="utf-8")
    bloco_br = conteudo.split("const BR")[1]
    return re.search(rf'\b{chave}: "([^"]+)"', bloco_br).group(1)


def test_textos_br_iguais_aos_do_frontend():
    assert msg("funcao_paga_importar_pdf", "BR") == _texto_br_do_frontend("textosPlanos.ts", "pdf")
    assert msg("funcao_paga_ler_talao", "BR") == _texto_br_do_frontend("textosPlanos.ts", "talao")
    assert msg("funcao_paga_precos_por_loja", "BR") == _texto_br_do_frontend("textosPrecosLojas.ts", "soPlanosPagos")
    limite = _texto_br_do_frontend("textosPlanos.ts", "textoMes").replace("{limite}", "30")
    assert msg("limite_pedidos_mes", "BR", limite=30) == f"Você chegou ao limite deste mês. {limite}"


# --- Limites (limites.py) ---


def test_429_dos_pedidos_em_br(monkeypatch, conta_br):
    monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: "free")
    monkeypatch.setattr(limites, "registar_pedido_atomico", lambda *args: False)

    with pytest.raises(HTTPException) as erro:
        limites.registar_pergunta("utilizador-teste", "chat")

    assert erro.value.status_code == 429
    assert erro.value.detail == msg("limite_pedidos_mes", "BR", limite=30)


@pytest.mark.parametrize(("resultado", "chave"), [("pdf", "limite_pdf"), ("pedidos", "limite_pedidos_dia")])
def test_429_do_pdf_em_br(monkeypatch, conta_br, resultado, chave):
    monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: "essencial")
    monkeypatch.setattr(limites, "_chamar_registar_pdf_ia", lambda parametros: resultado)

    with pytest.raises(HTTPException) as erro:
        limites.registar_pdf("utilizador-teste")

    assert erro.value.status_code == 429
    assert erro.value.detail == msg(chave, "BR", limite=15 if resultado == "pdf" else 20)


def test_402_em_br(monkeypatch, conta_br):
    monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: "essencial")

    with pytest.raises(HTTPException) as erro:
        limites.exigir_funcao("utilizador-teste", "resumo_anual_ia")

    assert (erro.value.status_code, erro.value.detail) == (402, msg("funcao_completo_resumo_anual_ia", "BR"))


def test_conta_cheia_e_aviso_do_resumo_em_br(monkeypatch, conta_br):
    monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: "essencial")

    with pytest.raises(HTTPException) as erro:
        limites.exigir_espaco_na_conta(limites.MAX_TRANSACOES_POR_CONTA, 1, "utilizador-teste")

    assert erro.value.detail == msg("conta_cheia", "BR")
    assert "20.000" in erro.value.detail
    assert limites.aviso_resumo_sem_pedidos("utilizador-teste") == msg("resumo_sem_pedidos_dia", "BR")


def test_conta_cheia_sem_user_id_fica_em_pt():
    with pytest.raises(HTTPException) as erro:
        limites.exigir_espaco_na_conta(limites.MAX_TRANSACOES_POR_CONTA, 1)

    assert erro.value.detail == msg("conta_cheia", "PT")


# --- Rotas (main.py) ---


def test_402_do_talao_em_br(cliente, limite, conta_br):
    limite.plano = "free"

    resposta = cliente.post("/compras/ler", files={"foto": ("nota.jpg", b"\xff\xd8\xff" + b"0" * 2000, "image/jpeg")})

    assert resposta.status_code == 402
    assert resposta.json() == {"detail": "A leitura de notas fiscais está disponível nos planos Essencial e Completo."}


def test_imagem_pequena_em_br(cliente, conta_br):
    resposta = cliente.post("/compras/ler", files={"foto": ("nota.jpg", b"\xff\xd8\xff", "image/jpeg")})

    assert resposta.status_code == 422
    assert resposta.json() == {"detail": "Imagem pequena demais. Tente outra foto."}


def test_404_do_produto_e_da_juncao_em_br(cliente, conta_br):
    chave = "x" * 101  # acima de 100 caracteres: 404 sem ler a base de dados

    assert cliente.get(f"/compras/produtos/{chave}").json() == {"detail": "Produto não encontrado nas suas compras."}
    assert cliente.delete(f"/compras/produtos/juntar/{chave}").json() == {"detail": "Esta junção não existe."}


def test_ano_invalido_em_br(cliente, conta_br):
    resposta = cliente.get("/relatorio?ano=1999")

    assert resposta.status_code == 422
    assert resposta.json()["detail"].startswith("Ano inválido. Escolha um ano entre 2000 e ")


def test_csv_grande_demais_em_br(cliente, conta_br):
    resposta = cliente.post("/transacoes/importar", files={"ficheiro": ("extrato.csv", b"a" * (1024 * 1024 + 1))})

    assert resposta.status_code == 422
    assert resposta.json() == {"detail": "CSV grande demais. Máx. 1 MB."}


def test_pdf_com_paginas_a_mais_em_br(cliente, conta_br, monkeypatch):
    monkeypatch.setattr(main, "contar_paginas_pdf", lambda pdf: 12)

    resposta = cliente.post("/transacoes/importar", files={"ficheiro": ("extrato.pdf", b"%PDF-1.4 inventado")})

    assert resposta.status_code == 400
    assert resposta.json() == {"detail": "Este PDF tem 12 páginas. O máximo é 10. Divida o extrato em partes menores."}


def test_apagar_conta_sem_confirmacao_em_br(cliente, conta_br):
    resposta = cliente.request("DELETE", "/conta", json={"confirmacao": "apagar"})

    assert resposta.status_code == 400
    assert resposta.json() == {"detail": 'Para apagar a conta, digite "APAGAR" na confirmação.'}


def test_mesma_rota_em_pt_por_omissao(cliente):
    resposta = cliente.post("/transacoes/importar", files={"ficheiro": ("extrato.csv", b"a" * (1024 * 1024 + 1))})

    assert resposta.json() == {"detail": "CSV demasiado grande. Máx. 1 MB."}


def test_juntar_produtos_iguais_em_br():
    with pytest.raises(HTTPException) as erro:
        produtos.juntar_produtos("utilizador-teste", "leite", "leite", "BR")

    assert erro.value.detail == "Escolha dois produtos diferentes para juntar."


# --- Resumo anual (relatorio.py) ---


LINHAS = [
    {"data": "2025-01-01", "descricao": "Salario Exemplo", "valor": 3000.0, "categoria": "rendimento"},
    {"data": "2025-01-05", "descricao": "Aluguel Exemplo", "valor": -1200.0, "categoria": "casa"},
    {"data": "2025-01-07", "descricao": "Saque Exemplo", "valor": -200.0, "categoria": "levantamentos"},
    {"data": "2025-01-09", "descricao": "Internet Exemplo", "valor": -100.0, "categoria": "telecomunicações"},
]


def test_relatorio_br_com_titulo_e_etiquetas_do_brasil():
    r = relatorio.montar_relatorio(2025, LINHAS, [], date(2026, 11, 10), "BR")

    assert r.titulo == "Resumo anual das suas finanças – 2025"
    assert "contador" in r.aviso and "e-fatura" not in r.aviso and "Imposto de Renda" not in r.aviso
    assert "e-fatura" not in r.nota_categorias
    etiquetas = {c.categoria: c.etiqueta for c in r.categorias}
    assert etiquetas == {"casa": "Moradia", "levantamentos": "Saques", "telecomunicações": "Telefone e internet"}
    # As chaves guardadas não mudam.
    assert {c.categoria for c in r.categorias} == {"casa", "levantamentos", "telecomunicações"}


def test_etiquetas_iguais_ao_frontend():
    opcoes = (FRONTEND / "opcoes.ts").read_text(encoding="utf-8").split("BR: {")[1].split("}")[0]
    for chave, rotulo in [("casa", "Moradia"), ("rendimento", "Receitas"), ("levantamentos", "Saques"),
                          ("telecomunicações", "Telefone e internet")]:  # fmt: skip
        assert relatorio.etiqueta(chave, "BR") == rotulo
        assert f'"{rotulo[0].lower() + rotulo[1:]}"' in opcoes


def test_relatorio_pt_continua_igual():
    r = relatorio.montar_relatorio(2025, LINHAS, [], date(2026, 11, 10))

    assert r.titulo == "Resumo anual das tuas finanças – 2025"
    assert r.aviso == relatorio.AVISO
    assert relatorio.etiqueta("rendimento") == "Entradas" and relatorio.etiqueta("casa") == "Casa"


def test_csv_br_com_reais_e_metas():
    r = relatorio.montar_relatorio(2025, LINHAS, [], date(2026, 11, 10), "BR")
    texto = relatorio.relatorio_em_csv(r, "BR", "BRL").decode("utf-8-sig")

    assert "Valor (R$)" in texto and "Saldo (R$)" in texto and "(€)" not in texto
    assert "Metas de economia (hoje)" in texto and "Objetivos de poupança" not in texto
    assert "Moradia;1200,00" in texto


def test_csv_pt_continua_com_euros():
    texto = relatorio.relatorio_em_csv(relatorio.montar_relatorio(2025, LINHAS, [], date(2026, 11, 10))).decode("utf-8-sig")

    assert "Valor (€)" in texto and "Objetivos de poupança (hoje)" in texto and "R$" not in texto


# --- A assinatura lê-se uma só vez por pedido ---


@pytest.fixture
def leituras(monkeypatch):
    lidas = []

    def ler(user_id):
        lidas.append(user_id)
        return Assinatura("essencial", date(2099, 12, 31), pais="BR", moeda="BRL", com_perfil=True)

    monkeypatch.setattr(limites, "_ler_assinatura", ler)
    return lidas


def test_fora_de_um_pedido_cada_chamada_le_a_base_de_dados(leituras):
    limites.assinatura_do_utilizador("u1")
    limites.assinatura_do_utilizador("u1")

    assert leituras == ["u1", "u1"]


def test_dentro_de_um_pedido_le_uma_vez_por_conta(leituras):
    token = limites.abrir_cache_do_pedido()
    try:
        limites.assinatura_do_utilizador("u1")
        limites.local_do_utilizador("u1")
        limites.plano_do_utilizador("u1")
        limites.assinatura_do_utilizador("u2")
        limites.esquecer_assinatura("u1")
        limites.assinatura_do_utilizador("u1")
    finally:
        limites.fechar_cache_do_pedido(token)

    assert leituras == ["u1", "u2", "u1"]


def test_o_middleware_partilha_a_leitura_entre_a_dependencia_e_a_rota(leituras):
    # Rotas e dependências síncronas correm noutras threads: a memória do pedido tem de chegar a todas.
    app = FastAPI()
    app.add_middleware(main.CacheDoPedido)

    def dependencia() -> str:
        limites.assinatura_do_utilizador("u1")
        return "u1"

    @app.get("/teste")
    def rota(user_id: str = Depends(dependencia)):
        return {"pais": limites.local_do_utilizador(user_id).pais, "plano": limites.plano_do_utilizador(user_id)}

    cliente = TestClient(app)
    assert cliente.get("/teste").json() == {"pais": "BR", "plano": "essencial"}
    assert cliente.get("/teste").status_code == 200

    assert leituras == ["u1", "u1"]  # uma por pedido


def test_local_do_utilizador_fica_pt_se_a_leitura_falhar(monkeypatch, capsys):
    def falhar(user_id):
        raise RuntimeError("base de dados em baixo")

    monkeypatch.setattr(limites, "_ler_assinatura", falhar)

    assert limites.local_do_utilizador("u1") == Local()
    assert "base de dados em baixo" not in capsys.readouterr().out


def test_local_do_utilizador_traz_o_pais_e_a_moeda(leituras):
    assert limites.local_do_utilizador("u1") == BR
