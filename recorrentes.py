"""Pagamentos que se repetem todos os meses (assinaturas, ginásio, renda, telemóvel...), sem IA.

Só contas sobre as despesas: não gasta pedidos à IA e funciona em todos os planos.

Regras para um pagamento contar como recorrente:
- é uma despesa (valor negativo), fora das categorias transferências e levantamentos;
- a descrição, depois de normalizada, é a mesma (tiram-se números, datas, referências e acentos,
  que mudam de mês para mês: "COMPRA 4312 NETFLIX.COM 05/10" e "COMPRA 4312 NETFLIX.COM 05/11" são iguais),
  e não é genérica ("MB WAY 912345678" fica só "mb way": podia ser qualquer pessoa);
- aparece em pelo menos MESES_MINIMOS meses de calendário seguidos;
- em cada mês conta um só pagamento: dois ou mais com valores parecidos (±10% entre si, ex.: uma cobrança
  repetida) contam como um, o mais recente; com valores diferentes, o mês parte a sequência;
- cada mês fica a ±10% do mês anterior da sequência, com UMA exceção: uma mudança de preço
  (ex.: a assinatura subiu), desde que o novo preço depois se mantenha;
- continua ativo: o último desses meses é o mês atual ou o anterior (uma assinatura cancelada há meses não aparece).
"""

import re
import threading
import time
import unicodedata
from datetime import date

from database import ler_todas, supabase
from models import Recorrente

MESES_MINIMOS = 3
TOLERANCIA_VALOR = 0.10
# Meses para trás que se leem (além do atual): chega para ver um ano de assinaturas.
MESES_A_LER = 12
# Uma descrição que, sem as palavras genéricas, tem menos letras do que isto não diz nada.
LETRAS_MINIMAS = 3
# Categorias que não são pagamentos de um serviço: mexer dinheiro entre contas e levantar dinheiro.
# Os nomes são os de Categoria (models.py).
CATEGORIAS_EXCLUIDAS = {"transferências", "levantamentos"}
# Palavras que aparecem em muitas descrições sem dizer a quem se pagou (já normalizadas, sem acentos).
# "MB WAY P/ JOAO" fica "joao" (conta); "MB WAY 912345678" fica vazio (não conta).
PALAVRAS_GENERICAS = {
    "mb", "way", "mbway", "multibanco", "atm", "levantamento", "levant", "transferencia", "transf", "trf",
    "sepa", "pagamento", "pag", "compra", "cartao", "debito", "deb", "dd", "ref", "p", "para", "de", "a",
    # Brasil: "PIX ENVIADO MARIA" fica "maria"; "PAG BOLETO SABESP" fica "sabesp".
    "pix", "enviado", "recebido", "boleto", "ted", "doc", "tef", "saque",
}  # fmt: skip

# Quanto tempo (segundos) se guarda a resposta de cada utilizador. Ler um ano de despesas é a consulta
# mais pesada da rota; o dashboard e o Planeamento pedem-na sempre que abrem.
CACHE_SEGUNDOS = 5 * 60
# Por utilizador: (quando se calculou, o "hoje" usado, a lista). Vive na memória do servidor
# (perde-se quando o Render reinicia, e não se partilha entre servidores: não faz mal, é só uma cache).
_CACHE: dict[str, tuple[float, date, list[Recorrente]]] = {}
# O FastAPI corre as rotas em várias threads: o cadeado impede duas de mexerem na cache ao mesmo tempo.
_CADEADO = threading.Lock()


def _agora() -> float:
    """Segundos de um relógio que só anda para a frente. Função à parte para os testes poderem fixá-lo."""
    return time.monotonic()


def esquecer_recorrentes(user_id: str) -> None:
    """Apaga a cache do utilizador. Chama-se sempre que as movimentações dele mudam."""
    with _CADEADO:
        _CACHE.pop(user_id, None)


def normalizar_descricao(descricao: str) -> str:
    """A descrição sem o que muda de mês para mês: números, datas, referências, acentos e pontuação.

    Cada palavra com algum algarismo sai inteira (datas "05/10", referências "REF123456",
    cartões "XXXX1234", telefones). Das outras ficam só as letras, em minúsculas.
    """
    sem_acentos = unicodedata.normalize("NFKD", descricao).encode("ascii", "ignore").decode("ascii").lower()
    palavras = []
    for palavra in sem_acentos.split():
        if any(caractere.isdigit() for caractere in palavra):
            continue
        palavras.extend(re.findall(r"[a-z]+", palavra))
    return " ".join(palavras)


def e_generica(chave: str) -> bool:
    """Se a descrição normalizada não diz a quem se pagou (só palavras genéricas, ou quase nenhuma letra)."""
    letras = "".join(palavra for palavra in chave.split() if palavra not in PALAVRAS_GENERICAS)
    return len(letras) < LETRAS_MINIMAS


def _absoluto(mes: str) -> int:
    """ "2026-11" -> um número que sobe 1 por mês, para ver se dois meses são seguidos (dez -> jan incluído)."""
    return int(mes[:4]) * 12 + int(mes[5:7]) - 1


def _mes_de(absoluto: int) -> str:
    return f"{absoluto // 12:04d}-{absoluto % 12 + 1:02d}"


def _perto(a: float, b: float) -> bool:
    """Se dois valores estão a ±10% um do outro (em relação ao maior)."""
    return abs(a - b) <= max(a, b) * TOLERANCIA_VALOR


def _pagamento_do_mes(movimentos: list[dict]) -> dict | None:
    """O pagamento que conta num mês. Vários com valores parecidos contam como um (o mais recente);
    com valores diferentes, None (o mês parte a sequência)."""
    valores = [abs(m["valor"]) for m in movimentos]
    if not _perto(max(valores), min(valores)):
        return None
    return max(movimentos, key=lambda m: m["data"])


