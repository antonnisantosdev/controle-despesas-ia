-- 023: objetivos e orçamentos novos esperam por uma mudança de moeda em curso (como as movimentações e as compras).
--
-- Porquê: a função atualizar_perfil_conta (sql/020, sql/022) só muda a moeda se a conta não tiver dados.
-- Prende a linha da assinatura (FOR UPDATE) e depois vê se há movimentações, compras, objetivos ou orçamentos.
-- As movimentações e as compras já esperam por esse FOR UPDATE (gatilho moeda_principal_no_movimento, 020).
-- Os objetivos e os orçamentos não: um objetivo gravado no mesmo instante podia ficar de fora da verificação,
-- e a conta mudava de moeda com um objetivo escrito na moeda antiga. Risco baixo (precisa de dois pedidos
-- quase ao mesmo tempo), mas fecha-se igual aos outros.
--
-- 1. Função espera_perfil_conta: só lê a linha da assinatura com FOR SHARE (espera se estiver a mudar).
--    Não muda nada na linha nova (objetivos e orçamentos não têm coluna moeda).
-- 2. Gatilhos BEFORE INSERT em objetivos e orcamentos.
--
-- Correr no Supabase (SQL Editor). Não precisa de deploy da API. Pode correr-se mais do que uma vez.
-- Precisa da 020 já corrida.


-- === 1. Função ===
-- SECURITY INVOKER e search_path vazio, como a moeda_principal_no_movimento (020).
CREATE OR REPLACE FUNCTION public.espera_perfil_conta()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
    PERFORM 1
    FROM public.assinaturas a
    WHERE a.user_id = NEW.user_id
    FOR SHARE;
    RETURN NEW;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.espera_perfil_conta() FROM PUBLIC, anon, authenticated;


-- === 2. Gatilhos ===
DROP TRIGGER IF EXISTS objetivos_espera_perfil ON public.objetivos;
CREATE TRIGGER objetivos_espera_perfil
    BEFORE INSERT ON public.objetivos
    FOR EACH ROW EXECUTE FUNCTION public.espera_perfil_conta();

DROP TRIGGER IF EXISTS orcamentos_espera_perfil ON public.orcamentos;
CREATE TRIGGER orcamentos_espera_perfil
    BEFORE INSERT ON public.orcamentos
    FOR EACH ROW EXECUTE FUNCTION public.espera_perfil_conta();


-- === Como verificar (não faz parte da migração: correr à parte, depois) ===

-- a) Os gatilhos existem. Deve dar 2 linhas (objetivos_espera_perfil, orcamentos_espera_perfil):
-- SELECT tgname FROM pg_trigger WHERE tgname IN ('objetivos_espera_perfil', 'orcamentos_espera_perfil') ORDER BY 1;

-- b) Ninguém de fora chama a função diretamente. Deve dar false, false:
-- SELECT has_function_privilege('anon', 'public.espera_perfil_conta()', 'EXECUTE') AS anon,
--        has_function_privilege('authenticated', 'public.espera_perfil_conta()', 'EXECUTE') AS authenticated;

-- c) Criar um objetivo e um orçamento na app (conta de TESTE) continua a funcionar como antes.
