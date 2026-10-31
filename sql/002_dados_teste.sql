-- Dados de teste inventados (nunca usar dados bancários reais).
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.
-- Valores negativos são despesas, positivos são receitas.

INSERT INTO transacoes (data, descricao, valor, categoria) VALUES
    ('2026-09-01', 'Salário Empresa Fictícia', 1200.00, 'rendimento'),
    ('2026-09-03', 'Supermercado Pingo Azul', -45.30, 'alimentação'),
    ('2026-09-05', 'Passe mensal metro', -40.00, 'transporte'),
    ('2026-09-12', 'Restaurante O Tasco Inventado', -22.50, 'restaurantes'),
    -- Esta ainda não tem categoria: no futuro será a IA a sugerir uma.
    ('2026-09-15', 'Cinema Shopping Teste', -8.90, NULL);
