"""Ferramentas que a IA pode pedir no chat.

A IA escolhe a ferramenta e os parâmetros (por exemplo, o mês). O user_id vem
sempre do token e é este código que o junta: a IA nunca o vê nem o escolhe.
O plano também vem do servidor: é ele que diz até que mês as ferramentas podem ver
(meses_historico em limites.py).
"""

import json
import re

from consultas import gastos_de_varios_meses, gastos_do_mes
from ia import PedidoInvalido
from limites import config_ia_do_plano, hoje_em_lisboa, primeiro_mes_visivel
from objetivos import listar_objetivos
from orcamento import planeamento_do_mes

# Meses máximos que gastos_de_varios_meses devolve numa chamada: um ano. Mais do que isso
# enchia o prompt (e o custo) sem ajudar a responder; a IA pode pedir outro intervalo.
MAX_MESES_POR_CHAMADA = 12

NOMES_DOS_PLANOS = {"free": "Free", "essencial": "Essencial", "completo": "Completo"}

_PROPRIEDADE_MES = {"type": "string", "description": "Mês no formato AAAA-MM, por exemplo 2026-10."}

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
            "properties": {"mes": _PROPRIEDADE_MES},
            "required": ["mes"],
            "additionalProperties": False,
        },
    },
    {
        "name": "gastos_de_varios_meses",
        "description": (
            "Devolve os gastos por categoria, em euros, de cada mês entre mes_inicio e mes_fim "
            f"(os dois incluídos, no máximo {MAX_MESES_POR_CHAMADA} meses por chamada). "
            "Usa para comparar meses, ver a evolução de uma categoria ou somar vários meses."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"mes_inicio": _PROPRIEDADE_MES, "mes_fim": _PROPRIEDADE_MES},
            "required": ["mes_inicio", "mes_fim"],
            "additionalProperties": False,
        },
    },
    {
        "name": "orcamentos_do_mes",
        "description": (
            "Devolve o orçamento mensal (limite) de cada categoria e quanto já se gastou nesse mês, em euros. "
            "limite vem vazio nas categorias com gastos mas sem orçamento. Usa para perguntas sobre "
            "orçamentos, sobre quanto falta gastar ou sobre categorias que passaram o limite."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"mes": _PROPRIEDADE_MES},
            "required": ["mes"],
            "additionalProperties": False,
        },
    },
    {
        "name": "objetivos_de_poupanca",
        "description": (
            "Devolve os objetivos de poupança do utilizador: nome, valor alvo, valor já poupado e data alvo, "
            "do prazo mais próximo para o mais distante. Usa para perguntas sobre objetivos e poupança."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

_FORMATO_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _validar_mes(mes: object) -> str:
    """O mês, se estiver no formato AAAA-MM. Senão, um erro que volta para a IA corrigir o pedido."""
    if not isinstance(mes, str) or not _FORMATO_MES.match(mes):
        raise PedidoInvalido(f"mês inválido: {mes!r}. Usa o formato AAAA-MM, por exemplo 2026-10.")
    return mes


def meses_entre(primeiro: str, ultimo: str) -> list[str]:
    """Todos os meses de primeiro a ultimo, os dois incluídos: ("2026-11", "2027-01") -> 3 meses."""
    inicio = int(primeiro[:4]) * 12 + int(primeiro[5:]) - 1
    fim = int(ultimo[:4]) * 12 + int(ultimo[5:]) - 1
    return [f"{absoluto // 12:04d}-{absoluto % 12 + 1:02d}" for absoluto in range(inicio, fim + 1)]


def _fora_do_historico(plano: str | None, primeiro: str) -> dict:
    """A resposta para meses que o plano não vê. A IA usa-a para explicar e sugerir mudar de plano."""
    nome = NOMES_DOS_PLANOS.get(plano or "", "Free")
    return {
        "fora_do_historico": True,
        "mensagem": (
            f"O plano {nome} do utilizador só mostra dados desde {primeiro}. "
            "Para ver meses mais antigos, pode mudar para um plano com mais histórico."
        ),
    }


def _gastos_por_categoria(user_id: str, mes: str) -> list[dict]:
    return [gasto.model_dump() for gasto in gastos_do_mes(user_id, mes)]


def _gastos_de_varios_meses(user_id: str, plano: str | None, primeiro: str | None, inicio: str, fim: str) -> dict:
    if inicio > fim:
        raise PedidoInvalido("mes_inicio tem de ser igual ou anterior a mes_fim.")
    if primeiro and fim < primeiro:
        return _fora_do_historico(plano, primeiro)
    resultado: dict = {}
    # Um intervalo que começa antes do que o plano vê é cortado, com um aviso para a IA explicar.
    if primeiro and inicio < primeiro:
        inicio = primeiro
        resultado["aviso"] = _fora_do_historico(plano, primeiro)["mensagem"]
    meses = meses_entre(inicio, fim)
    if len(meses) > MAX_MESES_POR_CHAMADA:
        raise PedidoInvalido(f"no máximo {MAX_MESES_POR_CHAMADA} meses por chamada; pede um intervalo mais curto.")
    gastos = gastos_de_varios_meses(user_id, meses)
    resultado["meses"] = {mes: [gasto.model_dump() for gasto in lista] for mes, lista in gastos.items()}
    return resultado


def executar_ferramenta(nome: str, argumentos: dict, user_id: str, plano: str | None) -> str:
    """Corre a ferramenta pedida pela IA e devolve o resultado como texto JSON.

    user_id vem sempre do token e plano do servidor (nunca da IA nem do browser).
    """
    primeiro = primeiro_mes_visivel(config_ia_do_plano(plano), hoje_em_lisboa())

    if nome == "gastos_por_categoria":
        mes = _validar_mes(argumentos.get("mes"))
        resultado = _fora_do_historico(plano, primeiro) if primeiro and mes < primeiro else _gastos_por_categoria(user_id, mes)
    elif nome == "gastos_de_varios_meses":
        inicio = _validar_mes(argumentos.get("mes_inicio"))
        fim = _validar_mes(argumentos.get("mes_fim"))
        resultado = _gastos_de_varios_meses(user_id, plano, primeiro, inicio, fim)
    elif nome == "orcamentos_do_mes":
        mes = _validar_mes(argumentos.get("mes"))
        if primeiro and mes < primeiro:
            resultado = _fora_do_historico(plano, primeiro)
        else:
            resultado = [linha.model_dump() for linha in planeamento_do_mes(user_id, mes)]
    elif nome == "objetivos_de_poupanca":
        resultado = [objetivo.model_dump(mode="json") for objetivo in listar_objetivos(user_id)]
    else:
        raise PedidoInvalido(f"Ferramenta desconhecida: {nome}")
    return json.dumps(resultado, ensure_ascii=False)