def _ultima_sequencia(pagamentos: dict[str, dict | None]) -> tuple[list[dict], float | None]:
    """A última sequência de meses seguidos que conta, e o valor antes da mudança de preço (se houve).

    Cada mês tem de ficar a ±10% do anterior. Aceita-se uma mudança maior (o preço mudou); uma segunda
    quer dizer que o preço não se manteve, e a sequência recomeça no mês anterior a ela.
    """
    sequencia: list[dict] = []
    valor_anterior: float | None = None
    mes_anterior: str | None = None
    for mes in sorted(pagamentos):
        pagamento = pagamentos[mes]
        seguido = mes_anterior is not None and _absoluto(mes) == _absoluto(mes_anterior) + 1
        mes_anterior = mes
        if pagamento is None or not seguido:
            sequencia, valor_anterior = ([pagamento] if pagamento else []), None
            continue
        if not sequencia:
            sequencia = [pagamento]
            continue
        ultimo = abs(sequencia[-1]["valor"])
        if not _perto(abs(pagamento["valor"]), ultimo):
            if valor_anterior is None:
                valor_anterior = ultimo  # a primeira mudança de preço: aceita-se
            else:
                sequencia, valor_anterior = [sequencia[-1]], ultimo  # segunda mudança: recomeça
        sequencia.append(pagamento)
    return sequencia, valor_anterior


def _recorrente_do_grupo(movimentos: list[dict], mes_anterior: str) -> Recorrente | None:
    """Vê se os movimentos de uma descrição normalizada são um pagamento mensal. None se não forem."""
    por_mes: dict[str, list[dict]] = {}
    for movimento in movimentos:
        por_mes.setdefault(movimento["data"][:7], []).append(movimento)
    pagamentos = {mes: _pagamento_do_mes(lista) for mes, lista in por_mes.items()}

    sequencia, valor_anterior = _ultima_sequencia(pagamentos)
    if len(sequencia) < MESES_MINIMOS or sequencia[-1]["data"][:7] < mes_anterior:
        return None

    ultimo = sequencia[-1]
    return Recorrente(
        descricao=ultimo["descricao"].strip(),
        categoria=ultimo.get("categoria"),
        valor_mensal=round(abs(ultimo["valor"]), 2),
        valor_anterior=round(valor_anterior, 2) if valor_anterior is not None else None,
        meses_seguidos=len(sequencia),
        ultimo_pagamento=date.fromisoformat(ultimo["data"][:10]),
    )


def agrupar_despesas(transacoes: list[dict]) -> dict[str, list[dict]]:
    """As despesas que podem ser pagamentos mensais, agrupadas pela descrição normalizada.

    Cada descrição normaliza-se uma só vez (é a parte mais pesada com milhares de movimentos).
    """
    grupos: dict[str, list[dict]] = {}
    for transacao in transacoes:
        if transacao["valor"] >= 0:  # só despesas: o salário também se repete, mas não é um pagamento
            continue
        if transacao.get("categoria") in CATEGORIAS_EXCLUIDAS:
            continue
        chave = normalizar_descricao(transacao["descricao"] or "")
        if e_generica(chave):
            continue
        grupos.setdefault(chave, []).append(transacao)
    return grupos


def recorrentes_dos_grupos(grupos: dict[str, list[dict]], hoje: date) -> list[tuple[str, Recorrente]]:
    """(chave, pagamento mensal) de cada grupo que é um pagamento mensal, do maior valor mensal para o menor."""
    mes_anterior = _mes_de(_absoluto(hoje.strftime("%Y-%m")) - 1)
    encontrados = [(chave, _recorrente_do_grupo(lista, mes_anterior)) for chave, lista in grupos.items()]
    return sorted(((c, r) for c, r in encontrados if r), key=lambda par: par[1].valor_mensal, reverse=True)


def detetar_recorrentes(transacoes: list[dict], hoje: date) -> list[Recorrente]:
    """Os pagamentos mensais nas transações (cada uma com data, descricao, valor e categoria).

    Do maior valor mensal para o menor.
    """
    return [recorrente for _, recorrente in recorrentes_dos_grupos(agrupar_despesas(transacoes), hoje)]


def _ler_despesas(user_id: str, hoje: date) -> list[dict]:
    """As despesas do último ano (e do mês atual), página a página."""
    desde = _mes_de(_absoluto(hoje.strftime("%Y-%m")) - MESES_A_LER) + "-01"
    return ler_todas(
        lambda: supabase.table("transacoes")
        .select("data, descricao, valor, categoria")
        .eq("user_id", user_id)
        .lt("valor", 0)
        .gte("data", desde)
        .order("id")
    )


def recorrentes_do_utilizador(user_id: str, hoje: date) -> list[Recorrente]:
    """Os pagamentos que se repetem, guardados na cache durante CACHE_SEGUNDOS (ou até o dia mudar)."""
    agora = _agora()
    with _CADEADO:
        guardado = _CACHE.get(user_id)
    if guardado and guardado[1] == hoje and agora - guardado[0] < CACHE_SEGUNDOS:
        return guardado[2]

    # A leitura da base de dados fica fora do cadeado: não bloqueia os pedidos dos outros utilizadores.
    recorrentes = detetar_recorrentes(_ler_despesas(user_id, hoje), hoje)
    with _CADEADO:
        # Tira as entradas que já passaram do prazo, para a cache não crescer sem fim.
        for chave in [chave for chave, (quando, _, _) in _CACHE.items() if agora - quando >= CACHE_SEGUNDOS]:
            _CACHE.pop(chave, None)
        _CACHE[user_id] = (agora, hoje, recorrentes)
    return recorrentes
