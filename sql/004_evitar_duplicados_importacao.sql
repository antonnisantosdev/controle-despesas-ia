-- Evita que o mesmo extrato importado duas vezes crie transações repetidas.
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.

-- "Impressão digital" de cada linha do extrato, calculada pela API ao importar.
-- Transações criadas à mão (POST /transacoes) ficam com NULL, e isso não conta como repetido.
ALTER TABLE transacoes
    ADD COLUMN hash_importacao TEXT;

-- O mesmo utilizador não pode ter duas transações com a mesma impressão digital.
-- (Utilizadores diferentes podem, porque cada um importa os seus extratos.)
ALTER TABLE transacoes
    ADD CONSTRAINT transacoes_user_hash_unico UNIQUE (user_id, hash_importacao);
