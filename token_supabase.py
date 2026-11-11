"""Validar os tokens do Supabase na própria API, sem pedir ao Supabase em cada pedido (JWKS).

Com chaves de assinatura assimétricas (Supabase > Settings > JWT Keys), o Supabase publica as chaves públicas
em {SUPABASE_URL}/auth/v1/.well-known/jwks.json. A API guarda-as em memória (CacheJWKS) e valida a assinatura,
o "exp", a audiência ("authenticated"), o emissor ({SUPABASE_URL}/auth/v1) e o "sub" (UUID).

ler_token_supabase devolve:
- o id do utilizador, se o token for válido;
- None, se não se consegue decidir aqui (projeto ainda com o segredo HS256, token sem "kid" ou com um "kid"
  que não está no JWKS, JWKS em baixo): quem chama pergunta ao Supabase (get_user), como antes;
- TokenInvalido, se o token for de uma das nossas chaves mas não servir (expirado, assinatura errada...) ou "alg": "none".

Limite conhecido: um token validado aqui continua a valer até expirar (1 h no Supabase), mesmo que a conta
seja apagada ou a sessão terminada. Ver obter_utilizador_atual e obter_utilizador_confirmado (auth.py).
"""

import re
import threading
import time
from collections.abc import Callable
from typing import Any

import httpx
import jwt

# Só estes algoritmos se validam aqui (as chaves assimétricas do Supabase: ECC P-256 e RSA).
# Nunca HS256 com uma chave pública (confusão de algoritmos) nem "none".
ALGORITMOS_ACEITES = frozenset({"ES256", "RS256"})
AUDIENCIA = "authenticated"
PAPEL = "authenticated"
FOLGA_RELOGIO_SEGUNDOS = 30
FORMATO_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

# Quanto tempo se usam as chaves guardadas antes de as ir buscar outra vez.
VALIDADE_CACHE_SEGUNDOS = 10 * 60
# Um "kid" desconhecido obriga a ir buscar o JWKS (o Supabase pode ter rodado a chave), mas no máximo
# uma vez por este intervalo: quem inventa "kid" não consegue pôr a API a pedir o JWKS em cada pedido.
INTERVALO_MINIMO_ENTRE_PEDIDOS = 30
# Se o pedido do JWKS falhar, espera-se isto antes de tentar outra vez (entretanto usa-se o get_user).
ESPERA_DEPOIS_DE_FALHA = 60


class TokenInvalido(Exception):
    """O token foi recusado aqui; a resposta é 401."""


def emissor_esperado(supabase_url: str) -> str:
    """O "iss" dos tokens: {SUPABASE_URL}/auth/v1.

    Atenção: com um domínio próprio no Supabase (custom domain), o "iss" e o JWKS passam a usar esse domínio.
    Nesse caso o SUPABASE_URL do .env tem de ser o domínio próprio, senão todos os tokens levam 401.
    """
    return f"{supabase_url.rstrip('/')}/auth/v1"


def url_jwks(supabase_url: str) -> str:
    return f"{emissor_esperado(supabase_url)}/.well-known/jwks.json"


def _relogio() -> float:
    return time.monotonic()


def _pedir_jwks(url: str) -> dict[str, Any]:
    """Pede o JWKS ao Supabase (pedido público, sem chaves). Timeout curto: corre dentro de um pedido à API."""
    resposta = httpx.get(url, timeout=httpx.Timeout(5, connect=3))
    resposta.raise_for_status()
    return resposta.json()


def _chaves_do_jwks(jwks: Any) -> dict[str, jwt.PyJWK]:
    """As chaves públicas utilizáveis, por "kid". Ignora as simétricas ("oct"), as sem "kid"
    e as de outros algoritmos."""
    chaves: dict[str, jwt.PyJWK] = {}
    if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
        return chaves
    for dados in jwks["keys"]:
        if not isinstance(dados, dict) or dados.get("kty") not in ("EC", "RSA"):
            continue
        if dados.get("use", "sig") != "sig" or not isinstance(dados.get("kid"), str):
            continue
        try:
            chave = jwt.PyJWK(dados)
        except (jwt.PyJWKError, jwt.InvalidKeyError):
            continue
        if chave.algorithm_name in ALGORITMOS_ACEITES:
            chaves[dados["kid"]] = chave
    return chaves


