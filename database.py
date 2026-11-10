import os
from collections.abc import Callable

from dotenv import load_dotenv
from postgrest import SyncSelectRequestBuilder
from supabase import Client, create_client

# Lê o ficheiro .env e coloca os valores nas variáveis de ambiente.
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Faltam SUPABASE_URL ou SUPABASE_KEY no ficheiro .env")

# Um único cliente partilhado por toda a API.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
