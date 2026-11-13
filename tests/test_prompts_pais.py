"""Prompts da IA por país (Fase 1 Brasil, passo 9). Sem IA verdadeira: um cliente falso guarda o que se enviaria.

Língua = país onde a pessoa vive (PT-PT "tu" / PT-BR "você"); moeda, formato e limiares = moeda da conta;
contexto bancário (categorizar e PDF) = país da moeda. Em PT os prompts ficam como estavam.
"""

import hashlib
from datetime import date
from types import SimpleNamespace
from typing import get_args

import pytest

import ferramentas
import ia
import main
from limites import CONFIG_IA_POR_PLANO
from mensagens import Local, msg
from models import CATEGORIAS_SO_HUMANAS, CategoriaIA, TransacaoCriar

PT = Local()
BR = Local(pais="BR", moeda="BRL")
PT_EM_REAIS = Local(pais="PT", moeda="BRL")  # vive em Portugal, controla a conta do Brasil
BR_EM_EUROS = Local(pais="BR", moeda="EUR")  # vive no Brasil, controla a conta de Portugal
FREE = CONFIG_IA_POR_PLANO["free"]

# Os prompts PT de uma conta PT/EUR. O único que mudou na Fase 1 Brasil foi a primeira linha
# ("app portuguesa" passou a "app"). Se mudares um prompt PT de propósito, atualiza aqui o hash.
HASHES_PT = {
    "INSTRUCOES": "0e69e6d89d2ed66259ea1f512f800ca3fb79efbf1670f5526cdf8532bc1ba5c0",
    "INSTRUCOES_CHAT": "bcd3c7c52154da0b0216f8572c89b01ed4ed95fb5330ed8f9c6f935036084986",
    "INSTRUCOES_RESUMO": "02d786b650644d80b8f09df75cbd109e54c219e513eb8740a7aa0514586dccb7",
    "INSTRUCOES_ORCAMENTO": "e0d908c5d69b5937caebad66600643c4c9718a984f7f92de9dfaea8b6fa8bb84",
    "INSTRUCOES_TALAO": "e41f3d8866845aee6be82d8ecb8d8990dc3104251fe0b0a0ae509bc88997f90a",
    "INSTRUCOES_EXTRATO_PDF": "1de2d3b6e7d7d28a5c6fa4d7c0910932ac9c5c48767ae158cbf02cf17f9f92e4",
    "INSTRUCOES_POUPANCA": "e6238f886583d5efc025188ddc87dc5c80d52befe99a4120589fe4a33912d24e",
    "INSTRUCOES_RESUMO_ANUAL": "fca8644d3a954f7b94b25bc0aaecd3e5c94a8075a3a9f66836ec998e7687e5c8",
}


class IAFalsa:
    """Imita anthropic.Anthropic() para todas as funções: guarda os argumentos e devolve uma resposta válida."""

    def __init__(self, parsed_output=None, texto="Resposta inventada"):
        self.chamadas: list[dict] = []
        self.parsed_output = parsed_output
        self.texto = texto
        self.messages = self

    def __call__(self):
        return self

    def _resposta(self):
        return SimpleNamespace(
            parsed_output=self.parsed_output,
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=self.texto)],
            usage=SimpleNamespace(input_tokens=10, output_tokens=10),
        )

    def create(self, **argumentos):
        self.chamadas.append(argumentos)
        return self._resposta()

    def parse(self, **argumentos):
        self.chamadas.append(argumentos)
        return self._resposta()

    def stream(self, **argumentos):
        self.chamadas.append(argumentos)
        resposta = self._resposta()

        class Fluxo:
            def __enter__(self):
                return SimpleNamespace(get_final_message=lambda: resposta)

            def __exit__(self, *erro):
                return False

        return Fluxo()


@pytest.fixture
def ia_falsa(monkeypatch):
    def _criar(parsed_output=None, texto="Resposta inventada"):
        falsa = IAFalsa(parsed_output, texto)
        monkeypatch.setattr(ia.anthropic, "Anthropic", falsa)
        monkeypatch.setattr(ia, "_registar_chamada", lambda *args, **opcoes: None)
        return falsa

    return _criar


