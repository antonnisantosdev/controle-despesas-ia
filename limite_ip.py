"""Limites de pedidos por IP, na memória do servidor (usados pela demo e pelas rotas de entrada e registo).
Também o limite de tentativas falhadas por conta (email) no POST /login: LimiteDeFalhasPorEmail.

- ip_do_pedido: o IP de quem fez o pedido (no Render, a 3.ª entrada a contar da direita do X-Forwarded-For).
- chave_do_ip: IPv6 conta por prefixo /64; prefixo_48_do_ipv6: segundo limite, por /48 (só IPv6).
- LimitePorIP: até N pedidos por chave em cada janela; acima disso, 429 com a mensagem do limite.

Nada disto escreve IPs nem emails nos logs.
"""

import hashlib
import hmac
import ipaddress
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException, Request

from mensagens import msg


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

    def devolver(self, ip: str) -> None:
        """Desconta um pedido já contado (ex.: uma tentativa reservada que afinal não falhou)."""
        chave = self.chave(ip)
        if chave is None:
            return
        with self._cadeado:
            if chave not in self._pedidos:
                return
            inicio, pedidos = self._pedidos[chave]
            if pedidos <= 1:
                del self._pedidos[chave]
            else:
                self._pedidos[chave] = (inicio, pedidos - 1)

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

# POST /lista-espera (página /brasil, em português do Brasil). Texto aprovado pelo copywriter.
MENSAGEM_MUITAS_INSCRICOES = "Muitas tentativas a partir desta rede. Tente novamente mais tarde."

# POST /login (email e palavra-passe).
LOGIN_POR_IP = 10
LOGIN_POR_48 = 30
LOGIN_JANELA_SEGUNDOS = 15 * MINUTO
# POST /registo.
REGISTO_POR_IP = 5
REGISTO_POR_48 = 15
REGISTO_JANELA_SEGUNDOS = HORA
# POST /lista-espera: os mesmos números do registo.
LISTA_ESPERA_POR_IP = 5
LISTA_ESPERA_POR_48 = 15
LISTA_ESPERA_JANELA_SEGUNDOS = HORA
# GET /login/google (o endereço do Supabase para começar o login com o Google).
GOOGLE_INICIO_POR_IP = 20
GOOGLE_INICIO_POR_48 = 60
GOOGLE_INICIO_JANELA_SEGUNDOS = 15 * MINUTO
# POST /login/google/troca (o regresso do Google).
GOOGLE_TROCA_POR_IP = 10
GOOGLE_TROCA_POR_48 = 30
GOOGLE_TROCA_JANELA_SEGUNDOS = 15 * MINUTO


# Interruptor de emergência: False desliga os limites das rotas públicas (ex.: se o Render mudar
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
LIMITE_LISTA_ESPERA = LimiteDaRota(
    LISTA_ESPERA_POR_IP, LISTA_ESPERA_POR_48, LISTA_ESPERA_JANELA_SEGUNDOS, MENSAGEM_MUITAS_INSCRICOES
)
LIMITE_GOOGLE_INICIO = LimiteDaRota(
    GOOGLE_INICIO_POR_IP, GOOGLE_INICIO_POR_48, GOOGLE_INICIO_JANELA_SEGUNDOS, MENSAGEM_MUITAS_ENTRADAS
)
LIMITE_GOOGLE_TROCA = LimiteDaRota(
    GOOGLE_TROCA_POR_IP, GOOGLE_TROCA_POR_48, GOOGLE_TROCA_JANELA_SEGUNDOS, MENSAGEM_MUITAS_ENTRADAS
)



# --- Limite por conta no POST /login (contra quem tenta palavras-passe na mesma conta) ---

