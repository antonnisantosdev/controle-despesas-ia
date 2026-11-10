-- Fase 3, parte 2: preço de um produto por loja, a partir dos talões (Minhas compras).
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.
-- Pode correr-se mais do que uma vez sem estragar nada (IF NOT EXISTS e DROP ... IF EXISTS).
--
-- ATENÇÃO: correr ANTES do deploy. O código novo grava as colunas novas de compra_itens:
--   - sem esta migração, guardar um talão (POST /compras) falha com 500 (coluna inexistente);
--   - a reposição da demo também falha (os talões da demo já trazem as colunas novas);
--   - as rotas /compras/produtos falham (leem as colunas novas e a tabela produtos_alias).
-- A API antiga funciona com a migração já corrida (as colunas novas têm valor por omissão ou aceitam NULL).
--
-- 1. compra_itens ganha:
--    - produto_chave: o nome normalizado do produto (produtos.chave_do_produto), que junta o mesmo produto
--      entre talões e lojas ("LEITE UHT M/G 1L" e "Leite meio-gordo 1 L" dão "leite meio gordo 1 l");
--    - nome_generico: o nome curto lido pela IA ("leite meio gordo 1 l"), para mostrar na página de preços;
--    - unidade: em que se mede a quantidade ('un', 'kg' ou 'l'). Os preços só se comparam na mesma unidade.
-- 2. produtos_alias: quando o utilizador junta dois produtos que são o mesmo (chave_origem passa a contar
--    como chave_destino). RLS ligado e sem policies, como as outras tabelas: só a API (chave secreta) lhes toca.
--
-- Os itens já gravados ficam com produto_chave vazio (NULL) e unidade 'un'. Não se preenchem aqui:
-- a normalização (abreviaturas, quantidades, pesos) está em Python e não se consegue repetir igual em SQL.
-- A API calcula a chave desses itens ao ler (produtos.itens_do_utilizador), e trata uma quantidade
-- com casas decimais como kg. Nada fica por fazer à mão.
--
-- Como verificar depois de correr: ver as consultas no fim do ficheiro.


-- === 1. Colunas novas em compra_itens ===

ALTER TABLE public.compra_itens ADD COLUMN IF NOT EXISTS produto_chave TEXT NULL;
ALTER TABLE public.compra_itens ADD COLUMN IF NOT EXISTS nome_generico TEXT NULL;
ALTER TABLE public.compra_itens ADD COLUMN IF NOT EXISTS unidade TEXT NOT NULL DEFAULT 'un';

-- A regra das unidades (o DROP antes do ADD deixa correr o ficheiro outra vez).
ALTER TABLE public.compra_itens DROP CONSTRAINT IF EXISTS compra_itens_unidade_valida;
ALTER TABLE public.compra_itens
    ADD CONSTRAINT compra_itens_unidade_valida CHECK (unidade IN ('un', 'kg', 'l'));

-- Tetos de tamanho (a API já corta a chave em 100 e o nome genérico em 100).
ALTER TABLE public.compra_itens DROP CONSTRAINT IF EXISTS compra_itens_produto_chave_tamanho;
ALTER TABLE public.compra_itens
    ADD CONSTRAINT compra_itens_produto_chave_tamanho CHECK (char_length(produto_chave) <= 100);
ALTER TABLE public.compra_itens DROP CONSTRAINT IF EXISTS compra_itens_nome_generico_tamanho;
ALTER TABLE public.compra_itens
    ADD CONSTRAINT compra_itens_nome_generico_tamanho CHECK (char_length(nome_generico) <= 100);

-- Encontrar um produto pela chave.
CREATE INDEX IF NOT EXISTS compra_itens_produto_chave ON public.compra_itens (produto_chave);


-- === 2. Tabela produtos_alias ===

CREATE TABLE IF NOT EXISTS public.produtos_alias (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    chave_origem TEXT NOT NULL CHECK (char_length(chave_origem) BETWEEN 1 AND 100),
    chave_destino TEXT NOT NULL CHECK (char_length(chave_destino) BETWEEN 1 AND 100),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Uma chave só pode estar juntada a uma outra (juntar outra vez substitui: upsert na API).
    UNIQUE (user_id, chave_origem),
    CHECK (chave_origem <> chave_destino)
);

-- Só a API (chave secreta) lê e escreve.
ALTER TABLE public.produtos_alias ENABLE ROW LEVEL SECURITY;

-- Pede à API do Supabase (PostgREST) para ver já as colunas e a tabela novas.
NOTIFY pgrst, 'reload schema';


-- === Como verificar (não faz parte da migração: correr à parte, depois) ===

-- a) As colunas novas. Deve dar 3 linhas (nome_generico, produto_chave, unidade):
-- SELECT column_name, data_type, column_default
-- FROM information_schema.columns
-- WHERE table_schema = 'public' AND table_name = 'compra_itens'
--   AND column_name IN ('produto_chave', 'nome_generico', 'unidade');

-- b) RLS ligado e sem policies na tabela nova. Deve dar true e 0:
-- SELECT relrowsecurity FROM pg_class WHERE oid = 'public.produtos_alias'::regclass;
-- SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND tablename = 'produtos_alias';

-- c) Na app (plano pago): guardar um talão e abrir a página de preços; o produto deve aparecer.
