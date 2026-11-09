-- Fase 1: medição dos pedidos à IA, limite de extratos PDF por mês e resumos guardados.
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.
-- Pode correr-se mais do que uma vez sem estragar nada (IF NOT EXISTS, DROP ... IF EXISTS e CREATE OR REPLACE).
-- A API funciona antes e depois desta migração: enquanto não for corrida, usa os caminhos antigos
-- (limites.py, ia.py e resumo.py) e deixa avisos nos logs do Render.
--
-- 1. uso_ia.funcao: para que foi cada pedido à IA (chat, importar_csv, importar_pdf, resumo, orcamento,
--    talao, poupanca, categorizar, categorizar_pendentes). Os PDF do mês contam-se por esta coluna
--    (funcao = 'importar_pdf'). As linhas antigas ficam com funcao vazia (NULL).
-- 2. registar_pedido_ia ganha o parâmetro p_funcao (com default NULL: quem a chamar sem ele continua a funcionar).
-- 3. chamadas_ia: stop_reason (porque parou a resposta) e os tokens da cache (lidos e escritos).
-- 4. resumos_ia: o resumo do mês escrito pela IA fica guardado, em vez de ficar só na memória do servidor
--    (que se perde quando o Render reinicia e obrigava a gastar outro pedido).
--
-- Como verificar depois de correr: ver as consultas no fim do ficheiro.


-- === 1. Coluna funcao em uso_ia ===

ALTER TABLE public.uso_ia ADD COLUMN IF NOT EXISTS funcao TEXT NULL;

-- A contagem "quantos PDF este mês?" filtra por utilizador, funcao e data.
CREATE INDEX IF NOT EXISTS uso_ia_user_funcao_data ON public.uso_ia (user_id, funcao, criado_em);


-- === 2. registar_pedido_ia com p_funcao ===

-- Apaga a versão da 015 (3 parâmetros). Se ficassem as duas, uma chamada com 3 parâmetros
-- seria ambígua (as duas serviam) e o PostgREST recusava-a.
DROP FUNCTION IF EXISTS public.registar_pedido_ia(uuid, timestamptz, int);

-- Igual à da 015 (ver lá a explicação do cadeado, do SECURITY INVOKER e do search_path vazio),
-- mas grava também a funcao do pedido.
CREATE OR REPLACE FUNCTION public.registar_pedido_ia(
    p_user_id uuid,
    p_desde timestamptz,
    p_limite int,
    p_funcao text DEFAULT NULL
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_pedidos int;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext(p_user_id::text));

    SELECT count(*) INTO v_pedidos
    FROM public.uso_ia
    WHERE user_id = p_user_id
      AND criado_em >= p_desde;

    IF v_pedidos >= p_limite THEN
        RETURN false;
    END IF;

    INSERT INTO public.uso_ia (user_id, funcao) VALUES (p_user_id, p_funcao);
    RETURN true;
END;
$$;

-- Só a API a pode chamar (como na 015).
REVOKE EXECUTE ON FUNCTION public.registar_pedido_ia(uuid, timestamptz, int, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.registar_pedido_ia(uuid, timestamptz, int, text) TO service_role;


-- === 3. Colunas novas em chamadas_ia ===

ALTER TABLE public.chamadas_ia ADD COLUMN IF NOT EXISTS stop_reason TEXT NULL;
-- As chamadas antigas ficam com 0 (não usávamos a cache).
ALTER TABLE public.chamadas_ia ADD COLUMN IF NOT EXISTS cache_read_tokens INTEGER NOT NULL DEFAULT 0;
ALTER TABLE public.chamadas_ia ADD COLUMN IF NOT EXISTS cache_creation_tokens INTEGER NOT NULL DEFAULT 0;


-- === 4. Tabela resumos_ia ===

-- Um resumo por utilizador e por mês: quando os números do mês mudam, o resumo novo substitui o antigo.
-- assinatura: impressão digital (SHA-256) dos números do mês usados no resumo. Se for igual,
-- a API devolve o texto guardado sem chamar a IA nem gastar um pedido.
CREATE TABLE IF NOT EXISTS public.resumos_ia (
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    mes TEXT NOT NULL CHECK (mes ~ '^\d{4}-(0[1-9]|1[0-2])$'),  -- "2026-11"
    assinatura TEXT NOT NULL,
    texto TEXT NOT NULL,
    alertas JSONB NOT NULL DEFAULT '[]'::jsonb,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, mes)
);

-- RLS ligado e nenhuma policy: só a API (chave secreta) lê e escreve.
ALTER TABLE public.resumos_ia ENABLE ROW LEVEL SECURITY;


-- Pede à API do Supabase (PostgREST) para ver já as colunas, a função e a tabela novas.
NOTIFY pgrst, 'reload schema';


-- === Como verificar (não faz parte da migração: correr à parte, depois) ===

-- a) Colunas novas. Deve dar 4 linhas: chamadas_ia (cache_creation_tokens, cache_read_tokens, stop_reason) e uso_ia (funcao).
-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND ((table_name = 'uso_ia' AND column_name = 'funcao')
--     OR (table_name = 'chamadas_ia' AND column_name IN ('stop_reason', 'cache_read_tokens', 'cache_creation_tokens')))
-- ORDER BY table_name, column_name;

-- b) Só fica uma versão da função, com 4 parâmetros. Deve dar uma linha:
--    registar_pedido_ia | p_user_id uuid, p_desde timestamp with time zone, p_limite integer, p_funcao text DEFAULT NULL::text
-- SELECT p.proname, pg_get_function_arguments(p.oid)
-- FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
-- WHERE n.nspname = 'public' AND p.proname = 'registar_pedido_ia';

-- c) Quem pode chamar a função. Deve dar false, false, true:
-- SELECT has_function_privilege('anon', 'public.registar_pedido_ia(uuid, timestamptz, int, text)', 'EXECUTE') AS anon,
--        has_function_privilege('authenticated', 'public.registar_pedido_ia(uuid, timestamptz, int, text)', 'EXECUTE') AS authenticated,
--        has_function_privilege('service_role', 'public.registar_pedido_ia(uuid, timestamptz, int, text)', 'EXECUTE') AS service_role;

-- d) A tabela resumos_ia tem RLS ligado e nenhuma policy. Deve dar true e 0:
-- SELECT relrowsecurity FROM pg_class WHERE oid = 'public.resumos_ia'::regclass;
-- SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND tablename = 'resumos_ia';

-- e) Na app: fazer uma pergunta no chat. Em Table Editor > uso_ia, a linha nova tem funcao = 'chat';
--    em chamadas_ia, a linha nova tem stop_reason (ex.: end_turn) e os tokens da cache (0).
--    Abrir o dashboard num mês com movimentações: aparece uma linha em resumos_ia; recarregar a página
--    não cria outra linha nem faz subir o contador de pedidos à IA.

-- Consulta útil (não faz parte da migração): pedidos à IA por função nos últimos 30 dias.
-- SELECT coalesce(funcao, '(antes da 016)') AS funcao, count(*) AS pedidos
-- FROM uso_ia
-- WHERE criado_em > now() - interval '30 days'
-- GROUP BY 1
-- ORDER BY pedidos DESC;
