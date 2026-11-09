-- Cada chamada à IA passa a guardar de quem foi (user_id): assim sabe-se quanto custa cada utilizador,
-- e se o preço de cada plano cobre o que esse plano gasta.
-- A API já envia o user_id; enquanto esta migração não for corrida, grava a chamada sem ele (ia.py).
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.

-- 1. A coluna é opcional: as chamadas antigas e as do script de avaliação ficam sem utilizador.
--    Se a conta for apagada, as chamadas ficam (sem dono) para as contas de custos continuarem certas.
ALTER TABLE chamadas_ia
    ADD COLUMN IF NOT EXISTS user_id UUID NULL REFERENCES auth.users (id) ON DELETE SET NULL;

-- 2. As consultas de custos por utilizador filtram pelo utilizador e pela data.
CREATE INDEX IF NOT EXISTS chamadas_ia_utilizador_data ON chamadas_ia (user_id, criado_em);

-- O RLS fica como na 011: ligado e sem políticas, só a API (chave secreta) lê e escreve.

-- Consulta útil (não faz parte da migração): custo por utilizador nos últimos 30 dias, com o plano.
-- SELECT u.email,
--        a.plano,
--        count(*) AS chamadas,
--        round(sum(c.custo_usd), 4) AS custo_total_usd
-- FROM chamadas_ia c
-- JOIN auth.users u ON u.id = c.user_id
-- LEFT JOIN assinaturas a ON a.user_id = c.user_id
-- WHERE c.origem = 'app' AND c.criado_em > now() - interval '30 days'
-- GROUP BY u.email, a.plano
-- ORDER BY custo_total_usd DESC;