class CacheJWKS:
    """As chaves públicas do Supabase em memória, renovadas a cada VALIDADE_CACHE_SEGUNDOS
    ou quando aparece um "kid" desconhecido (com o travão do INTERVALO_MINIMO_ENTRE_PEDIDOS).

    O pedido do JWKS faz-se fora do cadeado: só um pedido vai buscá-lo de cada vez, e os outros
    usam entretanto as chaves que já havia (ou, sem chaves, o get_user). Assim um Supabase lento
    não prende os outros pedidos à API.
    """

    def __init__(self, url: str, pedir: Callable[[str], dict[str, Any]] = _pedir_jwks):
        self.url = url
        self.pedir = pedir
        self._chaves: dict[str, jwt.PyJWK] = {}
        self._valido_ate: float | None = None  # None: ainda não se pediu
        self._ultimo_pedido: float | None = None
        self._a_pedir = False
        self._avisado_sem_chaves = False
        self._cadeado = threading.Lock()

    def chave(self, kid: str) -> jwt.PyJWK | None:
        """A chave com este "kid", ou None se não houver (ou se o JWKS não estiver disponível)."""
        with self._cadeado:
            agora = _relogio()
            expirou = self._valido_ate is None or agora >= self._valido_ate
            desconhecido = kid not in self._chaves and self._pode_pedir(agora)
            if self._a_pedir or not (expirou or desconhecido):
                return self._chaves.get(kid)
            self._a_pedir = True
            self._ultimo_pedido = agora
        try:
            self._renovar()
        finally:
            with self._cadeado:
                self._a_pedir = False
        with self._cadeado:
            return self._chaves.get(kid)

    def _pode_pedir(self, agora: float) -> bool:
        return self._ultimo_pedido is None or agora - self._ultimo_pedido >= INTERVALO_MINIMO_ENTRE_PEDIDOS

    def _renovar(self) -> None:
        """Pede o JWKS (fora do cadeado) e guarda as chaves que servem."""
        try:
            jwks = self.pedir(self.url)
            chaves = _chaves_do_jwks(jwks)
        except Exception as erro:
            # Só o tipo no log. As chaves antigas deixam de se usar: na dúvida, o get_user decide.
            print(f"AVISO: não foi possível ler o JWKS do Supabase ({type(erro).__name__}); a usar o get_user.")
            with self._cadeado:
                self._chaves = {}
                self._valido_ate = _relogio() + ESPERA_DEPOIS_DE_FALHA
            return
        self._avisar_se_nenhuma_chave_serve(jwks, chaves)
        with self._cadeado:
            self._chaves = chaves
            self._valido_ate = _relogio() + VALIDADE_CACHE_SEGUNDOS

    def _avisar_se_nenhuma_chave_serve(self, jwks: Any, chaves: dict[str, jwt.PyJWK]) -> None:
        """Um aviso (uma vez por arranque) se o JWKS tem chaves e nenhuma serve: tudo segue para o get_user.
        Ex.: algoritmo novo no Supabase ou o cryptography em falta. Sem dados das chaves no log."""
        tem_chaves = isinstance(jwks, dict) and isinstance(jwks.get("keys"), list) and len(jwks["keys"]) > 0
        if tem_chaves and not chaves and not self._avisado_sem_chaves:
            self._avisado_sem_chaves = True
            print("AVISO: o JWKS do Supabase tem chaves, mas nenhuma serve (ES256/RS256); a usar o get_user.")

    def limpar(self) -> None:
        with self._cadeado:
            self._chaves = {}
            self._valido_ate = None
            self._ultimo_pedido = None
            self._a_pedir = False


def ler_token_supabase(token: str, chaves: CacheJWKS, emissor: str) -> str | None:
    """O id do utilizador de um token do Supabase validado aqui, None para perguntar ao Supabase,
    ou TokenInvalido (ver o topo do ficheiro)."""
    try:
        cabecalho = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError:
        # Nem parece um JWT: o get_user responde como sempre respondeu.
        return None
    algoritmo = cabecalho.get("alg")
    if not isinstance(algoritmo, str) or algoritmo.lower() == "none":
        raise TokenInvalido("alg inválido")
    kid = cabecalho.get("kid")
    if algoritmo not in ALGORITMOS_ACEITES or not isinstance(kid, str):
        # Ex.: projeto ainda com o segredo HS256 (que a API não tem): decide o Supabase.
        return None
    chave = chaves.chave(kid)
    if chave is None:
        return None
    if chave.algorithm_name != algoritmo:
        # O token diz um algoritmo e a chave é de outro: tentativa de confusão de algoritmos.
        raise TokenInvalido("alg diferente da chave")
    try:
        dados = jwt.decode(
            token,
            chave.key,
            algorithms=[algoritmo],
            audience=AUDIENCIA,
            issuer=emissor,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
            leeway=FOLGA_RELOGIO_SEGUNDOS,
        )
    except jwt.InvalidTokenError as erro:
        raise TokenInvalido(type(erro).__name__) from None
    sub = dados.get("sub")
    if not isinstance(sub, str) or not FORMATO_UUID.fullmatch(sub):
        raise TokenInvalido("sub inválido")
    if dados.get("role") != PAPEL:
        raise TokenInvalido("role inválido")
    return sub
