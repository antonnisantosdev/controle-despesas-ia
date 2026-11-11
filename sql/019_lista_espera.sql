-- Marketing: lista de espera do Brasil e origem do registo (o canal de onde a pessoa veio, pelo utm_source).
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.
-- Pode correr-se mais do que uma vez sem estragar nada (IF NOT EXISTS e DROP ... IF EXISTS).
--
-- ATENÇÃO: correr ANTES do deploy.
--   - sem esta migração, o POST /lista-espera responde 503 (tabela inexistente);
--   - o registo e o login com o Google continuam a funcionar: se a coluna origem não existir,
--     a API só escreve um aviso no log (sem dados) e segue.
--
-- 1. lista_espera: quem pediu para ser avisado quando a app abrir no Brasil.
--    Só email, país onde vive, países dos cartões/contas que vai usar, origem, a data do consentimento e a versão do texto aceite (finalidade única: esse aviso).
--    consentimento_versao: posta pela API (lista_espera.VERSAO_CONSENTIMENTO), nunca pelo browser.
--    RLS ligado e sem policies: só a API (chave secreta) lê e escreve.
--    O email guarda-se já em minúsculas (a API normaliza); o CHECK garante que fica assim.
-- 2. assinaturas.origem: o canal de cada conta nova (instagram, youtube, tiktok, linkedin ou outro).
--    A linha é criada pelo gatilho do registo (sql/013); a API preenche a origem logo a seguir,
--    só se ainda estiver vazia. NULL = conta sem link com UTM (ou criada antes desta migração).
--
-- Como verificar depois de correr: ver as consultas no fim do ficheiro.


-- === 1. Tabela lista_espera ===

CREATE TABLE IF NOT EXISTS public.lista_espera (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL CHECK (char_length(email) BETWEEN 3 AND 254 AND email = lower(email)),
    pais TEXT NOT NULL CHECK (pais IN ('BR', 'PT', 'outro')),
    -- Países dos cartões e contas que a pessoa vai usar: 1 a 3, só da lista (a API recusa repetidos).
    paises_cartoes TEXT[] NOT NULL CHECK (
        cardinality(paises_cartoes) BETWEEN 1 AND 3
        AND array_position(paises_cartoes, NULL) IS NULL
        AND paises_cartoes <@ ARRAY['BR', 'PT', 'outro']::TEXT[]
    ),
    origem TEXT NULL CHECK (origem IN ('instagram', 'youtube', 'tiktok', 'linkedin', 'outro')),
    consentimento_em TIMESTAMPTZ NOT NULL,
    consentimento_versao TEXT NOT NULL CHECK (char_length(consentimento_versao) BETWEEN 1 AND 50),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Um email só entra uma vez (a API ignora o segundo pedido e responde igual).
    UNIQUE (email)
);

-- Só a API (chave secreta) lê e escreve.
ALTER TABLE public.lista_espera ENABLE ROW LEVEL SECURITY;


-- === 2. Coluna origem em assinaturas ===

ALTER TABLE public.assinaturas ADD COLUMN IF NOT EXISTS origem TEXT NULL;

-- A lista fechada (o DROP antes do ADD deixa correr o ficheiro outra vez).
ALTER TABLE public.assinaturas DROP CONSTRAINT IF EXISTS assinaturas_origem_valida;
ALTER TABLE public.assinaturas
    ADD CONSTRAINT assinaturas_origem_valida
    CHECK (origem IN ('instagram', 'youtube', 'tiktok', 'linkedin', 'outro'));

-- Pede à API do Supabase (PostgREST) para ver já a tabela e a coluna novas.
NOTIFY pgrst, 'reload schema';


-- === Como verificar (não faz parte da migração: correr à parte, depois) ===

-- a) RLS ligado e sem policies na tabela nova. Deve dar true e 0:
-- SELECT relrowsecurity FROM pg_class WHERE oid = 'public.lista_espera'::regclass;
-- SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND tablename = 'lista_espera';

-- b) A coluna nova. Deve dar 1 linha (origem, text):
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_schema = 'public' AND table_name = 'assinaturas' AND column_name = 'origem';

-- c) Registos por canal (para as métricas semanais):
-- SELECT coalesce(origem, 'sem origem') AS origem, count(*) FROM assinaturas GROUP BY 1 ORDER BY 2 DESC;

-- d) Inscritos na lista de espera, por país e canal:
-- SELECT pais, coalesce(origem, 'sem origem') AS origem, count(*) FROM lista_espera GROUP BY 1, 2 ORDER BY 3 DESC;

-- e) Conservação (até 12 meses ou até à abertura no Brasil, o que vier primeiro). Apagar os antigos:
-- DELETE FROM lista_espera WHERE consentimento_em < now() - interval '12 months';
