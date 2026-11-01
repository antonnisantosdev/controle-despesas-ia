"""Categorização de transações com IA.

O resto da API só chama categorizar(); qual o fornecedor usado (Claude, Gemini...)
decide-se no .env com IA_FORNECEDOR, sem mudar mais nenhum ficheiro.
"""

import os
from typing import Literal

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

from models import TransacaoCriar

load_dotenv()

# As únicas categorias que a IA pode escolher. Com Literal, a resposta é validada:
# se a IA inventar outra palavra, o Pydantic rejeita-a.
Categoria = Literal[
    "alimentação",
    "restaurantes",
    "transporte",
    "casa",
    "saúde",
    "lazer",
    "compras",
    "telecomunicações",
    "rendimento",
    "transferências",
    "levantamentos",
    "outros",
]


# Formato obrigatório da resposta da IA (saída estruturada).
class Categorizacao(BaseModel):
    indice: int
    categoria: Categoria


class RespostaCategorizacao(BaseModel):
    categorizacoes: list[Categorizacao]


INSTRUCOES = """
És um assistente que categoriza transações de extratos de bancos portugueses.
Recebes uma lista de transações, uma por linha, no formato "índice: descrição (valor)".
Para cada transação, escolhe uma categoria da lista permitida.

O sinal do valor:
- Se for negativo, é uma despesa (ex.: -52.37).
- Se for positivo, é um rendimento (ex.: 1200.00).

Abreviaturas comuns nas descrições:
- "MB WAY" = pagamento por MB Way
- "ATM" = levantamento de dinheiro num multibanco
Lista de categorias permitidas:
- alimentação
- restaurantes
- transporte
- casa
- saúde
- lazer
- compras
- telecomunicações
- rendimento
- transferências
- levantamentos
- outros (para despesas que não se encaixam em nenhuma das categorias acima)

Regras para casos ambíguos:
- Se a transação for um pagamento a um supermercado, categoria = alimentação.
- Se a transação for um pagamento a um restaurante, categoria = restaurantes.
- Se a transação for um pagamento a uma farmácia, categoria = saúde.
Responde apenas com JSON, no formato:
{
  "categorizacoes": [
    {"indice": 0, "categoria": "alimentação"},
    {"indice": 1, "categoria": "restaurantes"},
    ...
  ]
}
"""


def categorizar(transacoes: list[TransacaoCriar]) -> list[str]:
    """Devolve uma categoria para cada transação, pela mesma ordem."""
    fornecedor = os.getenv("IA_FORNECEDOR", "claude")
    if fornecedor == "claude":
        return _categorizar_claude(transacoes)
    raise RuntimeError(f"Fornecedor de IA desconhecido: {fornecedor}")


def _categorizar_claude(transacoes: list[TransacaoCriar]) -> list[str]:
    cliente = anthropic.Anthropic()

    # Uma linha por transação, com um número para a IA dizer a qual se refere.
    # Exemplo: "0: COMPRA SUPERMERCADO PINGO AZUL (-52.37)"
    lista = "\n".join(f"{i}: {t.descricao} ({t.valor})" for i, t in enumerate(transacoes))

    resposta = cliente.messages.parse(
        model=os.getenv("CLAUDE_MODELO", "claude-haiku-5-5"),
        max_tokens=4096,
        system=INSTRUCOES,
        messages=[{"role": "user", "content": lista}],
        output_format=RespostaCategorizacao,
    )
    if resposta.parsed_output is None:
        raise RuntimeError(f"A IA não devolveu uma resposta válida (stop_reason={resposta.stop_reason})")

    # Organiza por índice; se a IA saltar alguma transação, fica "outros".
    por_indice = {c.indice: c.categoria for c in resposta.parsed_output.categorizacoes}
    return [por_indice.get(i, "outros") for i in range(len(transacoes))]
