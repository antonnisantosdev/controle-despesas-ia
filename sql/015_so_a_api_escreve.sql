-- Fecha dois riscos baixos que ficaram em aberto na revisão de segurança.
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.
-- Pode correr-se mais do que uma vez sem estragar nada (DROP ... IF EXISTS e CREATE OR REPLACE).
--
-- 1. Só a API escreve nas tabelas.
--    A API usa a chave secreta (SUPABASE_KEY = Secret key, sb_secret_...), que passa por cima do RLS.
--    A policy de INSERT da 003 já não faz falta à API, mas deixava qualquer pessoa com login criar
--    movimentações diretamente no Supabase (com o token do login e a chave pública), sem passar
--    pela API: sem o teto de 20 000 movimentações e sem as regras do plano.
--    Nas migrações, esta é a única policy de escrita (INSERT, UPDATE ou DELETE) em todas as tabelas.
--    As outras tabelas (assinaturas, uso_ia, orcamentos, compras, compra_itens, objetivos, chamadas_ia)
--    já têm RLS ligado e nenhuma policy: só a API lhes toca.
--
-- 2. Contador de pedidos à IA sem "corridas".
--    Até agora a API contava os pedidos e só depois inseria, em dois passos: vários pedidos ao mesmo
--    tempo podiam ver todos "29 de 30" e passar o limite. A função registar_pedido_ia faz as duas
--    coisas de uma vez, com um cadeado por utilizador (como um LOCK do MySQL, mas só para essa conta).
--    Enquanto esta migração não for corrida, a API usa o caminho antigo (limites.py) e não parte.
--
-- Como verificar depois de correr: ver as consultas no fim do ficheiro.


-- === 1. Policies de escrita ===

-- Apaga a policy de INSERT de transacoes (criada na 003).
DROP POLICY IF EXISTS "Utilizador cria as suas transações" ON public.transacoes;

-- A policy de SELECT da 003 ("Utilizador vê as suas transações") FICA.
-- Hoje ninguém a usa (o frontend não usa o cliente do Supabase e a API passa por cima do RLS),
-- mas não abre nada de novo: cada pessoa só vê as suas movimentações, que já vê na app.
-- Se um dia se quiser fechar também a leitura direta, basta:
-- DROP POLICY IF EXISTS "Utilizador vê as suas transações" ON public.transacoes;


-- === 2. Função registar_pedido_ia ===

-- Regista um pedido à IA se o utilizador ainda estiver abaixo do limite, e diz se registou.
--   p_user_id: o utilizador; p_desde: início do dia ou do mês de Lisboa, em UTC; p_limite: pedidos do plano.
--   Devolve true se registou o pedido, false se já tinha chegado ao limite (a API responde 429).
--
-- SECURITY INVOKER: a função corre com as permissões de quem a chama (a API, com a chave secreta).
--   Com DEFINER correria como o dono e, se alguém a conseguisse chamar, gastava pedidos em nome de
--   qualquer user_id. Com INVOKER, mesmo nesse caso o RLS da uso_ia (sem policies) bloqueava.
-- search_path vazio + nomes completos (public.uso_ia): ninguém consegue trocar a tabela por outra.
CREATE OR REPLACE FUNCTION public.registar_pedido_ia(p_user_id uuid, p_desde timestamptz, p_limite int)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_pedidos int;
BEGIN
    -- Cadeado deste utilizador até ao fim da transação: um segundo pedido da mesma conta espera
    -- aqui até o primeiro acabar, e só então conta (já com o pedido do primeiro incluído).
    -- Contas diferentes não esperam umas pelas outras.
    PERFORM pg_advisory_xact_lock(hashtext(p_user_id::text));

    SELECT count(*) INTO v_pedidos
    FROM public.uso_ia
    WHERE user_id = p_user_id
      AND criado_em >= p_desde;

    IF v_pedidos >= p_limite THEN
        RETURN false;
    END IF;

    INSERT INTO public.uso_ia (user_id) VALUES (p_user_id);
    RETURN true;
END;
$$;

-- Só a API a pode chamar. No Postgres, qualquer função nova pode ser chamada por todos (PUBLIC),
-- e o Supabase dá-a também a anon e authenticated: tira-se a todos e dá-se só à chave secreta.
REVOKE EXECUTE ON FUNCTION public.registar_pedido_ia(uuid, timestamptz, int) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.registar_pedido_ia(uuid, timestamptz, int) TO service_role;

-- Pede à API do Supabase (PostgREST) para ver já a função nova.
NOTIFY pgrst, 'reload schema';


-- === Como verificar (não faz parte da migração: correr à parte, depois) ===

-- a) Policies que sobram em todas as tabelas. Deve aparecer só uma linha:
--    transacoes | Utilizador vê as suas transações | SELECT
-- SELECT tablename, policyname, cmd
-- FROM pg_policies
-- WHERE schemaname = 'public'
-- ORDER BY tablename, cmd;

-- b) Quem pode chamar a função. Deve dar false, false, true:
-- SELECT has_function_privilege('anon', 'public.registar_pedido_ia(uuid, timestamptz, int)', 'EXECUTE') AS anon,
--        has_function_privilege('authenticated', 'public.registar_pedido_ia(uuid, timestamptz, int)', 'EXECUTE') AS authenticated,
--        has_function_privilege('service_role', 'public.registar_pedido_ia(uuid, timestamptz, int)', 'EXECUTE') AS service_role;

-- c) Na app: fazer uma pergunta no chat. Em Table Editor > uso_ia deve aparecer uma linha nova,
--    e o contador do menu lateral deve subir um.