# Só contam as tentativas falhadas (email ou palavra-passe errados).
# - Por (email, rede): 10 falhas em 15 min e 20 por dia. A rede é o /48 no IPv6 ou o próprio IPv4 (rede_do_ip).
#   Quem bloqueia uma conta assim só a bloqueia para a sua própria rede.
# - Por email sozinho: 100 falhas por dia, contra ataques distribuídos (só se atinge com 5 ou mais redes).
LOGIN_FALHAS_POR_EMAIL_E_REDE = 10
LOGIN_FALHAS_POR_EMAIL_E_REDE_JANELA_SEGUNDOS = 15 * MINUTO
LOGIN_FALHAS_POR_EMAIL_E_REDE_DIA = 20
LOGIN_FALHAS_POR_EMAIL_DIA = 100
# Proposta do dev-seguranca, por aprovar pelo copywriter. A mesma resposta exista ou não a conta.
MENSAGEM_MUITAS_FALHAS_NA_CONTA = "Muitas tentativas falhadas nesta conta. Tenta mais tarde ou entra com o Google."

# Sal aleatório, novo em cada arranque: a memória guarda só um HMAC-SHA-256 do email, nunca o email em claro,
# e sem o sal não se confirma um email conhecido contra os contadores.
_SAL_EMAIL = secrets.token_bytes(32)


def rede_do_ip(ip: str) -> str:
    """A rede com que um IP conta no limite por (email, rede): o /48 no IPv6, o próprio endereço no IPv4."""
    return prefixo_48_do_ipv6(ip) or chave_do_ip(ip)


def chave_do_email(email: str, rede: str | None = None) -> str:
    """HMAC-SHA-256 do email sem espaços à volta e em minúsculas (e da rede, se vier)."""
    texto = email.strip().lower()
    if rede is not None:
        texto = f"{texto}\x00{rede}"
    return hmac.new(_SAL_EMAIL, texto.encode("utf-8"), hashlib.sha256).hexdigest()


def _a_propria_chave(chave: str) -> str:
    return chave


@dataclass(frozen=True)
class ReservaDeTentativa:
    """As chaves de uma tentativa já contada (para a devolver se o login não falhar)."""

    chave_do_par: str
    chave_do_email: str


class LimiteDeFalhasPorEmail:
    """As falhas de login por (email, rede) numa janela curta e num dia, e por email num dia.

    A tentativa reserva-se ANTES de falar com o Supabase, de uma só vez (sob um cadeado), e devolve-se
    se o login der certo: assim muitos pedidos ao mesmo tempo não passam todos antes de algum contar.
    Usa o LimitePorIP com a chave já calculada (a classe só conta chaves, sejam IPs ou emails).
    Com o teto cheio esquece a chave mais antiga: quem inventa milhares de emails não bloqueia o login a todos.
    Respeita o interruptor LIMITES_PUBLICOS_LIGADOS.
    """

    def __init__(self, por_par: int, janela_segundos: float, por_par_dia: int, por_dia: int, mensagem: str):
        self.curto = LimitePorIP(por_par, janela_segundos, mensagem, chave=_a_propria_chave, esquecer_ao_encher=True)
        self.par_dia = LimitePorIP(por_par_dia, DIA, mensagem, chave=_a_propria_chave, esquecer_ao_encher=True)
        self.dia = LimitePorIP(por_dia, DIA, mensagem, chave=_a_propria_chave, esquecer_ao_encher=True)
        self._cadeado = threading.Lock()

    def _contadores(self, reserva: ReservaDeTentativa) -> list[tuple[LimitePorIP, str]]:
        """Cada contador com a chave da reserva que lhe toca."""
        return [
            (self.curto, reserva.chave_do_par),
            (self.par_dia, reserva.chave_do_par),
            (self.dia, reserva.chave_do_email),
        ]

    def reservar(self, email: str, ip: str) -> ReservaDeTentativa | None:
        """Conta já esta tentativa, ou responde 429 se a conta chegou a um dos limites (sem contar nada).
        None com os limites desligados."""
        if not LIMITES_PUBLICOS_LIGADOS:
            return None
        reserva = ReservaDeTentativa(chave_do_email(email, rede_do_ip(ip)), chave_do_email(email))
        with self._cadeado:
            contados: list[tuple[LimitePorIP, str]] = []
            try:
                for limite, chave in self._contadores(reserva):
                    limite.registar(chave)
                    contados.append((limite, chave))
            except HTTPException:
                # Um limite recusou: desconta-se o que já tinha sido contado nos outros.
                for limite, chave in contados:
                    limite.devolver(chave)
                raise
        return reserva

    def devolver(self, reserva: ReservaDeTentativa | None) -> None:
        """Desconta uma tentativa reservada que não foi uma falha (ver o POST /login em main.py)."""
        if reserva is None:
            return
        with self._cadeado:
            for limite, chave in self._contadores(reserva):
                limite.devolver(chave)

    def limpar(self) -> None:
        self.curto.limpar()
        self.par_dia.limpar()
        self.dia.limpar()


