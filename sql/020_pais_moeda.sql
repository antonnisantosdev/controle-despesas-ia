-- Brasil, Fase 1: país onde a pessoa vive, países dos cartões e contas, e moeda principal da conta.
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.
-- Pode correr-se mais do que uma vez sem estragar nada (IF NOT EXISTS, DROP ... IF EXISTS e CREATE OR REPLACE).
--
-- ATENÇÃO: correr ANTES do deploy da API que usa estas colunas.
--   Sem esta migração a API continua a funcionar como hoje (todas as contas PT, EUR, hora de Lisboa):
--   só o PUT /conta/perfil responde 503 e fica um aviso nos logs.
--
-- Nada muda para as contas que já existem: os DEFAULT põem todas em PT / {PT} / EUR,
-- e todas as movimentações e compras antigas ficam em EUR.
--
-- 1. assinaturas.pais: onde a pessoa vive (língua, fuso horário, formatos). Muda-se livremente.
--    assinaturas.paises_bancos: de que países são os cartões e contas (1 ou 2, sem repetidos).
--    assinaturas.moeda: a moeda principal (Fase 1: uma moeda por conta). Tem de ser a de um dos países
--    das contas (EUR para PT, BRL para BR). Só muda enquanto a conta não tiver dados (função do ponto 3).
-- 2. transacoes.moeda e compras.moeda: a moeda de cada movimento e de cada talão. Um gatilho põe sempre
--    a moeda principal da conta, seja qual for o valor enviado (a API também a envia, mas quem manda é a base de dados).
-- 3. Função atualizar_perfil_conta: muda país, países das contas e moeda de uma só vez. Se a moeda mudar
--    e a conta já tiver movimentações, compras, objetivos ou orçamentos, não muda nada e devolve 'tem_dados'.
--    No registo e no 1.º login com o Google (p_so_se_padrao = true) só muda uma conta ainda no perfil padrão
--    (PT / {PT} / EUR) e sem dados; senão não muda nada e devolve 'nao_padrao'.
--
-- Como verificar depois de correr: ver as consultas no fim do ficheiro.


-- === 1. Colunas novas em assinaturas ===

ALTER TABLE public.assinaturas ADD COLUMN IF NOT EXISTS pais TEXT NOT NULL DEFAULT 'PT';
ALTER TABLE public.assinaturas ADD COLUMN IF NOT EXISTS paises_bancos TEXT[] NOT NULL DEFAULT '{PT}';
ALTER TABLE public.assinaturas ADD COLUMN IF NOT EXISTS moeda CHAR(3) NOT NULL DEFAULT 'EUR';

-- As regras (o DROP antes do ADD deixa correr o ficheiro outra vez).
ALTER TABLE public.assinaturas DROP CONSTRAINT IF EXISTS assinaturas_pais_valido;
ALTER TABLE public.assinaturas
    ADD CONSTRAINT assinaturas_pais_valido CHECK (pais IN ('PT', 'BR'));

-- 1 ou 2 países, só da lista, sem NULL e sem repetidos.
-- Só listas simples a começar no índice 1: num array 2D (ex. '{{PT},{BR}}') ou a começar noutro índice
-- (ex. '[0:1]={PT,PT}'), paises_bancos[1] <> paises_bancos[2] dava NULL e o CHECK deixava passar.
ALTER TABLE public.assinaturas DROP CONSTRAINT IF EXISTS assinaturas_paises_bancos_validos;
ALTER TABLE public.assinaturas
    ADD CONSTRAINT assinaturas_paises_bancos_validos CHECK (
        array_ndims(paises_bancos) = 1
        AND array_lower(paises_bancos, 1) = 1
        AND cardinality(paises_bancos) BETWEEN 1 AND 2
        AND array_position(paises_bancos, NULL) IS NULL
        AND paises_bancos <@ ARRAY['PT', 'BR']::TEXT[]
        AND (cardinality(paises_bancos) = 1 OR paises_bancos[1] <> paises_bancos[2])
    );

ALTER TABLE public.assinaturas DROP CONSTRAINT IF EXISTS assinaturas_moeda_valida;
ALTER TABLE public.assinaturas
    ADD CONSTRAINT assinaturas_moeda_valida CHECK (moeda IN ('EUR', 'BRL'));

