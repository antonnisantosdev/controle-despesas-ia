-- Planos: cada assinatura passa a ter um plano, e o plano decide quantas perguntas à IA se podem fazer por dia.
-- Os limites de cada plano estão no limites.py (LIMITES_POR_PLANO), não aqui.
-- Para mudar o plano de alguém: Supabase > Table Editor > assinaturas > coluna plano.
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.

-- 1. As contas que já existem ficam no Essencial (o DEFAULT preenche as linhas antigas).
--    O CHECK recusa qualquer outro valor, como um erro de escrita ("completto").
ALTER TABLE assinaturas
    ADD COLUMN plano TEXT NOT NULL DEFAULT 'essencial'
    CHECK (plano IN ('free', 'essencial', 'completo'));

-- 2. Para confirmar: cada utilizador, o plano e até quando tem acesso.
-- SELECT u.email, a.plano, a.ativo_ate
-- FROM assinaturas a JOIN auth.users u ON u.id = a.user_id;
