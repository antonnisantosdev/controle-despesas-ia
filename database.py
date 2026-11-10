import os
from collections.abc import Callable

import httpx
from dotenv import load_dotenv
from postgrest import SyncSelectRequestBuilder
from supabase import Client, ClientOptions, create_client

# Lê o ficheiro .env e coloca os valores nas variáveis de ambiente.
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Faltam SUPABASE_URL ou SUPABASE_KEY no ficheiro .env")

# Erros de uma ligação que já não existe (ex.: a API acordou no Render e a ligação guardada morreu).
ERROS_DE_LIGACAO = (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError)
# Só leituras se repetem: uma escrita repetida podia gravar duas vezes.
METODOS_IDEMPOTENTES = {"GET", "HEAD"}


class TransporteQueRepete(httpx.BaseTransport):
    """Repete uma vez as leituras que falham por a ligação ter morrido; as escritas nunca se repetem.

    O httpx reaproveita ligações (keep-alive). Quando o Render adormece a API, a ligação ao Supabase
    morre do outro lado e o primeiro pedido ao acordar dava httpx.ReadError (500). Na segunda tentativa
    o httpx abre uma ligação nova.
    """

    def __init__(self, transporte: httpx.BaseTransport):
        self._transporte = transporte

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        try:
            return self._transporte.handle_request(request)
        except ERROS_DE_LIGACAO:
            if request.method not in METODOS_IDEMPOTENTES:
                raise
            return self._transporte.handle_request(request)

    def close(self) -> None:
        self._transporte.close()


def cliente_http() -> httpx.Client:
    """O cliente httpx do Supabase, com as mesmas opções que a biblioteca usa por omissão."""
    return httpx.Client(
        transport=TransporteQueRepete(httpx.HTTPTransport(http2=True)),
        # 30 s para ler (5 s para ligar): este cliente também valida os tokens (auth.get_user) e corre
        # no threadpool; com os 120 s do postgrest, um Supabase pendurado prendia as threads da API.
        timeout=httpx.Timeout(30, connect=5),
        follow_redirects=True,
    )


# Um único cliente partilhado por toda a API (base de dados e auth usam o mesmo cliente httpx).
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(httpx_client=cliente_http()))

# O Supabase devolve no máximo 1000 linhas por pedido, e corta o resto sem avisar.
TAMANHO_PAGINA = 1000


def ler_todas(nova_consulta: Callable[[], SyncSelectRequestBuilder]) -> list[dict]:
    """Lê todas as linhas de uma consulta, uma página de cada vez (como LIMIT e OFFSET em MySQL).

    nova_consulta é uma função que devolve a consulta já montada (select, filtros e order),
    sem o .execute(). Tem de ser uma consulta nova em cada página: o .range() altera a consulta.
    A consulta precisa de um .order(), senão a base de dados pode repetir ou saltar linhas entre páginas.
    """
    linhas: list[dict] = []
    while True:
        # Uma consulta nova em cada página: o .range() acrescenta parâmetros em vez de os substituir.
        consulta = nova_consulta()
        # O range inclui o início e o fim: de 0 a 999 são 1000 linhas.
        resposta = consulta.range(len(linhas), len(linhas) + TAMANHO_PAGINA - 1).execute()
        # Só uma página vazia diz que acabou. Parar numa página incompleta poupava um pedido,
        # mas perdia linhas se o Supabase devolvesse menos de TAMANHO_PAGINA por pedido (max_rows menor).
        if not resposta.data:
            break
        linhas.extend(resposta.data)
    return linhas