def _prompts(local: Local) -> dict[str, str]:
    """O system de cada função para esta conta (o que iria para a IA)."""
    return {
        "categorizar": ia.instrucoes_de_categorizar(local),
        "chat": ia.instrucoes_do_chat(FREE, date(2026, 11, 9), local),
        "resumo": ia._instrucoes(ia.MODELOS_RESUMO, local.pais, local.moeda),
        "orcamento": ia._instrucoes(ia.MODELOS_ORCAMENTO, local.pais, local.moeda),
        "talao": ia._instrucoes(ia.MODELOS_TALAO, local.pais, local.moeda),
        "extrato_pdf": ia._instrucoes(ia.MODELOS_EXTRATO_PDF, ia._pais_da_moeda(local.moeda), local.moeda),
        "poupanca": ia._instrucoes(ia.MODELOS_POUPANCA, local.pais, local.moeda),
        "resumo_anual": ia._instrucoes(ia.MODELOS_RESUMO_ANUAL, local.pais, local.moeda),
    }


# --- PT inalterado ---


@pytest.mark.parametrize("nome", HASHES_PT)
def test_prompts_pt_iguais_aos_de_antes(nome):
    assert hashlib.sha256(getattr(ia, nome).encode()).hexdigest() == HASHES_PT[nome]


def test_uma_conta_pt_recebe_os_prompts_de_sempre():
    prompts = _prompts(PT)

    assert prompts["categorizar"] == ia.INSTRUCOES
    assert prompts["chat"] == f"{ia.INSTRUCOES_CHAT}\nHoje é 2026-11-09."
    assert prompts["resumo"] == ia.INSTRUCOES_RESUMO
    assert prompts["orcamento"] == ia.INSTRUCOES_ORCAMENTO
    assert prompts["talao"] == ia.INSTRUCOES_TALAO
    assert prompts["extrato_pdf"] == ia.INSTRUCOES_EXTRATO_PDF
    assert prompts["poupanca"] == ia.INSTRUCOES_POUPANCA
    assert prompts["resumo_anual"] == ia.INSTRUCOES_RESUMO_ANUAL
    # Sem local é o mesmo que PT/EUR.
    assert ia.instrucoes_do_chat(FREE, date(2026, 11, 9)) == prompts["chat"]


@pytest.mark.parametrize("local", [PT, BR, PT_EM_REAIS, BR_EM_EUROS])
def test_nenhum_prompt_diz_app_portuguesa(local):
    for nome, texto in _prompts(local).items():
        assert "app portuguesa" not in texto, nome
        assert "{" + "moeda}" not in texto and "{exemplo}" not in texto, nome  # nada por preencher


# --- BR: "você", R$, fuso e termos do Brasil ---


def test_prompts_br_tratam_por_voce_e_nunca_dizem_portuguesa():
    for nome, texto in _prompts(BR).items():
        assert "Você" in texto or "você" in texto, nome
        assert "portugues" not in texto.lower().replace("português do brasil", ""), nome
        assert "Portugal" not in texto, nome
        assert '"tu"' not in texto, nome


def test_prompts_br_com_reais():
    prompts = _prompts(BR)
    for nome in ("chat", "resumo", "orcamento", "poupanca", "resumo_anual"):
        assert "R$" in prompts[nome] and "€" not in prompts[nome], nome
    assert "Os valores estão em reais" in prompts["chat"]
    assert "R$ 1.234,56" in prompts["chat"]


def test_chat_br_com_o_fuso_e_as_palavras_do_brasil():
    texto = _prompts(BR)["chat"]

    assert texto.endswith("Hoje é 2026-11-09 (horário de Brasília).")
    assert "português do Brasil" in texto
    assert "levantamentos = saques" in texto and "casa = moradia" in texto and "rendimento = receitas" in texto
    assert "pedágio" in texto and "portagens" not in texto


