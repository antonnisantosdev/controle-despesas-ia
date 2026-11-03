// Listas de escolha, iguais aos Literal do backend (models.py: Categoria e MetodoPagamento).
// Se mudares uma lista lá, muda-a também aqui.

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
];

// Código guardado na base de dados -> nome mostrado ao utilizador.
export const METODOS_PAGAMENTO: Record<string, string> = {
  dinheiro: "Dinheiro",
  cartao_debito: "Cartão de débito",
  cartao_credito: "Cartão de crédito",
  cartao_refeicao: "Cartão refeição",
  mbway: "MB Way",
  transferencia: "Transferência",
  debito_direto: "Débito direto",
};
