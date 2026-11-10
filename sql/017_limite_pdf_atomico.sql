-- Limite de extratos PDF por mês sem "corridas".
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.
-- Precisa da 016 já corrida (usa a coluna uso_ia.funcao).
-- Pode correr-se mais do que uma vez sem estragar nada (CREATE OR REPLACE).
--
-- Até agora a API via primeiro os PDF do mês (limites.exigir_limite_pdf) e só depois registava o pedido
-- (registar_pedido_ia), em dois passos: vários PDF enviados ao mesmo tempo podiam ver todos "14 de 15"
-- e passar o limite de PDF. A função registar_pdf_ia faz tudo de uma vez: conta os PDF do mês e os
-- pedidos do período e só regista o pedido (funcao = 'importar_pdf') se os dois estiverem abaixo do limite.
--
-- Usa o MESMO cadeado da registar_pedido_ia (015/016): um PDF e uma pergunta do chat da mesma conta
-- feitos ao mesmo tempo também esperam um pelo outro, e o contador de pedidos não passa o limite.
-- A registar_pedido_ia não muda.
--
-- Enquanto esta migração não for corrida, a API usa o caminho antigo (limites.py) e deixa um aviso nos logs.
--
-- Como verificar depois de correr: ver as consultas no fim do ficheiro.


-- === Função registar_pdf_ia ===

-- Regista a leitura de um PDF (um pedido à IA com funcao = 'importar_pdf') se o utilizador ainda tiver
-- PDF e pedidos no plano, e diz qual limite falhou.
--   p_user_id: o utilizador.
--   p_desde_pedidos / p_limite_pedidos: início do dia (ou do mês, no Free) de Lisboa em UTC, e pedidos do plano.
--   p_desde_pdf / p_limite_pdf: início do mês de Lisboa em UTC, e PDF por mês do plano.
--   Devolve 'ok' se registou, 'pdf' se já chegou ao limite de PDF do mês, 'pedidos' se já chegou ao
--   limite de pedidos à IA (a API responde 429 com a mensagem certa). O limite de PDF vê-se primeiro,
--   como fazia a API.
--
-- SECURITY INVOKER e search_path vazio, como a registar_pedido_ia (ver a explicação na 015).
CREATE OR REPLACE FUNCTION public.registar_pdf_ia(
    p_user_id uuid,
    p_desde_pedidos timestamptz,
    p_limite_pedidos int,
    p_desde_pdf timestamptz,
    p_limite_pdf int
)
RETURNS text
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_pdfs int;
    v_pedidos int;
BEGIN
    -- O mesmo cadeado da registar_pedido_ia: um segundo pedido da mesma conta (PDF ou outro) espera
    -- aqui até o primeiro acabar, e só então conta (já com o do primeiro incluído).
    PERFORM pg_advisory_xact_lock(hashtext(p_user_id::text));

    SELECT count(*) INTO v_pdfs
    FROM public.uso_ia
    WHERE user_id = p_user_id
      AND funcao = 'importar_pdf'
      AND criado_em >= p_desde_pdf;

    IF v_pdfs >= p_limite_pdf THEN
        RETURN 'pdf';
    END IF;

    SELECT count(*) INTO v_pedidos
    FROM public.uso_ia
    WHERE user_id = p_user_id
      AND criado_em >= p_desde_pedidos;

    IF v_pedidos >= p_limite_pedidos THEN
        RETURN 'pedidos';
    END IF;

    INSERT INTO public.uso_ia (user_id, funcao) VALUES (p_user_id, 'importar_pdf');
    RETURN 'ok';
END;
$$;

-- Só a API a pode chamar (como na 015 e na 016).
REVOKE EXECUTE ON FUNCTION public.registar_pdf_ia(uuid, timestamptz, int, timestamptz, int) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.registar_pdf_ia(uuid, timestamptz, int, timestamptz, int) TO service_role;

-- Pede à API do Supabase (PostgREST) para ver já a função nova.
NOTIFY pgrst, 'reload schema';


-- === Como verificar (não faz parte da migração: correr à parte, depois) ===

-- a) A função existe, com 5 parâmetros. Deve dar uma linha:
--    registar_pdf_ia | p_user_id uuid, p_desde_pedidos timestamp with time zone, p_limite_pedidos integer, p_desde_pdf timestamp with time zone, p_limite_pdf integer
-- SELECT p.proname, pg_get_function_arguments(p.oid)
-- FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
-- WHERE n.nspname = 'public' AND p.proname = 'registar_pdf_ia';

-- b) Quem pode chamar a função. Deve dar false, false, true:
-- SELECT has_function_privilege('anon', 'public.registar_pdf_ia(uuid, timestamptz, int, timestamptz, int)', 'EXECUTE') AS anon,
--        has_function_privilege('authenticated', 'public.registar_pdf_ia(uuid, timestamptz, int, timestamptz, int)', 'EXECUTE') AS authenticated,
--        has_function_privilege('service_role', 'public.registar_pdf_ia(uuid, timestamptz, int, timestamptz, int)', 'EXECUTE') AS service_role;

-- c) Na app (conta de teste num plano pago): importar um extrato PDF inventado. Em Table Editor > uso_ia
--    aparece uma linha nova com funcao = 'importar_pdf', e o contador de PDF do menu lateral sobe um.
--    Nos logs do Render NÃO deve aparecer "AVISO: função registar_pdf_ia não encontrada".
