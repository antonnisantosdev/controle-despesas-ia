-- Liga cada transação a um utilizador e protege a tabela com políticas RLS.
-- Antes de correr: cria o utilizador de teste em Authentication > Users > Add user,
-- com o email teste@exemplo.com (ou muda o email no UPDATE abaixo).
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.

-- 1. Nova coluna: a quem pertence a transação.
--    auth.users é a tabela de utilizadores que o Supabase gere sozinho.
--    ON DELETE CASCADE: se o utilizador for apagado, as transações dele também são.
ALTER TABLE transacoes
    ADD COLUMN user_id UUID REFERENCES auth.users (id) ON DELETE CASCADE;

-- 2. As 5 transações de teste passam a pertencer ao utilizador de teste.
UPDATE transacoes
SET user_id = (SELECT id FROM auth.users WHERE email = 'teste@exemplo.com');

-- 3. A partir de agora, nenhuma transação pode ficar sem dono.
ALTER TABLE transacoes
    ALTER COLUMN user_id SET NOT NULL;

-- 4. Políticas RLS: cada utilizador só mexe nas suas próprias linhas.
--    auth.uid() devolve o id de quem fez login.

-- Ler: só vê as linhas em que é o dono.
CREATE POLICY "Utilizador vê as suas transações"
    ON transacoes FOR SELECT
    USING (auth.uid() = user_id);

-- Criar: só pode criar transações em seu próprio nome.
CREATE POLICY "Utilizador cria as suas transações"
    ON transacoes FOR INSERT
    WITH CHECK (auth.uid() = user_id);
