-- Registo de cada chamada à IA: quantos tokens gastou, quanto custou e quanto tempo demorou.
-- Serve para saber quanto custa cada funcionalidade (e, mais tarde, quanto cobrar em cada plano).
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.

CREATE TABLE chamadas_ia (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    funcao TEXT NOT NULL,             -- categorizar, chat, resumo, talao, extrato_pdf...
    origem TEXT NOT NULL,             -- "app" (utilizadores) ou "avaliacao" (o script de avaliação)
    modelo TEXT NOT NULL,
    tokens_entrada INTEGER NOT NULL,
    tokens_saida INTEGER NOT NULL,
    custo_usd NUMERIC(12, 6),         -- vazio se o preço do modelo não for conhecido
    duracao_ms INTEGER NOT NULL,
    sucesso BOOLEAN NOT NULL          -- false se a resposta da IA não passou na validação
);

-- As consultas de custos filtram quase sempre por data.
CREATE INDEX chamadas_ia_data ON chamadas_ia (criado_em);

-- Só a API (chave secreta) lê e escreve.
ALTER TABLE chamadas_ia ENABLE ROW LEVEL SECURITY;

-- Consulta útil (não faz parte da migração): custo por funcionalidade nos últimos 30 dias.
-- SELECT funcao,
--        count(*) AS chamadas,
--        round(avg(tokens_entrada)) AS media_tokens_entrada,
--        round(avg(tokens_saida)) AS media_tokens_saida,
--        round(sum(custo_usd), 4) AS custo_total_usd,
--        round(avg(custo_usd) * 100, 4) AS custo_medio_centimos,
--        round(avg(duracao_ms)) AS media_ms
-- FROM chamadas_ia
-- WHERE origem = 'app' AND criado_em > now() - interval '30 days'
-- GROUP BY funcao
-- ORDER BY custo_total_usd DESC;
