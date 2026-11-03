-- Orçamento mensal por categoria: "quero gastar no máximo X € por mês em Y".
-- O mesmo limite vale para todos os meses, até o utilizador o mudar.
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.

CREATE TABLE orcamentos (
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    categoria TEXT NOT NULL,
    limite NUMERIC(12, 2) NOT NULL CHECK (limite > 0),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Um só limite por categoria e por utilizador: guardar outra vez substitui o anterior (upsert).
    PRIMARY KEY (user_id, categoria)
);

-- Só a API (chave secreta) lê e escreve.
ALTER TABLE orcamentos ENABLE ROW LEVEL SECURITY;
