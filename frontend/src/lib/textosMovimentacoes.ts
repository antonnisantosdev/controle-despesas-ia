// Textos da página Movimentações: lista, importação de extratos e nova movimentação.
// Passo 5 da Fase 1 Brasil: os textos saíram dos componentes .tsx sem mudar uma letra.
// Os textos de categorizar, apagar e envio à IA estão em textosPlanos.ts (TEXTOS_CATEGORIZAR, TEXTOS_APAGAR_MOVIMENTO,
// TEXTOS_ENVIO_IA). As categorias e os métodos de pagamento estão em opcoes.ts (iguais ao backend).
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).

export const TEXTOS_MOVIMENTACOES = {
  etiquetaTopo: "As tuas transações",
  titulo: "Movimentações",
  rotuloMes: "Mês",
  novaMovimentacao: "+ Nova movimentação",
  erroCarregar: "Não foi possível carregar as movimentações. Confirma que a API está a correr.",
  erroCategoria: "Não foi possível guardar a categoria. Tenta outra vez.",
  importadas: "{importadas} importada(s), {duplicadas} já existia(m).",
  fecharAviso: "Fechar aviso",
  aCarregar: "A carregar...",
  vazio: "Sem movimentações neste mês.",

  // Tabela
  colunaData: "Data",
  colunaDescricao: "Descrição",
  colunaCategoria: "Categoria",
  colunaMetodo: "Método",
  colunaValor: "Valor",
  colunaAcoes: "Ações", // só para leitores de ecrã
  rotuloCategoria: "Categoria de {descricao}",
  semCategoria: "sem categoria",
} as const;

// Botão "Importar extrato" (BotaoImportar, POST /transacoes/importar).
export const TEXTOS_IMPORTAR = {
  botao: "Importar extrato",
  aImportar: "A importar e a categorizar...",
  linhasInvalidas: "O extrato tem linhas inválidas. Corrige-as e volta a importar.",
  semApi: "Não foi possível ligar à API. Confirma que o fastapi dev está a correr.",
} as const;

// Formulário "Nova movimentação" (FormNovaMovimentacao, POST /transacoes).
export const TEXTOS_NOVA_MOVIMENTACAO = {
  titulo: "Nova movimentação",
  cancelar: "Cancelar",
  despesa: "Despesa",
  entrada: "Entrada",
  descricao: "Descrição",
  marcadorDescricao: "Ex.: Café com o João",
  valor: "Valor ({simbolo})", // {simbolo}: € ou R$, conforme a moeda da conta
  marcadorValor: "0,00",
  data: "Data",
  metodo: "Método de pagamento",
  categoria: "Categoria",
  iaEscolhe: "✨ Deixar a IA escolher",
  erroValor: "Escreve um valor maior do que zero.",
  erroGuardar: "Não foi possível guardar. Confirma os dados e tenta outra vez.",
  guardar: "Guardar",
  aGuardar: "A guardar...",
  aCategorizar: "A IA está a categorizar...",
} as const;
