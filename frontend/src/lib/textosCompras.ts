// Textos do separador Talões em Minhas compras: lista de compras e revisão do talão lido pela IA.
// Passo 5 da Fase 1 Brasil: os textos saíram dos componentes .tsx sem mudar uma letra.
// O separador Preços está em textosPrecosLojas.ts; o aviso de envio à IA em textosPlanos.ts (TEXTOS_ENVIO_IA).
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).

export const TEXTOS_COMPRAS = {
  etiquetaTopo: "Talões lidos pela IA",
  titulo: "Minhas compras",
  fotografar: "📷 Fotografar talão",
  aLer: "A IA está a ler o talão...",
  erroCarregar: "Não foi possível carregar as compras. Confirma que a API está a correr.",
  erroLer: "Não foi possível ler a fotografia. Tenta outra vez.",
  gravada: "Compra gravada: {loja}, {total}. Já aparece nas Movimentações.",
  aCarregar: "A carregar...",
  vazio: "Ainda não tens compras. Fotografa um talão para começar.",
  vazioSemTaloes: "Ainda não tens compras.", // no Free, onde não se fotografam talões
  resumoCompra: "{data} · {n} produtos",
  quantidade: " × {quantidade}",
} as const;

// Revisão do talão antes de gravar (RevisaoTalao, POST /compras).
export const TEXTOS_REVISAO_TALAO = {
  etiquetaTopo: "Lido pela IA",
  titulo: "Confirma o talão antes de gravar",
  loja: "Loja",
  data: "Data",
  categoria: "Categoria",
  metodo: "Método de pagamento",
  colunaProduto: "Produto",
  colunaQuantidade: "Qtd.",
  colunaPreco: "Preço ({simbolo})", // {simbolo}: € ou R$, conforme a moeda da conta
  rotuloProduto: "Produto",
  rotuloQuantidade: "Quantidade",
  rotuloPreco: "Preço",
  remover: "Remover {descricao}",
  total: "Total do talão ({simbolo})",
  soma: "Soma dos produtos: ",
  diferenca: "A soma dos produtos difere {diferenca} do total. Confirma os preços com o talão.",
  erroData: "A IA não conseguiu ler a data: escolhe-a antes de gravar.",
  erroGravar: "Não foi possível gravar a compra. Confirma os dados e tenta outra vez.",
  cancelar: "Cancelar",
  gravar: "Gravar compra",
  aGravar: "A gravar...",
} as const;
