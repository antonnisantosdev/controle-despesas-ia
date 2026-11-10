"""Limites de pedidos por IP, na memória do servidor (usados pela demo e pelas rotas de entrada e registo).

- ip_do_pedido: o IP de quem fez o pedido (no Render, a 3.ª entrada a contar da direita do X-Forwarded-For).
- chave_do_ip: IPv6 conta por prefixo /64; prefixo_48_do_ipv6: segundo limite, por /48 (só IPv6).
- LimitePorIP: até N pedidos por chave em cada janela; acima disso, 429 com a mensagem do limite.

Nada disto escreve IPs nos logs.
"""

import ipaddress
import threading
import time
from collections.abc import Callable

from fastapi import HTTPException, Request


def _relogio() -> float:
    """Segundos de um relógio que só anda para a frente. Função à parte para os testes poderem fixá-lo."""
    return time.monotonic()


# Quantos proxies de confiança acrescentam entradas ao X-Forwarded-For depois do visitante.
# No Render (log de 2026-11-10): [visitante, Cloudflare, proxy interno do Render] -> 2 proxies.
# Quem inventa entradas só as consegue pôr à esquerda do visitante, por isso conta-se a partir da direita.
PROXIES_A_FRENTE = 2


def ip_do_pedido(request: Request) -> str:
    """O IP de quem fez o pedido: a entrada do X-Forwarded-For logo à esquerda das que os proxies
    de confiança acrescentaram (PROXIES_A_FRENTE a contar da direita).

    As entradas mais à esquerda vêm do browser e podem ser inventadas para fugir ao limite.
    Sem entradas suficientes (ex.: em local, sem proxies), usa a mais à esquerda ou o IP da ligação.
    """
    entradas = _entradas_encaminhadas(request)
    if len(entradas) > PROXIES_A_FRENTE:
        return entradas[-(PROXIES_A_FRENTE + 1)]
    if entradas:
        return entradas[0]
    return request.client.host if request.client else "desconhecido"


def _entradas_encaminhadas(request: Request) -> list[str]:
    encaminhado = request.headers.get("x-forwarded-for", "")
    return [entrada.strip() for entrada in encaminhado.split(",") if entrada.strip()]


def chave_do_ip(ip: str) -> str:
    """A chave com que o IP conta para os limites.

    IPv6: conta o prefixo /64 inteiro (cada casa ou telemóvel recebe um /64 e pode mudar de endereço
    dentro dele à vontade). IPv4 (também dentro de IPv6, "::ffff:1.2.3.4"): o próprio endereço.
    Um texto que não seja um IP conta tal e qual.
    """
    try:
        endereco = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if isinstance(endereco, ipaddress.IPv6Address):
        if endereco.ipv4_mapped is not None:
            return str(endereco.ipv4_mapped)
        return str(ipaddress.IPv6Network(f"{endereco}/64", strict=False))
    return str(endereco)


def prefixo_48_do_ipv6(ip: str) -> str | None:
    """O prefixo /48 de um IPv6 ("2001:db8:1::/48"), ou None se não for IPv6 (um IPv4 não conta neste limite).

    Quem tem um /48 inteiro (um escritório, alguns fornecedores) pode usar 65 536 prefixos /64 diferentes:
    sem este segundo limite, fugia ao limite por /64.
    """
    try:
        endereco = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if not isinstance(endereco, ipaddress.IPv6Address) or endereco.ipv4_mapped is not None:
        return None
    return str(ipaddress.IPv6Network(f"{endereco}/48", strict=False))


class LimitePorIP:
    """Até `maximo` pedidos por IP em cada janela de `janela_segundos` (a janela começa no primeiro pedido).

    Vive na memória: perde-se quando o Render reinicia e não se partilha entre servidores (só há um).
    Com o teto de IPs cheio (mesmo depois de limpar as janelas que acabaram), os IPs novos levam 429
    com a `mensagem_teto` (sem ela, a `mensagem` do limite): na dúvida fecha-se, em vez de deixar
    a memória crescer sem fim.
    Os IPv6 contam por prefixo /64 (chave_do_ip). chave: outra forma de agrupar os IPs (ex.: por /48);
    se devolver None, o pedido não conta neste limite.
    """

    def __init__(
        self,
        maximo: int,
        janela_segundos: float,
        mensagem: str,
        teto_ips: int = 10_000,
        chave: Callable[[str], str | None] = chave_do_ip,
        mensagem_teto: str | None = None,
        esquecer_ao_encher: bool = False,
    ):
        # esquecer_ao_encher: com o teto cheio, esquece o IP mais antigo em vez de recusar os novos.
        # Usa-se nas rotas de entrada: recusar os novos deixava quem tem milhares de IPs bloquear o login
        # a toda a gente, e esse atacante já contorna o limite por IP de qualquer forma.
        self.esquecer_ao_encher = esquecer_ao_encher
        self.chave = chave
        self.maximo = maximo
        self.janela_segundos = janela_segundos
        self.mensagem = mensagem
        self.mensagem_teto = mensagem_teto or mensagem
        self.teto_ips = teto_ips
        self._pedidos: dict[str, tuple[float, int]] = {}  # ip -> (início da janela, pedidos)
        self._cadeado = threading.Lock()

    def _limpar_expiradas(self, agora: float) -> None:
        expiradas = [ip for ip, (inicio, _) in self._pedidos.items() if agora - inicio >= self.janela_segundos]
        for ip in expiradas:
            del self._pedidos[ip]

    def verificar(self, ip: str) -> None:
        """Responde 429 se este IP já chegou ao máximo da janela, sem contar o pedido."""
        chave = self.chave(ip)
        if chave is None:
            return
        with self._cadeado:
            agora = _relogio()
            inicio, pedidos = self._pedidos.get(chave, (agora, 0))
            if agora - inicio < self.janela_segundos and pedidos >= self.maximo:
                raise HTTPException(status_code=429, detail=self.mensagem)

    def registar(self, ip: str) -> None:
        """Conta o pedido deste IP, ou responde 429 se já chegou ao máximo da janela."""
        chave = self.chave(ip)
        if chave is None:
            return
        ip = chave
        with self._cadeado:
            agora = _relogio()
            inicio, pedidos = self._pedidos.get(ip, (agora, 0))
            if agora - inicio >= self.janela_segundos:
                inicio, pedidos = agora, 0
            if ip not in self._pedidos and len(self._pedidos) >= self.teto_ips:
                self._limpar_expiradas(agora)
                if len(self._pedidos) >= self.teto_ips:
                    if not self.esquecer_ao_encher:
                        raise HTTPException(status_code=429, detail=self.mensagem_teto)
                    mais_antigo = min(self._pedidos, key=lambda k: self._pedidos[k][0])
                    del self._pedidos[mais_antigo]
            if pedidos >= self.maximo:
                raise HTTPException(status_code=429, detail=self.mensagem)
            self._pedidos[ip] = (inicio, pedidos + 1)

    def limpar(self) -> None:
        """Esquece todos os IPs (para os testes)."""
        with self._cadeado:
            self._pedidos.clear()


