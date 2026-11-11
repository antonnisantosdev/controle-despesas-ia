// Textos do dashboard (Visão geral): cartões, gráficos, resumo do mês e chat.
// Passo 5 da Fase 1 Brasil: os textos saíram dos componentes .tsx sem mudar uma letra.
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).

export const TEXTOS_DASHBOARD = {
  etiquetaTopo: "Resumo financeiro",
  titulo: "Visão geral",
  rotuloMes: "Mês",
  erroCarregar: "Não foi possível carregar os dados. Confirma que a API está a correr.",

  // Cartões de resumo
  saldoMes: "Saldo do mês",
  saldoMesDescricao: "Entradas menos despesas",
  entradasMes: "Entradas do mês",
  entradasMesDescricao: "Dinheiro que entrou",
  despesasMes: "Despesas do mês",
  despesasMesDescricao: "Dinheiro que saiu",
  saldoAcumulado: "Saldo acumulado",
  saldoAcumuladoDescricao: "Desde o primeiro extrato",

  // Gráficos
  evolucaoTitulo: "Movimentação financeira",
  evolucaoTexto: "Entradas e despesas de cada mês",
  categoriasTitulo: "Gastos por categoria",
  categoriasTexto: "Para onde foi o dinheiro em {mes}",
  semMes: "...", // enquanto o mês ainda não chegou
} as const;

// Legendas e textos dos gráficos do dashboard (GraficoMensal e GraficoCategorias).
export const TEXTOS_GRAFICOS = {
  receitas: "Receitas",
  despesas: "Despesas",
  total: "Total",
  semDespesas: "Sem despesas neste mês.",
} as const;

// Cartão "Resumo do mês" (ResumoCartao, GET /resumo).
export const TEXTOS_RESUMO_MES = {
  titulo: "Resumo do mês",
  aCarregar: "A IA está a analisar o mês...",
  erro: "O resumo não está disponível. Tenta mais tarde.",
  atencao: "⚠ Atenção: ",
  nota: "ℹ Nota: ",
} as const;

// Chat do dashboard. Os exemplos aparecem entre aspas, separados por vírgulas e "ou" antes do último.
export const TEXTOS_CHAT = {
  titulo: "Pergunta às tuas finanças",
  exemplos: [
    "Em que gastei mais este mês?",
    "Quanto transferi para a Rita este mês?",
    "Quanto gastei em combustível nos últimos 3 meses?",
  ],
  experimenta: "Experimenta: {exemplos}",
  ou: "ou",
  aPensar: "A consultar os teus dados...",
  erro: "O chat falhou. Tenta mais tarde.",
  marcador: "Escreve uma pergunta...",
  enviar: "Enviar",
} as const;
