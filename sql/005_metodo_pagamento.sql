-- Como foi paga cada transação (dinheiro, cartão, MB Way...).
-- Fica vazio (NULL) nas transações antigas e nas importadas de extratos, que não trazem essa informação.
ALTER TABLE transacoes ADD COLUMN metodo_pagamento TEXT;