MINUTO = 60
HORA = 60 * MINUTO
DIA = 24 * HORA


# --- Limites das rotas públicas de entrada e registo (antes de qualquer pedido ao Supabase) ---

# Textos aprovados pelo copywriter.
MENSAGEM_MUITAS_ENTRADAS = (
    "Houve muitas tentativas de entrar a partir desta rede. Tenta outra vez daqui a uns minutos."
)
MENSAGEM_MUITOS_REGISTOS = (
    "Houve muitos pedidos para criar conta a partir desta rede. Tenta outra vez mais tarde."
)

# POST /login (email e palavra-passe).
LOGIN_POR_IP = 10
LOGIN_POR_48 = 30
LOGIN_JANELA_SEGUNDOS = 15 * MINUTO
# POST /registo.
REGISTO_POR_IP = 5
REGISTO_POR_48 = 15
REGISTO_JANELA_SEGUNDOS = HORA
# GET /login/google (o endereço do Supabase para começar o login com o Google).
GOOGLE_INICIO_POR_IP = 20
GOOGLE_INICIO_POR_48 = 60
GOOGLE_INICIO_JANELA_SEGUNDOS = 15 * MINUTO
# POST /login/google/troca (o regresso do Google).
GOOGLE_TROCA_POR_IP = 10
GOOGLE_TROCA_POR_48 = 30
GOOGLE_TROCA_JANELA_SEGUNDOS = 15 * MINUTO


# Interruptor de emergência: False desliga os limites das 4 rotas públicas (ex.: se o Render mudar
# a forma do X-Forwarded-For e toda a gente passar a contar como o mesmo IP).
LIMITES_PUBLICOS_LIGADOS = True


class LimiteDaRota:
    """Os dois limites de uma rota: por IP (/64 no IPv6) e por /48 (só IPv6). Cada rota tem os seus contadores."""

    def __init__(self, por_ip: int, por_48: int, janela_segundos: float, mensagem: str):
        self.por_ip = LimitePorIP(por_ip, janela_segundos, mensagem, esquecer_ao_encher=True)
        self.por_48 = LimitePorIP(
            por_48, janela_segundos, mensagem, chave=prefixo_48_do_ipv6, esquecer_ao_encher=True
        )

    def __call__(self, request: Request) -> None:
        """Para usar como dependência do FastAPI: conta o pedido antes de a rota correr (e antes de ler o corpo).

        Primeiro verifica os dois limites e só depois conta: um pedido recusado pelo limite do IP não sobe
        o contador do /48, para um só telemóvel não bloquear a rede inteira dos vizinhos.
        """
        if not LIMITES_PUBLICOS_LIGADOS:
            return
        ip = ip_do_pedido(request)
        self.por_ip.verificar(ip)
        self.por_48.verificar(ip)
        self.por_ip.registar(ip)
        self.por_48.registar(ip)

    def limpar(self) -> None:
        self.por_ip.limpar()
        self.por_48.limpar()


LIMITE_LOGIN = LimiteDaRota(LOGIN_POR_IP, LOGIN_POR_48, LOGIN_JANELA_SEGUNDOS, MENSAGEM_MUITAS_ENTRADAS)
LIMITE_REGISTO = LimiteDaRota(REGISTO_POR_IP, REGISTO_POR_48, REGISTO_JANELA_SEGUNDOS, MENSAGEM_MUITOS_REGISTOS)
LIMITE_GOOGLE_INICIO = LimiteDaRota(
    GOOGLE_INICIO_POR_IP, GOOGLE_INICIO_POR_48, GOOGLE_INICIO_JANELA_SEGUNDOS, MENSAGEM_MUITAS_ENTRADAS
)
LIMITE_GOOGLE_TROCA = LimiteDaRota(
    GOOGLE_TROCA_POR_IP, GOOGLE_TROCA_POR_48, GOOGLE_TROCA_JANELA_SEGUNDOS, MENSAGEM_MUITAS_ENTRADAS
)

LIMITES_DAS_ROTAS_PUBLICAS = (LIMITE_LOGIN, LIMITE_REGISTO, LIMITE_GOOGLE_INICIO, LIMITE_GOOGLE_TROCA)


def limpar_limites_das_rotas_publicas() -> None:
    """Esquece todos os contadores das rotas de entrada e registo (para os testes)."""
    for limite in LIMITES_DAS_ROTAS_PUBLICAS:
        limite.limpar()
