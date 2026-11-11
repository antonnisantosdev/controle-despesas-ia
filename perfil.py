"""Perfil da conta (sql/020): país onde a pessoa vive, países dos cartões e contas, e moeda principal.

- pais: língua, fuso e formatos. Muda-se livremente.
- paises_bancos: 1 ou 2 países (PT, BR). Mudam-se livremente, desde que a moeda continue a ser de um deles.
- moeda: Fase 1, uma moeda por conta (EUR ou BRL). Só muda com a conta sem dados (função
  atualizar_perfil_conta da sql/020, atómica). Bancos só PT: EUR; só BR: BRL; os dois: a escolhida.

As regras puras (sem base de dados) ficam no início: o models.py usa-as para validar o registo.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from postgrest.exceptions import APIError

from database import supabase
from limites import COLUNA_NAO_EXISTE, FUNCAO_NAO_EXISTE, MOEDA_DO_PAIS, assinatura_do_utilizador

# Textos das respostas do PUT /conta/perfil (novos, PT-PT; o passo 8 do plano Brasil trata as versões BR).
MENSAGEM_MOEDA_COM_DADOS = (
    "Só podes mudar a moeda principal enquanto a conta não tiver movimentações, compras, orçamentos nem objetivos."
)
MENSAGEM_MOEDA_INCOERENTE = "A moeda principal tem de ser a de um dos países dos teus cartões e contas."
MENSAGEM_PERFIL_INDISPONIVEL = "Não foi possível guardar as definições agora. Tenta mais tarde."


@dataclass(frozen=True)
class Perfil:
    pais: str
    paises_bancos: tuple[str, ...]
    moeda: str


class PerfilInvalido(ValueError):
    """A moeda não é a de nenhum dos países das contas. ValueError: no Pydantic dá 422."""


def moedas_possiveis(paises_bancos: tuple[str, ...] | list[str]) -> set[str]:
    """As moedas que a conta pode ter com estes países das contas (EUR com PT, BRL com BR)."""
    return {MOEDA_DO_PAIS[pais] for pais in paises_bancos}


def resolver_moeda(paises_bancos: tuple[str, ...] | list[str], pedida: str | None, preferida: str) -> str:
    """A moeda principal: a pedida (se for possível), senão a preferida (se for possível), senão a do 1.º país.

    Com um só país há uma só moeda possível. PerfilInvalido se a pedida não for de nenhum dos países.
    """
    possiveis = moedas_possiveis(paises_bancos)
    if pedida is not None:
        if pedida not in possiveis:
            raise PerfilInvalido(MENSAGEM_MOEDA_INCOERENTE)
        return pedida
    if preferida in possiveis:
        return preferida
    return MOEDA_DO_PAIS[paises_bancos[0]]


def perfil_inicial(pais: str | None, paises_bancos: list[str] | None, moeda: str | None) -> Perfil | None:
    """O perfil a gravar no registo, ou None se não veio nenhum campo (fica o DEFAULT da base de dados).

    Sem país: PT. Sem países das contas: o país onde vive. Sem moeda com dois países: a do país onde vive.
    """
    if pais is None and paises_bancos is None and moeda is None:
        return None
    pais = pais or "PT"
    bancos = tuple(paises_bancos or [pais])
    return Perfil(pais, bancos, resolver_moeda(bancos, moeda, MOEDA_DO_PAIS[pais]))


def perfil_atualizado(atual: Perfil, pais: str | None, paises_bancos: list[str] | None, moeda: str | None) -> Perfil:
    """O perfil depois do PUT /conta/perfil: o que vier muda, o resto fica.

    Sem moeda no pedido, fica a atual, se ainda for de um dos países das contas; senão passa à do país que
    ficou (ex.: tirar PT dos bancos de uma conta em EUR pede BRL, e isso só passa com a conta sem dados).
    """
    novo_pais = pais or atual.pais
    bancos = tuple(paises_bancos) if paises_bancos is not None else atual.paises_bancos
    return Perfil(novo_pais, bancos, resolver_moeda(bancos, moeda, atual.moeda))


# --- Base de dados ---


def _chamar_atualizar_perfil(user_id: str, perfil: Perfil, so_se_padrao: bool) -> str | None:
    """Chama a função atualizar_perfil_conta (sql/020). None se ainda não existir no Supabase.

    so_se_padrao: só muda uma conta ainda no perfil padrão (PT / {PT} / EUR) e sem dados; senão a função
    devolve 'nao_padrao' sem mudar nada. True no registo e no 1.º login com o Google; False nas definições.
    """
    try:
        resposta = supabase.rpc(
            "atualizar_perfil_conta",
            {
                "p_user_id": user_id,
                "p_pais": perfil.pais,
                "p_paises_bancos": list(perfil.paises_bancos),
                "p_moeda": perfil.moeda,
                "p_so_se_padrao": so_se_padrao,
            },
        ).execute()
    except APIError as erro:
        if erro.code in FUNCAO_NAO_EXISTE or erro.code in COLUNA_NAO_EXISTE:
            return None
        raise
    # A função devolve texto ('ok', 'tem_dados', 'nao_padrao' ou 'sem_conta'). Qualquer outra coisa conta como falha.
    return resposta.data if isinstance(resposta.data, str) else ""


def guardar_perfil_inicial(user_id: str | None, perfil: Perfil | None) -> None:
    """Grava o perfil escolhido no registo (ou no 1.º login com o Google). Só para contas acabadas de criar
    (quem chama garante-o, como na origem). Nunca falha: um erro só deixa um aviso no log (sem o id nem o email),
    e a conta fica com o perfil de sempre (PT, EUR), que se muda depois nas definições.

    Segunda barreira: a base de dados só muda a conta se ainda tiver o perfil padrão e não tiver dados
    (p_so_se_padrao). Um registo repetido ou um login tardio nunca desfaz o que a pessoa escolheu depois.
    """
    if not user_id or perfil is None:
        return
    try:
        resultado = _chamar_atualizar_perfil(user_id, perfil, so_se_padrao=True)
    except Exception as erro:
        print(f"AVISO: perfil do registo não gravado ({type(erro).__name__}).")
        return
    if resultado is None:
        print("AVISO: função atualizar_perfil_conta não encontrada (sql/020); perfil do registo não gravado.")
    elif resultado == "nao_padrao":
        print("AVISO: perfil do registo não gravado (a conta já não tinha o perfil padrão ou já tinha dados).")
    elif resultado != "ok":
        print(f"AVISO: perfil do registo não gravado ({resultado or 'resposta inesperada'}).")


def atualizar_perfil(user_id: str, pais: str | None, paises_bancos: list[str] | None, moeda: str | None) -> Perfil:
    """Muda o perfil da conta (PUT /conta/perfil) e devolve-o como ficou.

    422 se a moeda não for de um dos países das contas; 409 se a moeda mudar e a conta já tiver dados;
    503 se a sql/020 ainda não foi corrida ou a base de dados responder algo inesperado.
    """
    try:
        conta = assinatura_do_utilizador(user_id)
    except APIError as erro:
        # Base de dados recusou ou falhou (permissão, timeout...): 503, e no log só o código.
        print(f"AVISO: PUT /conta/perfil não leu a assinatura ({erro.code}).")
        raise HTTPException(status_code=503, detail=MENSAGEM_PERFIL_INDISPONIVEL)
    if not conta.com_perfil:
        print("AVISO: PUT /conta/perfil antes da sql/020.")
        raise HTTPException(status_code=503, detail=MENSAGEM_PERFIL_INDISPONIVEL)
    atual = Perfil(conta.pais, conta.paises_bancos, conta.moeda)
    try:
        novo = perfil_atualizado(atual, pais, paises_bancos, moeda)
    except PerfilInvalido as erro:
        raise HTTPException(status_code=422, detail=str(erro))

    try:
        resultado = _chamar_atualizar_perfil(user_id, novo, so_se_padrao=False)
    except APIError as erro:
        # Ex.: CHECK violado (23514), permissão (42501), bloqueio. Nunca 500 sem CORS.
        print(f"AVISO: atualizar_perfil_conta falhou ({erro.code}).")
        raise HTTPException(status_code=503, detail=MENSAGEM_PERFIL_INDISPONIVEL)
    if resultado == "ok":
        return novo
    if resultado == "tem_dados":
        raise HTTPException(status_code=409, detail=MENSAGEM_MOEDA_COM_DADOS)
    if resultado is None:
        print("AVISO: função atualizar_perfil_conta não encontrada (sql/020).")
    else:
        print(f"AVISO: atualizar_perfil_conta devolveu uma resposta inesperada: {resultado!r}")
    raise HTTPException(status_code=503, detail=MENSAGEM_PERFIL_INDISPONIVEL)