def test_limiares_em_reais():
    br = _prompts(BR)
    assert "mais de 50% e mais de R$ 250 em relação ao mês anterior" in br["resumo"]
    assert "(múltiplos de R$ 10, ou de R$ 50 acima de R$ 500)" in br["orcamento"]
    assert "arredondado para reais inteiros" in br["poupanca"]
    pt = _prompts(PT)
    assert "mais de 50% e mais de 50 € em relação ao mês anterior" in pt["resumo"]
    assert "(múltiplos de 5 €, ou de 10 € acima de 100 €)" in pt["orcamento"]
    assert "arredondado a euros." in pt["poupanca"]


def test_a_moeda_e_a_lingua_sao_independentes():
    pt_em_reais, br_em_euros = _prompts(PT_EM_REAIS), _prompts(BR_EM_EUROS)

    # Vive em Portugal com conta em reais: língua PT ("tu"), valores em reais, bancos do Brasil.
    assert '"tu"' in pt_em_reais["chat"] and "Os valores são em reais" in pt_em_reais["chat"]
    assert "R$ 250" in pt_em_reais["resumo"]
    assert "bancos brasileiros" in pt_em_reais["categorizar"]
    # Vive no Brasil com conta em euros: "você", valores em euros, bancos de Portugal.
    assert '"você"' in br_em_euros["chat"] and "1.234,56 €" in br_em_euros["chat"]
    assert "50 €" in br_em_euros["resumo"]
    assert br_em_euros["categorizar"] == ia.INSTRUCOES
    assert br_em_euros["extrato_pdf"] == ia.INSTRUCOES_EXTRATO_PDF


def test_talao_br_e_nota_fiscal():
    texto = _prompts(BR)["talao"]

    assert "nota fiscal ou cupom fiscal" in texto
    assert "loja brasileira" in texto and "IVA" not in texto
    assert '"leite semidesnatado 1 l"' in texto


def test_categorizar_br_com_as_mesmas_categorias():
    texto = ia.instrucoes_de_categorizar(BR)

    assert "bancos brasileiros" in texto and "PIX" in texto and "SAQUE" in texto and "MB WAY" not in texto
    for categoria in get_args(CategoriaIA):
        assert f"- {categoria}" in texto, categoria
    # As categorias só humanas nunca entram na lista que a IA pode escolher.
    for categoria in CATEGORIAS_SO_HUMANAS:
        assert categoria not in texto
        assert categoria not in ia.instrucoes_de_categorizar(Local())


def test_resumo_anual_br_proibe_os_termos_fiscais_do_brasil():
    texto = _prompts(BR)["resumo_anual"]

    assert "Imposto de Renda" in texto and "IRPF" in texto and "Receita Federal" in texto
    assert ia.tem_palavra_proibida("Não precisa declarar no IRPF.", "BR")
    assert ia.tem_palavra_proibida("Pode ter restituições.", "BR")
    assert ia.tem_palavra_proibida("A Receita Federal...", "BR")
    assert not ia.tem_palavra_proibida("As suas receitas subiram e a moradia ficou igual.", "BR")
    # No PT a verificação é a de sempre.
    assert not ia.tem_palavra_proibida("Não precisa declarar no IRPF.")


# --- As funções enviam o prompt do país (com a IA falsa) ---


def test_resumir_mes_br(ia_falsa):
    falsa = ia_falsa(parsed_output=SimpleNamespace(resumo="ok", alertas=[]))

    ia.resumir_mes({"mes": "2026-10"}, local=BR)

    assert falsa.chamadas[0]["system"] == _prompts(BR)["resumo"]


def test_categorizar_br_e_pdf_br(ia_falsa):
    falsa = ia_falsa(parsed_output=SimpleNamespace(categorizacoes=[], movimentos=[]))

    ia.categorizar([TransacaoCriar(data=date(2026, 10, 1), descricao="PIX MERCADO EXEMPLO", valor=-10.0)], local=BR)
    ia.ler_extrato_pdf(b"%PDF-1.4 inventado", local=BR)

    assert "bancos brasileiros" in falsa.chamadas[0]["system"]
    assert falsa.chamadas[1]["system"] == ia.INSTRUCOES_EXTRATO_PDF_BR
    assert falsa.chamadas[1]["messages"][0]["content"][1]["text"] == "Leia este extrato."