-- A moeda principal tem de ser a de um dos países das contas (EUR com PT, BRL com BR).
ALTER TABLE public.assinaturas DROP CONSTRAINT IF EXISTS assinaturas_moeda_dos_bancos;
ALTER TABLE public.assinaturas
    ADD CONSTRAINT assinaturas_moeda_dos_bancos CHECK (
        (moeda = 'EUR' AND 'PT' = ANY (paises_bancos))
        OR (moeda = 'BRL' AND 'BR' = ANY (paises_bancos))
    );


-- === 2. Moeda de cada movimento e de cada compra ===

ALTER TABLE public.transacoes ADD COLUMN IF NOT EXISTS moeda CHAR(3) NOT NULL DEFAULT 'EUR';
ALTER TABLE public.transacoes DROP CONSTRAINT IF EXISTS transacoes_moeda_valida;
ALTER TABLE public.transacoes
    ADD CONSTRAINT transacoes_moeda_valida CHECK (moeda IN ('EUR', 'BRL'));

ALTER TABLE public.compras ADD COLUMN IF NOT EXISTS moeda CHAR(3) NOT NULL DEFAULT 'EUR';
ALTER TABLE public.compras DROP CONSTRAINT IF EXISTS compras_moeda_valida;
ALTER TABLE public.compras
    ADD CONSTRAINT compras_moeda_valida CHECK (moeda IN ('EUR', 'BRL'));

-- Gatilho: cada movimento e cada compra novos ficam com a moeda principal da conta (nunca a do pedido).
-- FOR SHARE: se a função do ponto 3 estiver a mudar a moeda desta conta, o INSERT espera que acabe
-- (e grava já a moeda nova); se o INSERT vier primeiro, é a função que espera e depois vê o movimento.
-- Assim nunca fica um movimento numa moeda e a conta noutra.
-- SECURITY INVOKER e search_path vazio, como as funções da 015 e da 017.
CREATE OR REPLACE FUNCTION public.moeda_principal_no_movimento()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_moeda CHAR(3);
BEGIN
    SELECT a.moeda INTO v_moeda
    FROM public.assinaturas a
    WHERE a.user_id = NEW.user_id
    FOR SHARE;

    -- Sem assinatura (não devia acontecer: a API recusa estas contas) fica o DEFAULT da coluna.
    IF v_moeda IS NOT NULL THEN
        NEW.moeda := v_moeda;
    END IF;
    RETURN NEW;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.moeda_principal_no_movimento() FROM PUBLIC, anon, authenticated;

DROP TRIGGER IF EXISTS transacoes_moeda_principal ON public.transacoes;
CREATE TRIGGER transacoes_moeda_principal
    BEFORE INSERT OR UPDATE OF moeda ON public.transacoes
    FOR EACH ROW EXECUTE FUNCTION public.moeda_principal_no_movimento();

DROP TRIGGER IF EXISTS compras_moeda_principal ON public.compras;
CREATE TRIGGER compras_moeda_principal
    BEFORE INSERT OR UPDATE OF moeda ON public.compras
    FOR EACH ROW EXECUTE FUNCTION public.moeda_principal_no_movimento();


-- === 3. Função atualizar_perfil_conta ===

-- Muda o país, os países das contas e a moeda principal de uma conta, de uma só vez.
--   Devolve 'ok' se mudou; 'tem_dados' se a moeda ia mudar e a conta já tem movimentações, compras,
--   objetivos ou orçamentos (não muda nada, a API responde 409); 'sem_conta' se não há linha em assinaturas.
--   Valores inválidos ou incoerentes (ex.: BRL só com bancos PT) são recusados pelos CHECK acima.
--
-- p_so_se_padrao (o registo e o 1.º login com o Google mandam true; as definições, false): só muda se a conta
--   ainda estiver no perfil padrão (PT / {PT} / EUR) e sem dados; senão não muda nada e devolve 'nao_padrao'.
--   Assim um registo repetido ou um login tardio nunca desfaz o que a pessoa já escolheu nas definições.
--   NULL conta como true (na dúvida, não se muda nada).
--
-- Atómica: o FOR UPDATE prende a linha da assinatura até ao fim, e o gatilho dos movimentos espera por ela
-- (ver ponto 2). A verificação dos dados é uma instrução à parte, depois do FOR UPDATE: em READ COMMITTED
-- vê já um movimento gravado enquanto esperava.
--
-- SECURITY INVOKER (e não DEFINER), como a registar_pedido_ia (015) e a registar_pdf_ia (017): corre com as
-- permissões da API (chave secreta), por isso não dá a ninguém mais poder do que já tem. Com DEFINER, se a
-- função escapasse ao REVOKE, mudava a moeda de qualquer user_id. search_path vazio e nomes completos.
-- A versão antiga (sem p_so_se_padrao) tem outra assinatura: o CREATE OR REPLACE criava uma segunda função
-- ao lado dela, e a antiga continuava a poder ser chamada. Apaga-se primeiro.
DROP FUNCTION IF EXISTS public.atualizar_perfil_conta(uuid, text, text[], text);

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
    SET pais = p_pais, paises_bancos = p_paises_bancos, moeda = p_moeda
    WHERE user_id = p_user_id;
    RETURN 'ok';
