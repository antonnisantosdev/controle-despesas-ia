-- Questionário de boas-vindas: o que a pessoa responde na 1.ª entrada (motivo e objetivos) e quando o acabou.
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.
-- Pode correr-se mais do que uma vez sem estragar nada (IF NOT EXISTS, DROP ... IF EXISTS).
-- Precisa da 020 (país, países das contas e moeda) já corrida.
--
-- ATENÇÃO: correr ANTES do deploy da API e do frontend que usam o questionário.
--   Sem esta migração a API continua a funcionar como hoje: o GET /plano diz que ninguém tem o questionário
--   por fazer (boas_vindas_pendente = false), e as rotas /conta/boas-vindas respondem 503.
--
-- 1. Tabela boas_vindas: uma linha por conta, com as duas respostas opcionais (sem texto livre).
--    motivo: porque instalou a app (uma opção da lista, ou NULL se saltou).
--    objetivos: o que quer conseguir (1 a 7 opções da lista, sem repetidos, ou NULL se saltou).
--    A IA não usa estas respostas; só servem para adaptar a app e para estatísticas agregadas.
--    Apagam-se com a conta (ON DELETE CASCADE). O país, os bancos e a moeda ficam em assinaturas (020).
-- 2. assinaturas.boas_vindas_em: quando a conta acabou o questionário. NULL = ainda por fazer.
--    As contas que JÁ existem (incluindo a demo) ficam marcadas agora: nunca veem o questionário.
--    As contas novas ficam com NULL: o gatilho da 013 (criar_assinatura_free) só escreve user_id, plano,
--    ativo_ate e notas, por isso a coluna nova fica com o valor por omissão (NULL).
--    A marcação só corre quando a coluna é criada: correr o ficheiro outra vez não marca as contas novas
--    que ainda não responderam.
--
-- Como verificar depois de correr: ver as consultas no fim do ficheiro.


-- === 1. Tabela boas_vindas ===

CREATE TABLE IF NOT EXISTS public.boas_vindas (
    user_id UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    motivo TEXT NULL,
    objetivos TEXT[] NULL,
    respondido_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- As regras (o DROP antes do ADD deixa correr o ficheiro outra vez).
ALTER TABLE public.boas_vindas DROP CONSTRAINT IF EXISTS boas_vindas_motivo_valido;
ALTER TABLE public.boas_vindas
    ADD CONSTRAINT boas_vindas_motivo_valido CHECK (
        motivo IN ('nao_sei', 'fim_mes', 'supermercado', 'folhas', 'poupar', 'experimentar', 'outro')
    );

-- 1 a 7 objetivos, só da lista, sem NULL e sem repetidos. Só listas simples a começar no índice 1 (como na 020).
-- COALESCE: numa lista vazia ('{}') o array_ndims dá NULL, e um CHECK com NULL deixava passar.
-- Sem repetidos: cada valor aparece no máximo uma vez (array_positions dá todas as posições desse valor;
-- num CHECK não pode haver subconsultas, por isso não dá para contar com unnest).
ALTER TABLE public.boas_vindas DROP CONSTRAINT IF EXISTS boas_vindas_objetivos_validos;
ALTER TABLE public.boas_vindas
    ADD CONSTRAINT boas_vindas_objetivos_validos CHECK (
        objetivos IS NULL
        OR (
            COALESCE(array_ndims(objetivos), 0) = 1
            AND array_lower(objetivos, 1) = 1
            AND cardinality(objetivos) BETWEEN 1 AND 7
            AND array_position(objetivos, NULL) IS NULL
            AND objetivos <@ ARRAY['importar', 'categorias', 'orcamento', 'chat', 'resumo', 'reserva', 'taloes']::TEXT[]
            AND cardinality(array_positions(objetivos, 'importar')) <= 1
            AND cardinality(array_positions(objetivos, 'categorias')) <= 1
            AND cardinality(array_positions(objetivos, 'orcamento')) <= 1
            AND cardinality(array_positions(objetivos, 'chat')) <= 1
            AND cardinality(array_positions(objetivos, 'resumo')) <= 1
            AND cardinality(array_positions(objetivos, 'reserva')) <= 1
            AND cardinality(array_positions(objetivos, 'taloes')) <= 1
        )
    );

-- Só a API (chave secreta) lê e escreve: RLS ligado e nenhuma policy (como as outras tabelas).
-- O REVOKE fecha também o acesso direto com a chave pública, mesmo que um dia alguém crie uma policy por engano.
ALTER TABLE public.boas_vindas ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.boas_vindas FROM anon, authenticated;


-- === 2. assinaturas.boas_vindas_em ===

-- Cria a coluna e marca todas as contas que já existem, de uma só vez e só da primeira vez.
-- Se a coluna já existir (ficheiro corrido outra vez), não faz nada: as contas novas continuam por responder.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'assinaturas' AND column_name = 'boas_vindas_em'
    ) THEN
        ALTER TABLE public.assinaturas ADD COLUMN boas_vindas_em TIMESTAMPTZ NULL;
        -- Contas antigas e demo: já "fizeram" o questionário (nunca o veem).
        UPDATE public.assinaturas SET boas_vindas_em = now();
    END IF;
