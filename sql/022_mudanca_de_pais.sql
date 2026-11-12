-- 022: quando a conta mudou de país pela última vez (assinaturas.pais_mudado_em).
--
-- Porquê: os contadores de pedidos à IA e de PDF contavam sempre desde o início mais antigo entre Lisboa e
-- São Paulo (para mudar de país não dar pedidos a mais). Isso deixava as contas PT presas até 3-4 h depois
-- da meia-noite. Com esta coluna, cada conta conta no fuso do seu país, e só no período em que mudou de
-- país se conta desde o início mais antigo (limites.py, inicio_dos_contadores).
--
-- 1. Coluna pais_mudado_em (NULL = nunca mudou).
-- 2. A função atualizar_perfil_conta (sql/020) passa a escrevê-la quando o país muda, na mesma transação.
--    Mesma assinatura, mesmas permissões (só a service_role).
--
-- Correr no Supabase (SQL Editor) ANTES do deploy da API. Pode correr-se mais do que uma vez.

-- === 1. Coluna ===
ALTER TABLE public.assinaturas ADD COLUMN IF NOT EXISTS pais_mudado_em TIMESTAMPTZ;

-- Contas que já vivem fora de Portugal podem ter mudado de país há pouco (antes desta coluna existir):
-- contam como mudança agora, para o período de hoje (ou o mês do Free) não ficar mais curto.
UPDATE public.assinaturas SET pais_mudado_em = now() WHERE pais <> 'PT' AND pais_mudado_em IS NULL;

-- === 2. Função atualizar_perfil_conta (igual à da sql/020, mais a data da mudança de país) ===
CREATE OR REPLACE FUNCTION public.atualizar_perfil_conta(
    p_user_id uuid,
    p_pais text,
    p_paises_bancos text[],
    p_moeda text,
    p_so_se_padrao boolean DEFAULT false
)
RETURNS text
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_pais TEXT;
    v_bancos TEXT[];
    v_moeda CHAR(3);
    v_tem_dados BOOLEAN;
BEGIN
    SELECT a.pais, a.paises_bancos, a.moeda INTO v_pais, v_bancos, v_moeda
    FROM public.assinaturas a
    WHERE a.user_id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN 'sem_conta';
    END IF;

    v_tem_dados := EXISTS (SELECT 1 FROM public.transacoes t WHERE t.user_id = p_user_id)
        OR EXISTS (SELECT 1 FROM public.compras c WHERE c.user_id = p_user_id)
        OR EXISTS (SELECT 1 FROM public.objetivos o WHERE o.user_id = p_user_id)
        OR EXISTS (SELECT 1 FROM public.orcamentos r WHERE r.user_id = p_user_id);

    IF p_so_se_padrao IS NOT FALSE AND (
        v_pais IS DISTINCT FROM 'PT'
        OR v_bancos IS DISTINCT FROM ARRAY['PT']::TEXT[]
        OR v_moeda IS DISTINCT FROM 'EUR'
        OR v_tem_dados
    ) THEN
        RETURN 'nao_padrao';
    END IF;

    IF v_moeda IS DISTINCT FROM p_moeda AND v_tem_dados THEN
        RETURN 'tem_dados';
    END IF;

    UPDATE public.assinaturas
    SET pais = p_pais,
        paises_bancos = p_paises_bancos,
        moeda = p_moeda,
        -- Só quando o país muda: o resto do perfil não mexe nos contadores.
        pais_mudado_em = CASE WHEN v_pais IS DISTINCT FROM p_pais THEN now() ELSE pais_mudado_em END
    WHERE user_id = p_user_id;
    RETURN 'ok';
END;
$$;

REVOKE EXECUTE ON FUNCTION public.atualizar_perfil_conta(uuid, text, text[], text, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.atualizar_perfil_conta(uuid, text, text[], text, boolean) TO service_role;

-- === Verificação (correr depois; deve dar uma linha com pais_mudado_em) ===
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_schema = 'public' AND table_name = 'assinaturas' AND column_name = 'pais_mudado_em';
--
-- Permissões da função (esperado: anon false, authenticated false, service_role true):
-- SELECT has_function_privilege('anon', 'public.atualizar_perfil_conta(uuid, text, text[], text, boolean)', 'EXECUTE') AS anon,
--        has_function_privilege('authenticated', 'public.atualizar_perfil_conta(uuid, text, text[], text, boolean)', 'EXECUTE') AS authenticated,
--        has_function_privilege('service_role', 'public.atualizar_perfil_conta(uuid, text, text[], text, boolean)', 'EXECUTE') AS service_role;
