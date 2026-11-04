-- Minhas compras: os talões lidos pela IA e os produtos de cada um.
-- Cada compra está ligada a UMA transação (com o total do talão), que é o que entra no dashboard;
-- os produtos ficam aqui só como detalhe.
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.

CREATE TABLE compras (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    -- ON DELETE CASCADE: se a transação for apagada, a compra (e os produtos) vão com ela.
    -- UNIQUE: uma transação só pode ter um talão.
    transacao_id BIGINT NOT NULL UNIQUE REFERENCES transacoes (id) ON DELETE CASCADE,
    loja TEXT NOT NULL,
    data DATE NOT NULL,
    total NUMERIC(12, 2) NOT NULL CHECK (total > 0),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Um produto de uma compra. Não precisa de user_id: o dono é o da compra.
CREATE TABLE compra_itens (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    compra_id BIGINT NOT NULL REFERENCES compras (id) ON DELETE CASCADE,
    descricao TEXT NOT NULL,
    quantidade NUMERIC(10, 3) NOT NULL CHECK (quantidade > 0),
    -- Pode ser 0 (um brinde), mas nunca negativo: os descontos já vêm abatidos.
    preco NUMERIC(12, 2) NOT NULL CHECK (preco >= 0)
);

-- A página Minhas compras lista as compras de um utilizador, das mais recentes para as mais antigas.
CREATE INDEX compras_user_data ON compras (user_id, data DESC);
-- Abrir uma compra vai buscar os produtos dela.
CREATE INDEX compra_itens_compra ON compra_itens (compra_id);

-- Só a API (chave secreta) lê e escreve.
ALTER TABLE compras ENABLE ROW LEVEL SECURITY;
ALTER TABLE compra_itens ENABLE ROW LEVEL SECURITY;
