import os

from dotenv import load_dotenv
from supabase import Client, create_client

# Lê o ficheiro .env e coloca os valores nas variáveis de ambiente.
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Faltam SUPABASE_URL ou SUPABASE_KEY no ficheiro .env")

# Um único cliente partilhado por toda a API.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
