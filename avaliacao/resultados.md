# Resultados da avaliação da categorização

| Data | Modelo | Conjunto | Casos | Acertos | Percentagem | Nota |
|---|---|---|---|---|---|---|
| 2026-11-08 | claude-haiku-5-5 | casos_categorizacao.csv | 49 | 45 | 91.8% | prompt inicial |
| 2026-11-08 | claude-haiku-5-5 | casos_novos.csv | 10 | 8 | 80.0% | prompt inicial |
| 2026-11-08 | claude-haiku-5-5 | casos_categorizacao.csv | 49 | 49 | 100.0% | regras por tipo de despesa |
| 2026-11-08 | claude-haiku-5-5 | casos_novos.csv | 10 | 10 | 100.0% | regras por tipo de despesa |
| 2026-11-12 | claude-haiku-5-5 | casos_br.csv | 44 | 43 | 97.7% | Brasil: prompt BR inicial (falhou Pix recebido de pessoa) |
| 2026-11-12 | claude-haiku-5-5 | casos_br.csv | 44 | 44 | 100.0% | Brasil: prompt BR com Pix recebido de pessoa = transferências |
