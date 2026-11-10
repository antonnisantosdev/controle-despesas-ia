// Textos da página Resumo anual (/relatorio). Revistos pelo copywriter.
// O título, o aviso e a nota das categorias vêm da API (relatorio.py, textos do contador): não se repetem aqui.
// Sem palavras fiscais: "Entradas" e "Saídas", nunca rendimento, imposto, IRS ou dedutível.
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).

export const TEXTOS_RELATORIO = {
  menu: "Resumo anual",
  etiquetaTopo: "Resumo anual",
  tituloReserva: "Resumo anual das tuas finanças – {ano}", // enquanto a API não responde (igual ao da API, para não saltar)
  seletorAno: "Escolher o ano",

  // Ações
  csv: "Descarregar em CSV",
  csvADescarregar: "A preparar o CSV...",
  csvErro: "Não foi possível descarregar o CSV. Tenta outra vez.",
  csvPlanoPago: "Descarregar o resumo anual em CSV (para abrir numa folha de cálculo) está disponível nos planos Essencial e Completo. No Free, podes ver o resumo aqui e guardá-lo em PDF.",
  pdf: "Guardar como PDF",
  pdfAjuda: "Abre-se a janela de impressão do browser: escolhe \"Guardar como PDF\" para ficares com o ficheiro.",
  ia: "Resumir o ano com a IA",
  iaAPensar: "A IA está a escrever o resumo...",
  iaTitulo: "Resumo do ano pela IA",
  iaGasta: "O resumo pela IA conta como 1 pedido à IA.",
  iaErro: "Não foi possível fazer o resumo pela IA. Tenta outra vez daqui a pouco.",
  iaDemo: "Na demo, o resumo pela IA não está disponível.",

  // Estados
  aCarregar: "A preparar o resumo do ano...",
  erro: "Não foi possível carregar o resumo do ano. Tenta outra vez daqui a pouco.",
  tentarOutraVez: "Tentar outra vez",
  vazioTitulo: "Ainda não há movimentos em {ano}",
  vazioTexto: "Importa os extratos desse ano ou regista movimentos à mão para veres aqui as entradas, as saídas e os gastos por categoria.",
  vazioBotao: "Ir para Movimentações",

  // Ano incompleto
  anoAtual: "O ano ainda não acabou: os números vão até {mes}.",
  mesesSemDados: "Meses sem movimentos: {meses}. Se tiveres extratos destes meses, podes importá-los.",

  // Totais
  saldo: "Saldo do ano",
  saldoDescricao: "Entradas menos saídas",
  entradas: "Entradas",
  entradasDescricao: "Dinheiro que entrou",
  saidas: "Saídas",
  saidasDescricao: "Dinheiro que saiu",

  // Mês a mês
  mesAMesTitulo: "Mês a mês",
  mesAMesTexto: "Entradas e saídas de cada mês",
  colunaMes: "Mês",
  colunaSaldo: "Saldo",
  semMovimentos: "sem movimentos",

  // Categorias
  categoriasTitulo: "Gastos por categoria",
  categoriasTexto: "Para onde foi o dinheiro ao longo do ano",
  categoriasVazio: "Sem gastos neste ano.",

  // Comparação
  comparacaoTitulo: "Comparação com {ano}",
  comparacaoMeses: "Comparamos os mesmos meses nos dois anos: {meses}.",
  comparacaoMesesIncompletos: "Em {ano} só há movimentos em {n} destes meses.",
  comparacaoSem: "Não há movimentos em {ano} nestes meses, por isso não há com que comparar.",
  comparacaoCategorias: "Gastos por categoria",
  comparacaoMais: "+{valor}",
  comparacaoIgual: "igual",
  anoInteiro: "ano inteiro",
  mesesAte: "{de} a {ate}",

  // Maiores gastos
  maioresTitulo: "Os maiores gastos do ano",
  maioresVazio: "Sem gastos neste ano.",

  // Recorrentes
  recorrentesTitulo: "Pagamentos que se repetem",
  recorrentesTexto: "Subscrições e outros pagamentos que te saem todos os meses",
  recorrentesPorMes: "{valor}/mês",
  recorrentesPagamentos: "{n} pagamentos no ano",
  recorrentesUmPagamento: "1 pagamento no ano",
  recorrentesVazio: "Não encontrámos pagamentos que se repetem neste ano.",

  // Objetivos
  objetivosTitulo: "Objetivos de poupança",
  objetivosTexto: "Como estão hoje, não no fim do ano",
  objetivosPoupado: "{poupado} de {alvo}",
  objetivosPrazo: "Prazo: {data}",
  objetivosVazio: "Ainda não tens objetivos de poupança.",
  objetivosLink: "Criar um objetivo",
};