LIMITE_LOGIN_POR_EMAIL = LimiteDeFalhasPorEmail(
    LOGIN_FALHAS_POR_EMAIL_E_REDE,
    LOGIN_FALHAS_POR_EMAIL_E_REDE_JANELA_SEGUNDOS,
    LOGIN_FALHAS_POR_EMAIL_E_REDE_DIA,
    LOGIN_FALHAS_POR_EMAIL_DIA,
    MENSAGEM_MUITAS_FALHAS_NA_CONTA,
)

# --- Limite por conta no PUT /conta/perfil (mudar país, países das contas e moeda) ---

# Cada pedido lê a assinatura e chama a função atualizar_perfil_conta (que prende a linha da conta e conta
# os dados em 4 tabelas): sem teto, um script com uma conta válida martelava a base de dados.
# Conta por user_id (vem do token, nunca do pedido), na memória do servidor, como os limites por IP.
# Conta os pedidos que chegam à rota: já com sessão válida, fora da demo (423 antes) e com o corpo válido
# (um corpo inválido é recusado pelo Pydantic, sem tocar na base de dados). Os 409, 422 da moeda e 503
# também contam: cada um destes já leu a base de dados.
PERFIL_POR_CONTA = 10
PERFIL_JANELA_SEGUNDOS = HORA
# Proposta, por aprovar pelo copywriter. Em PT; a versão BR está em mensagens.py e o main.py escolhe (sem ler a base de dados).
MENSAGEM_MUITAS_MUDANCAS_DE_PERFIL = msg("perfil_muitas_mudancas", "PT")

# Interruptor de emergência: False desliga este limite (não depende do X-Forwarded-For, por isso é à parte
# do LIMITES_PUBLICOS_LIGADOS).
LIMITE_PERFIL_LIGADO = True

# Com o teto cheio esquece a conta mais antiga: muitas contas a mudar o perfil ao mesmo tempo nunca
# bloqueiam as definições de quem não abusou.
LIMITE_PERFIL = LimitePorIP(
    PERFIL_POR_CONTA,
    PERFIL_JANELA_SEGUNDOS,
    MENSAGEM_MUITAS_MUDANCAS_DE_PERFIL,
    chave=_a_propria_chave,
    esquecer_ao_encher=True,
)


def registar_mudanca_de_perfil(user_id: str) -> None:
    """Conta um pedido de mudança de perfil desta conta, ou responde 429 acima de PERFIL_POR_CONTA por hora."""
    if not LIMITE_PERFIL_LIGADO:
        return
    LIMITE_PERFIL.registar(str(user_id))


def limpar_limite_do_perfil() -> None:
    """Esquece os contadores do PUT /conta/perfil (para os testes)."""
    LIMITE_PERFIL.limpar()


LIMITES_DAS_ROTAS_PUBLICAS = (
    LIMITE_LOGIN,
    LIMITE_REGISTO,
    LIMITE_LISTA_ESPERA,
    LIMITE_GOOGLE_INICIO,
    LIMITE_GOOGLE_TROCA,
    LIMITE_LOGIN_POR_EMAIL,
)


def limpar_limites_das_rotas_publicas() -> None:
    """Esquece todos os contadores das rotas de entrada e registo (para os testes)."""
    for limite in LIMITES_DAS_ROTAS_PUBLICAS:
        limite.limpar()
