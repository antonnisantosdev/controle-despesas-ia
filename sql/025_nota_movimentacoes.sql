-- Nota pessoal nas movimentações (ex. "jantar de anos da Rita").
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.
-- Pode correr-se mais do que uma vez sem estragar nada (IF NOT EXISTS e DROP ... IF EXISTS).
--
-- ATENÇÃO: correr ANTES do deploy da API que usa esta coluna.
--   Sem esta migração a API continua a funcionar: as listas mostram as movimentações sem nota,
--   uma movimentação nova grava-se sem a nota (fica um aviso nos logs) e só o PATCH que muda
--   a nota responde 503.
--
-- A descrição (texto do banco) não muda: entra no hash_importacao, que deteta extratos repetidos.
-- A nota é outra coluna, opcional, escrita pela pessoa. NULL = sem nota.
-- Quem escreve é só a API (sql/015): o RLS continua a deixar cada pessoa ler apenas as suas linhas.
--
-- Como verificar depois de correr: ver as consultas no fim do ficheiro.


-- === 1. Coluna nova ===

ALTER TABLE public.transacoes ADD COLUMN IF NOT EXISTS nota TEXT NULL;

-- No máximo 300 caracteres (a API já recusa mais; esta regra protege a tabela de qualquer outro caminho).
-- O DROP antes do ADD deixa correr o ficheiro outra vez.
ALTER TABLE public.transacoes DROP CONSTRAINT IF EXISTS transacoes_nota_tamanho;
ALTER TABLE public.transacoes
    ADD CONSTRAINT transacoes_nota_tamanho CHECK (nota IS NULL OR char_length(nota) <= 300);


-- === 2. A API passa a ver a coluna nova logo (sem esperar pela cache do PostgREST) ===

NOTIFY pgrst, 'reload schema';


-- === Verificação (correr à parte, depois do Run) ===

-- A coluna existe, é TEXT e aceita NULL (1 linha: nota | text | YES):
-- SELECT column_name, data_type, is_nullable
--   FROM information_schema.columns
--  WHERE table_schema = 'public' AND table_name = 'transacoes' AND column_name = 'nota';

-- A regra do tamanho existe (1 linha):
-- SELECT conname, pg_get_constraintdef(oid)
--   FROM pg_constraint
--  WHERE conrelid = 'public.transacoes'::regclass AND conname = 'transacoes_nota_tamanho';

-- As movimentações antigas ficaram sem nota (logo a seguir à primeira vez, o número tem de ser 0):
-- SELECT count(*) FROM public.transacoes WHERE nota IS NOT NULL;
