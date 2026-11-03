-- Registo de cada pergunta feita ao chat, para limitar quantas cada utilizador faz por dia
-- (cada pergunta custa dinheiro na conta da Anthropic).
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.

CREATE TABLE uso_ia (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A contagem "quantas perguntas hoje?" filtra por utilizador e data: este índice torna-a rápida
-- mesmo com milhares de linhas (como o índice de um livro, em vez de ler todas as páginas).
CREATE INDEX uso_ia_user_data ON uso_ia (user_id, criado_em);

-- Só a API (chave secreta) lê e escreve.
ALTER TABLE uso_ia ENABLE ROW LEVEL SECURITY;
