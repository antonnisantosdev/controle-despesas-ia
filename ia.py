"""Funções de IA: categorização de transações e chat sobre as finanças.

O resto da API só chama categorizar() e conversar(); qual o fornecedor usado (por agora,
o Claude) decide-se no .env com IA_FORNECEDOR, sem mudar mais nenhum ficheiro.
"""

import os
from collections.abc import Callable
from datetime import date

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

from models import Categoria, TransacaoCriar

load_dotenv()


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


class ErroIA(Exception):
    """A IA falhou (sem ligação, chave errada, sem créditos, resposta inválida...).

    O resto da API só conhece este erro, nunca os erros de cada fornecedor.
    """


def categorizar(transacoes: list[TransacaoCriar]) -> list[str]:
    """Devolve uma categoria para cada transação, pela mesma ordem."""
    fornecedor = os.getenv("IA_FORNECEDOR", "claude")
    if fornecedor == "claude":
        try:
            return _categorizar_claude(transacoes)
        except anthropic.APIError as erro:
            raise ErroIA(f"Claude: {erro}") from erro
    raise RuntimeError(f"Fornecedor de IA desconhecido: {fornecedor}")


def _categorizar_claude(transacoes: list[TransacaoCriar]) -> list[str]:
    cliente = anthropic.Anthropic()

    lista = "\n".join(f"{i}: {t.descricao} ({t.valor})" for i, t in enumerate(transacoes))

    resposta = cliente.messages.parse(
        model=os.getenv("CLAUDE_MODELO", "claude-haiku-5-5"),
        max_tokens=4096,
        system=INSTRUCOES,
        messages=[{"role": "user", "content": lista}],
        output_format=RespostaCategorizacao,
    )
    if resposta.parsed_output is None:
        raise ErroIA(f"A IA não devolveu uma resposta válida (stop_reason={resposta.stop_reason})")
    por_indice = {c.indice: c.categoria for c in resposta.parsed_output.categorizacoes}
    return [por_indice.get(i, "outros") for i in range(len(transacoes))]

INSTRUCOES_CHAT = """
És o assistente de uma app portuguesa de controlo de despesas pessoais.
Respondes a perguntas do utilizador sobre as finanças dele, em português de Portugal, de forma curta e direta.

Regras:
- Usa sempre as ferramentas para obter números. Nunca inventes nem estimes valores.
- Os valores são em euros. Escreve-os no formato português, por exemplo 1.234,56 €.
- Se nenhuma ferramenta permitir responder, diz que ainda não consegues responder a essa pergunta.
- Se a ferramenta não devolver dados para esse período, diz que não há registos.
"""

# Limite de voltas do ciclo: protege contra uma IA que peça ferramentas sem parar (e contra custos).
MAX_VOLTAS = 5


def conversar(pergunta: str, ferramentas: list[dict], executar: Callable[[str, dict], str]) -> str:
    """Responde a uma pergunta, deixando a IA pedir ferramentas.

    `executar(nome, argumentos)` corre a ferramenta pedida e devolve o resultado em texto.
    Quem chama já ligou essa função ao utilizador certo: a IA nunca vê o user_id.
    """
    fornecedor = os.getenv("IA_FORNECEDOR", "claude")
    if fornecedor == "claude":
        try:
            return _conversar_claude(pergunta, ferramentas, executar)
        except anthropic.APIError as erro:
            raise ErroIA(f"Claude: {erro}") from erro
    raise RuntimeError(f"Fornecedor de IA desconhecido: {fornecedor}")


def _conversar_claude(pergunta: str, ferramentas: list[dict], executar: Callable[[str, dict], str]) -> str:
    cliente = anthropic.Anthropic()
    instrucoes = f"{INSTRUCOES_CHAT}\nHoje é {date.today().isoformat()}."
    mensagens = [{"role": "user", "content": pergunta}]

    for _ in range(MAX_VOLTAS):
        resposta = cliente.messages.create(
            model=os.getenv("CLAUDE_MODELO", "claude-haiku-5-5"),
            max_tokens=2048,
            system=instrucoes,
            tools=ferramentas,
            messages=mensagens,
        )

        # Sem pedidos de ferramentas: é a resposta final. Junta os blocos de texto.
        if resposta.stop_reason != "tool_use":
            return "".join(bloco.text for bloco in resposta.content if bloco.type == "text")

        # A resposta da IA (com os pedidos de ferramentas) entra no histórico da conversa.
        mensagens.append({"role": "assistant", "content": resposta.content})

        # A IA pode pedir várias ferramentas de uma vez: corre cada uma e junta os resultados.
        resultados = []
        for bloco in resposta.content:
            if bloco.type != "tool_use":
                continue
            try:
                texto = executar(bloco.name, bloco.input)
                resultados.append({"type": "tool_result", "tool_use_id": bloco.id, "content": texto})
            except Exception as erro:
                # O erro volta para a IA, que costuma corrigir o pedido na volta seguinte.
                resultados.append(
                    {"type": "tool_result", "tool_use_id": bloco.id, "content": f"Erro: {erro}", "is_error": True}
                )

        # Os resultados das ferramentas entram no histórico como mensagem do utilizador.
        mensagens.append({"role": "user", "content": resultados})

    raise ErroIA(f"A IA pediu ferramentas mais de {MAX_VOLTAS} vezes sem responder")
