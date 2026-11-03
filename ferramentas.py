"""Ferramentas que a IA pode pedir no chat.

A IA escolhe a ferramenta e os parâmetros (por exemplo, o mês). O user_id vem
sempre do token e é este código que o junta: a IA nunca o vê nem o escolhe.
"""

import json

from consultas import gastos_do_mes

# A lista que a IA recebe: o nome, para que serve (a IA decide com base nisto)
# e os parâmetros que aceita, descritos em JSON Schema.
FERRAMENTAS = [
    {
        "name": "gastos_por_categoria",
        "description": (
            "Devolve quanto o utilizador gastou em cada categoria num mês, em euros, "
            "do maior gasto para o menor. Usa para perguntas sobre gastos de um mês "
            "ou de uma categoria num mês."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mes": {"type": "string", "description": "Mês no formato AAAA-MM, por exemplo 2026-10."},
            },
            "required": ["mes"],
            "additionalProperties": False,
        },
    },
]


def _gastos_por_categoria(user_id: str, mes: str) -> list[dict]:
    return [gasto.model_dump() for gasto in gastos_do_mes(user_id, mes)]


def executar_ferramenta(nome: str, argumentos: dict, user_id: str) -> str:
    """Corre a ferramenta pedida pela IA e devolve o resultado como texto JSON."""
    if nome == "gastos_por_categoria":
        resultado = _gastos_por_categoria(user_id, argumentos["mes"])
    else:
        raise ValueError(f"Ferramenta desconhecida: {nome}")
    return json.dumps(resultado, ensure_ascii=False)
