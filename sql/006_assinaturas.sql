-- Assinaturas manuais: cada utilizador tem acesso até uma data.
-- Quando alguém paga mais um mês (MB Way), muda-se o ativo_ate aqui no Supabase (Table Editor).
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.

-- 1. Uma linha por utilizador. Se o utilizador for apagado, a assinatura também é.
CREATE TABLE assinaturas (
    user_id UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    ativo_ate DATE NOT NULL,
    notas TEXT,  -- por exemplo: "pago por MB Way em 2026-11-03"
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. RLS ligado e sem políticas: só a API (com a chave secreta) lê e escreve esta tabela.
--    O frontend nunca lhe toca diretamente, por isso ninguém consegue "oferecer-se" mais meses.
ALTER TABLE assinaturas ENABLE ROW LEVEL SECURITY;

-- 3. O utilizador de teste fica com acesso até ao fim do ano.
INSERT INTO assinaturas (user_id, ativo_ate, notas)
SELECT id, '2026-12-31', 'utilizador de teste'
FROM auth.users
WHERE email = 'teste@exemplo.com';
