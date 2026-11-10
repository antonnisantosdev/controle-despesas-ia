// Textos dos pagamentos que se repetem (GET /recorrentes, sem IA).
// Revistos pelo copywriter (versão A, Fase 2).
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).

export const TEXTOS_RECORRENTES = {
  titulo: "Pagamentos que se repetem",
  explicacao:
    "Subscrições, ginásio, renda: as despesas que te saem da conta todos os meses. Aparecem aqui quando se repetem há pelo menos 3 meses seguidos, uma vez por mês, com a mesma descrição e um valor parecido. Não gasta pedidos à IA.",
  totalPorMes: "Cerca de {total} por mês",
  porMes: "{valor}/mês",
  detalhe: "Há {meses} meses seguidos · último a {data}",
  subiu: "Subiu de {antes} para {depois}",
  desceu: "Desceu de {antes} para {depois}",
  vazio:
    "Ainda não encontrámos pagamentos que se repitam. Precisamos de pelo menos 3 meses seguidos de movimentações, incluindo o mês atual ou o anterior. Importa os extratos dos últimos meses para os veres aqui.",
  erro: "Não foi possível carregar os pagamentos que se repetem.",
  aCarregar: "A procurar...",
  // Cartão do dashboard
  tituloCurto: "Pagamentos mensais",
  resumoCurto: "{quantos} pagamentos que se repetem, cerca de {total} por mês.",
  resumoCurtoUm: "1 pagamento que se repete, cerca de {total} por mês.",
  verTodos: "Ver no Planeamento",
};
