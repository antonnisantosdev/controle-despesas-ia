// Listas de escolha, iguais aos Literal do backend (models.py: Categoria e MetodoPagamento).
// Se mudares uma lista lá, muda-a também aqui.
// As CHAVES (o que vai para a base de dados e para a IA) não mudam por país: só o rótulo mostrado e quais
// aparecem para escolher. Nos componentes usar useOpcoes() (lib/textos.ts), que já escolhe pelo país da conta.

import type { Pais } from "./formatos";

export const CATEGORIAS = [
  "alimentação",
  "restaurantes",
  "transporte",
  "casa",
  "saúde",
  "lazer",
  "compras",
  "telecomunicações",
  "rendimento",
  "transferências",
  "levantamentos",
  "outros",
] as const;

export type Categoria = (typeof CATEGORIAS)[number];

// Rótulo mostrado de cada categoria. Em PT o rótulo é a própria chave (nomeCategoria, em lib/textos.ts, põe a 1.ª letra em maiúscula).
// BR: rótulos do copywriter (passo 7), em minúsculas como no PT. O tipo obriga a ter todas as chaves.
export const ROTULOS_CATEGORIAS: Record<Pais, Record<Categoria, string>> = {
  PT: {
    "alimentação": "alimentação",
    restaurantes: "restaurantes",
    transporte: "transporte",
    casa: "casa",
    "saúde": "saúde",
    lazer: "lazer",
    compras: "compras",
    "telecomunicações": "telecomunicações",
    rendimento: "rendimento",
    "transferências": "transferências",
    levantamentos: "levantamentos",
    outros: "outros",
  },
  BR: {
    "alimentação": "alimentação",
    restaurantes: "restaurantes",
    transporte: "transporte",
    casa: "moradia",
    "saúde": "saúde",
    lazer: "lazer",
    compras: "compras",
    "telecomunicações": "telefone e internet",
    rendimento: "receitas",
    "transferências": "transferências",
    levantamentos: "saques",
    outros: "outros",
  },
};

// Categorias que aparecem para escolher em cada país (pela ordem da lista). Para esconder uma num país,
// tira-a só da lista desse país: as movimentações antigas com essa chave continuam a mostrar o rótulo.
export const CATEGORIAS_POR_PAIS: Record<Pais, readonly Categoria[]> = {
  PT: CATEGORIAS,
  BR: CATEGORIAS,
};

export const METODOS = [
  "dinheiro",
  "cartao_debito",
  "cartao_credito",
  "cartao_refeicao",
  "mbway",
  "transferencia",
  "debito_direto",
  "pix",
  "boleto",
] as const;

export type MetodoPagamento = (typeof METODOS)[number];

// Código guardado na base de dados -> nome mostrado ao utilizador.
// BR: nomes do copywriter (passo 7).
export const ROTULOS_METODOS: Record<Pais, Record<MetodoPagamento, string>> = {
  PT: {
    dinheiro: "Dinheiro",
    cartao_debito: "Cartão de débito",
    cartao_credito: "Cartão de crédito",
    cartao_refeicao: "Cartão refeição",
    mbway: "MB Way",
    transferencia: "Transferência",
    debito_direto: "Débito direto",
    pix: "Pix", // não aparece para escolher em PT; só para movimentações de uma conta que mudou de país
    boleto: "Boleto",
  },
  BR: {
    dinheiro: "Dinheiro",
    cartao_debito: "Cartão de débito",
    cartao_credito: "Cartão de crédito",
    cartao_refeicao: "Vale-refeição",
    mbway: "MB Way", // não aparece para escolher no BR (METODOS_POR_PAIS); só para movimentações antigas
    transferencia: "Transferência",
    debito_direto: "Débito automático",
    pix: "Pix",
    boleto: "Boleto",
  },
};

// Métodos que aparecem para escolher em cada país. O MB Way só existe em Portugal; o Pix e o boleto, no Brasil
// (uma movimentação antiga com um método do outro país continua a mostrar o nome). No BR o Pix vem logo a seguir
// ao dinheiro: é a forma de pagamento mais usada lá.
export const METODOS_POR_PAIS: Record<Pais, readonly MetodoPagamento[]> = {
  PT: METODOS.filter((m) => m !== "pix" && m !== "boleto"),
  BR: ["dinheiro", "pix", "cartao_debito", "cartao_credito", "cartao_refeicao", "boleto", "transferencia", "debito_direto"],
};
