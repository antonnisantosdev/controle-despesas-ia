-- Cria a tabela de transações no Supabase (PostgreSQL).
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.
-- Os campos seguem o modelo Transacao do main.py.

CREATE TABLE transacoes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data DATE NOT NULL,
    descricao TEXT NOT NULL,
    valor NUMERIC(12, 2) NOT NULL,
    categoria TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Segurança: sem políticas, ninguém lê nem escreve através das chaves públicas.
-- As políticas por utilizador vêm no passo do login.
ALTER TABLE transacoes ENABLE ROW LEVEL SECURITY;
