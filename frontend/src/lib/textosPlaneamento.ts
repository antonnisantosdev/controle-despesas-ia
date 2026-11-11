// Textos da página Planeamento: orçamento por categoria e sugestão da IA.
// Passo 5 da Fase 1 Brasil: os textos saíram dos componentes .tsx sem mudar uma letra.
// Os pagamentos que se repetem estão em textosRecorrentes.ts e os alertas em textosPlanos.ts (TEXTOS_ALERTA_ORCAMENTO).
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).

export const TEXTOS_PLANEAMENTO = {
  etiquetaTopo: "Orçamento mensal",
  titulo: "Planeamento",
  rotuloMes: "Mês",
  sugerir: "✨ Sugerir orçamento",
  aSugerir: "A IA está a analisar...",
  erroCarregar: "Não foi possível carregar o planeamento. Confirma que a API está a correr.",
  erroGuardar: "Não foi possível guardar o orçamento. Tenta outra vez.",
  erroSugestao: "Não foi possível pedir a sugestão. Tenta outra vez.",
  // "Nas categorias com orçamento, gastaste 120,00 € de 300,00 € previstos." (os valores, na moeda da conta, vão a negrito)
  totalAntes: "Nas categorias com orçamento, gastaste ",
  totalMeio: " de ",
  totalFim: " previstos.",
  aCarregar: "A carregar...",
  vazio: "Sem gastos nem orçamentos neste mês.",
  rotuloNovaCategoria: "Categoria para novo orçamento",
  adicionar: "+ Adicionar orçamento para...",
} as const;

// Uma linha do orçamento (LinhaPlaneamento).
export const TEXTOS_LINHA_ORCAMENTO = {
  marcador: "Limite {simbolo}", // {simbolo}: € ou R$, conforme a moeda da conta
  rotuloCampo: "Orçamento mensal de {categoria}",
  guardar: "Guardar",
  semOrcamento: "Gastaste {gasto} · sem orçamento",
  passaste: "{gasto} de {limite} · passaste {diferenca}",
  faltam: "{gasto} de {limite} · faltam {diferenca}",
} as const;

// Sugestão de orçamento da IA (SugestoesIA). porMes vem a seguir ao nome da categoria (a negrito).
export const TEXTOS_SUGESTOES = {
  titulo: "✨ Sugestão da IA",
  aceitarTodas: "Aceitar todas",
  fechar: "Fechar",
  semGastos: "Ainda não há gastos suficientes para sugerir um orçamento.",
  porMes: " · {valor} por mês",
  aceite: "✓ Aceite",
  aceitar: "Aceitar",
} as const;