def test_ler_talao_br(ia_falsa):
    falsa = ia_falsa(parsed_output=SimpleNamespace(itens=[]))

    ia.ler_talao(b"\xff\xd8\xff" + b"0" * 2000, "image/jpeg", local=BR)

    assert falsa.chamadas[0]["system"] == ia.INSTRUCOES_TALAO_BR
    assert falsa.chamadas[0]["messages"][0]["content"][1]["text"] == "Leia esta nota fiscal."


def test_sugestao_poupanca_e_resumo_anual_br(ia_falsa):
    falsa = ia_falsa(parsed_output=SimpleNamespace(resumo="Resumo inventado.", sugestoes=[]))

    ia.sugerir_orcamento({}, local=BR)
    ia.planear_poupanca({}, local=BR)
    ia.resumir_ano({}, local=BR)

    assert [c["system"] for c in falsa.chamadas] == [_prompts(BR)[n] for n in ("orcamento", "poupanca", "resumo_anual")]


def test_chat_br_envia_o_prompt_br_e_a_resposta_sem_orcamento_em_br(ia_falsa):
    falsa = ia_falsa(texto="")  # sem texto: o chat devolve a mensagem de "reformular"

    resposta = ia.conversar("Quanto gastei?", [], lambda nome, argumentos: "{}", config=FREE, local=BR)

    assert "português do Brasil" in falsa.chamadas[0]["system"]
    assert resposta == msg("chat_sem_orcamento", "BR")


# --- Ferramentas do chat ---


def test_ferramentas_pt_sao_as_de_sempre():
    assert ferramentas.ferramentas_para(PT) is ferramentas.FERRAMENTAS
    assert ferramentas.ferramentas_para() is ferramentas.FERRAMENTAS


def test_ferramentas_br_em_reais_sem_mudar_a_lista_original():
    antes = repr(ferramentas.FERRAMENTAS)
    br = ferramentas.ferramentas_para(BR)

    assert "em reais" in repr(br) and "em euros" not in repr(br)
    assert "pedágio" in repr(br) and "portagens" not in repr(br)
    assert [f["name"] for f in br] == [f["name"] for f in ferramentas.FERRAMENTAS]
    assert repr(ferramentas.FERRAMENTAS) == antes
    # Só a moeda muda as descrições dos valores; só o país muda os exemplos de termos.
    assert "em euros" in repr(ferramentas.ferramentas_para(BR_EM_EUROS))
    assert "portagens" in repr(ferramentas.ferramentas_para(PT_EM_REAIS))


# --- As rotas passam o país e a moeda da conta ---


def test_rota_do_chat_passa_o_local_e_as_ferramentas_da_conta(cliente, monkeypatch):
    monkeypatch.setattr(main, "local_do_utilizador", lambda user_id: BR)
    monkeypatch.setattr(main, "plano_e_config_ia", lambda user_id: ("free", FREE))
    recebido = {}

    def conversar(pergunta, ferramentas_da_conta, executar, **opcoes):
        recebido.update(opcoes, ferramentas=ferramentas_da_conta)
        return "Resposta inventada"

    monkeypatch.setattr(main, "conversar", conversar)

    assert cliente.post("/chat", json={"pergunta": "Quanto gastei?"}).status_code == 200
    assert recebido["local"] == BR
    assert "em reais" in repr(recebido["ferramentas"])


def test_rota_de_importar_csv_passa_o_local(cliente, monkeypatch):
    monkeypatch.setattr(main, "local_do_utilizador", lambda user_id: BR)
    recebido = []
    monkeypatch.setattr(main, "categorizar", lambda novas, user_id=None, local=None: recebido.append(local) or ["outros"] * len(novas))
    csv = "Data;Descrição;Montante;Saldo\n01-10-2026;PIX MERCADO EXEMPLO;-10,00;100,00\n".encode()

    resposta = cliente.post("/transacoes/importar", files={"ficheiro": ("extrato.csv", csv)})

    assert resposta.status_code == 201
    assert recebido == [BR]
