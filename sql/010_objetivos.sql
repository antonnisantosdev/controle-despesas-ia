-- Minha reserva: objetivos de poupança ("Férias: 1.200 € até julho").
-- O valor poupado é atualizado à mão pelo utilizador ("+ Juntei dinheiro").
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.

CREATE TABLE objetivos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    nome TEXT NOT NULL CHECK (length(nome) BETWEEN 1 AND 100),
    valor_alvo NUMERIC(12, 2) NOT NULL CHECK (valor_alvo > 0),
    -- Sem prazo não há "quanto por mês", por isso a data é obrigatória.
    data_alvo DATE NOT NULL,
    -- Começa a zero. Pode passar o alvo (quem poupa a mais não deve ver um erro).
    valor_poupado NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (valor_poupado >= 0),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A página lista os objetivos de um utilizador, do prazo mais próximo para o mais distante.
CREATE INDEX objetivos_user_data ON objetivos (user_id, data_alvo);

-- Só a API (chave secreta) lê e escreve.
ALTER TABLE objetivos ENABLE ROW LEVEL SECURITY;