END;
$$;

-- Pede à API do Supabase (PostgREST) para ver já a tabela e a coluna novas.
NOTIFY pgrst, 'reload schema';


-- === Como verificar (não faz parte da migração: correr à parte, depois) ===

-- a) RLS ligado e sem policies na tabela nova. Deve dar true e 0:
-- SELECT relrowsecurity FROM pg_class WHERE oid = 'public.boas_vindas'::regclass;
-- SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND tablename = 'boas_vindas';

-- b) Sem acesso direto com a chave pública. Deve dar false, false:
-- SELECT has_table_privilege('anon', 'public.boas_vindas', 'SELECT') AS anon,
--        has_table_privilege('authenticated', 'public.boas_vindas', 'SELECT') AS authenticated;

-- c) Todas as contas que já existiam ficaram marcadas. Logo a seguir a correr, deve dar 0:
-- SELECT count(*) FROM assinaturas WHERE boas_vindas_em IS NULL;

-- d) O gatilho do registo (013) não escreve a coluna nova. Deve dar uma linha sem "boas_vindas_em":
-- SELECT prosrc FROM pg_proc WHERE proname = 'criar_assinatura_free';

-- e) As regras recusam valores fora da lista, listas vazias e repetidos. Cada linha deve dar um erro e não mudar
--    nada: "violates check constraint" (no caso 2D pode ser "multidimensional arrays are not supported", que
--    recusa na mesma). Numa conta de TESTE, trocar o id; usar uma conta que já tenha linha em boas_vindas:
-- UPDATE boas_vindas SET motivo = 'outra_coisa' WHERE user_id = '00000000-0000-0000-0000-000000000000';
-- UPDATE boas_vindas SET objetivos = '{}' WHERE user_id = '00000000-0000-0000-0000-000000000000';
-- UPDATE boas_vindas SET objetivos = '{chat,chat}' WHERE user_id = '00000000-0000-0000-0000-000000000000';
-- UPDATE boas_vindas SET objetivos = '{{chat},{resumo}}' WHERE user_id = '00000000-0000-0000-0000-000000000000';
-- UPDATE boas_vindas SET objetivos = '[0:1]={chat,resumo}' WHERE user_id = '00000000-0000-0000-0000-000000000000';

-- f) Métricas (só agregadas, nunca por pessoa). Grupos com menos de 5 contas juntam-se em "outros"
--    (um grupo pequeno podia apontar para uma pessoa). Mudar o 5 só com o OK do CEO.
-- Respostas por motivo:
-- WITH grupos AS (SELECT coalesce(motivo, 'saltou') AS motivo, count(*) AS contas FROM boas_vindas GROUP BY 1)
-- SELECT CASE WHEN contas >= 5 THEN motivo ELSE 'outros' END AS motivo, sum(contas) AS contas
-- FROM grupos GROUP BY 1 HAVING sum(contas) >= 5 ORDER BY 2 DESC;
-- Respostas por objetivo:
-- WITH grupos AS (SELECT objetivo, count(*) AS contas FROM boas_vindas, unnest(objetivos) AS objetivo GROUP BY 1)
-- SELECT CASE WHEN contas >= 5 THEN objetivo ELSE 'outros' END AS objetivo, sum(contas) AS contas
-- FROM grupos GROUP BY 1 HAVING sum(contas) >= 5 ORDER BY 2 DESC;
-- Quantos saltaram os objetivos (só se o total tiver pelo menos 5 contas):
-- SELECT count(*) FILTER (WHERE objetivos IS NULL) AS saltou, count(*) AS total FROM boas_vindas HAVING count(*) >= 5;