END;
$$;

-- Só a API a pode chamar (como na 015 e na 017).
REVOKE EXECUTE ON FUNCTION public.atualizar_perfil_conta(uuid, text, text[], text, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.atualizar_perfil_conta(uuid, text, text[], text, boolean) TO service_role;

-- Pede à API do Supabase (PostgREST) para ver já as colunas e a função novas.
NOTIFY pgrst, 'reload schema';


-- === Como verificar (não faz parte da migração: correr à parte, depois) ===

-- a) As colunas novas. Deve dar 5 linhas (assinaturas: moeda, pais, paises_bancos; compras e transacoes: moeda):
-- SELECT table_name, column_name, data_type, column_default FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND ((table_name = 'assinaturas' AND column_name IN ('pais', 'paises_bancos', 'moeda'))
--     OR (table_name IN ('transacoes', 'compras') AND column_name = 'moeda'))
-- ORDER BY table_name, column_name;

-- b) Todas as contas que já existiam ficaram PT / {PT} / EUR. Deve dar uma só linha: PT | {PT} | EUR | (todas)
-- SELECT pais, paises_bancos, moeda, count(*) FROM assinaturas GROUP BY 1, 2, 3;

-- c) Todos os movimentos e compras antigos em EUR. Deve dar só EUR:
-- SELECT moeda, count(*) FROM transacoes GROUP BY 1;
-- SELECT moeda, count(*) FROM compras GROUP BY 1;

-- d) Quem pode chamar a função. Deve dar false, false, true:
-- SELECT has_function_privilege('anon', 'public.atualizar_perfil_conta(uuid, text, text[], text, boolean)', 'EXECUTE') AS anon,
--        has_function_privilege('authenticated', 'public.atualizar_perfil_conta(uuid, text, text[], text, boolean)', 'EXECUTE') AS authenticated,
--        has_function_privilege('service_role', 'public.atualizar_perfil_conta(uuid, text, text[], text, boolean)', 'EXECUTE') AS service_role;

-- e) Os gatilhos existem. Deve dar 2 linhas (compras_moeda_principal, transacoes_moeda_principal):
-- SELECT tgname FROM pg_trigger WHERE tgname IN ('transacoes_moeda_principal', 'compras_moeda_principal') ORDER BY 1;

-- f) A regra da moeda (numa conta de TESTE com movimentações, trocar o id). Deve dar 'tem_dados' e não mudar nada:
-- SELECT public.atualizar_perfil_conta('00000000-0000-0000-0000-000000000000', 'BR', '{BR}', 'BRL', false);

-- g) Só existe a versão nova da função (com p_so_se_padrao). Deve dar uma só linha, a acabar em "boolean":
-- SELECT oid::regprocedure FROM pg_proc WHERE proname = 'atualizar_perfil_conta';

-- h) O registo não desfaz o perfil (numa conta de TESTE que já não esteja em PT / {PT} / EUR, ou com dados).
--    Deve dar 'nao_padrao' e não mudar nada:
-- SELECT public.atualizar_perfil_conta('00000000-0000-0000-0000-000000000000', 'BR', '{BR}', 'BRL', true);

-- i) A regra dos países das contas recusa arrays 2D e índices que não começam em 1. Cada linha deve dar
--    o erro "violates check constraint assinaturas_paises_bancos_validos" (numa conta de TESTE, trocar o id):
-- UPDATE assinaturas SET paises_bancos = '{{PT},{BR}}' WHERE user_id = '00000000-0000-0000-0000-000000000000';
-- UPDATE assinaturas SET paises_bancos = '[0:1]={PT,PT}' WHERE user_id = '00000000-0000-0000-0000-000000000000';
