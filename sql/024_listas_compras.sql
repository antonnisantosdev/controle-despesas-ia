-- 024: "Fazer as minhas compras": contador das listas de compras de cada mês, sem "corridas".
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.
-- Pode correr-se mais do que uma vez sem estragar nada (IF NOT EXISTS e CREATE OR REPLACE).
--
-- ATENÇÃO: correr ANTES do deploy. Sem esta migração, o POST /compras/lista responde 503 (falha fechada:
-- não se sabe quantas listas a conta já fez, por isso não se chama a IA nem se pagam pesquisas).
--
-- Cada lista de compras custa duas chamadas à IA e várias pesquisas na web (pagas à parte), por isso tem um
-- limite próprio por mês (limites.LIMITES_LISTAS_COMPRAS_POR_PLANO: Essencial 5, Completo 15).
-- Não gasta os pedidos à IA normais: conta-se nesta tabela, e não na uso_ia.
--
-- 1. Tabela uso_listas_compras: uma linha por lista pedida (só o dono e a hora; nem a lista, nem os mercados).
--    RLS ligado e sem policies: só a API (chave secreta) lê e escreve.
-- 2. Função registar_lista_compras: conta as listas do mês e só regista se houver espaço, de uma só vez.
--    Usa o MESMO cadeado da registar_pedido_ia e da registar_pdf_ia (015/016/017): duas listas da mesma conta
--    pedidas ao mesmo tempo esperam uma pela outra, e o contador não passa o limite.
--
-- Como verificar depois de correr: ver as consultas no fim do ficheiro.


-- === 1. Tabela uso_listas_compras ===

CREATE TABLE IF NOT EXISTS public.uso_listas_compras (
    id BIGSERIAL PRIMARY KEY,
    -- Ao apagar a conta, as linhas dela vão também.
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A contagem do mês procura sempre por utilizador e data.
CREATE INDEX IF NOT EXISTS uso_listas_compras_user_criado_idx
    ON public.uso_listas_compras (user_id, criado_em);

-- Só a API (chave secreta) lê e escreve: RLS ligado, sem policies, e sem permissões para quem vem do browser.
ALTER TABLE public.uso_listas_compras ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.uso_listas_compras FROM anon, authenticated;
REVOKE ALL ON SEQUENCE public.uso_listas_compras_id_seq FROM anon, authenticated;


-- === 2. Função registar_lista_compras ===

-- Regista uma lista de compras se o utilizador ainda tiver listas no mês.
--   p_user_id: o utilizador.
--   p_desde: o início do mês (no país da conta, ver limites.inicio_dos_contadores) em UTC.
--   p_limite: listas por mês do plano.
--   Devolve 'ok' se registou, 'limite' se já chegou ao limite do mês (a API responde 429).
--
-- SECURITY INVOKER e search_path vazio, como a registar_pdf_ia (ver a explicação na 015).
CREATE OR REPLACE FUNCTION public.registar_lista_compras(
    p_user_id uuid,
    p_desde timestamptz,
    p_limite int
)
RETURNS text
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_listas int;
BEGIN
    -- O mesmo cadeado da registar_pedido_ia e da registar_pdf_ia: um segundo pedido da mesma conta
    -- espera aqui até o primeiro acabar, e só então conta (já com o do primeiro incluído).
    PERFORM pg_advisory_xact_lock(hashtext(p_user_id::text));

    SELECT count(*) INTO v_listas
    FROM public.uso_listas_compras
    WHERE user_id = p_user_id
      AND criado_em >= p_desde;

    IF v_listas >= p_limite THEN
        RETURN 'limite';
    END IF;

    INSERT INTO public.uso_listas_compras (user_id) VALUES (p_user_id);
    RETURN 'ok';
END;
$$;

-- Só a API a pode chamar (como na 015, 016 e 017).
REVOKE EXECUTE ON FUNCTION public.registar_lista_compras(uuid, timestamptz, int) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.registar_lista_compras(uuid, timestamptz, int) TO service_role;

-- Pede à API do Supabase (PostgREST) para ver já a tabela e a função novas.
NOTIFY pgrst, 'reload schema';


-- === Como verificar (não faz parte da migração: correr à parte, depois) ===

-- a) RLS ligado e sem policies na tabela nova. Deve dar true e 0:
-- SELECT relrowsecurity FROM pg_class WHERE oid = 'public.uso_listas_compras'::regclass;
-- SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND tablename = 'uso_listas_compras';

-- b) A função existe, com 3 parâmetros. Deve dar uma linha:
--    registar_lista_compras | p_user_id uuid, p_desde timestamp with time zone, p_limite integer
-- SELECT p.proname, pg_get_function_arguments(p.oid)
-- FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
-- WHERE n.nspname = 'public' AND p.proname = 'registar_lista_compras';

-- c) Quem pode chamar a função. Deve dar false, false, true:
-- SELECT has_function_privilege('anon', 'public.registar_lista_compras(uuid, timestamptz, int)', 'EXECUTE') AS anon,
--        has_function_privilege('authenticated', 'public.registar_lista_compras(uuid, timestamptz, int)', 'EXECUTE') AS authenticated,
--        has_function_privilege('service_role', 'public.registar_lista_compras(uuid, timestamptz, int)', 'EXECUTE') AS service_role;

-- d) Na app (conta de TESTE num plano pago, a viver em Portugal): fazer uma lista de compras. Em Table Editor >
--    uso_listas_compras aparece uma linha nova, e o contador da página sobe um. A uso_ia não muda.

-- e) Listas por conta neste mês (para ver o uso e o custo):
-- SELECT user_id, count(*) FROM uso_listas_compras
-- WHERE criado_em >= date_trunc('month', now() AT TIME ZONE 'Europe/Lisbon') AT TIME ZONE 'Europe/Lisbon'
-- GROUP BY 1 ORDER BY 2 DESC;
