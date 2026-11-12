// Textos do separador Talões em Minhas compras: lista de compras e revisão do talão lido pela IA.
// Passo 5 da Fase 1 Brasil: os textos saíram dos componentes .tsx sem mudar uma letra.
// O separador Preços está em textosPrecosLojas.ts; o aviso de envio à IA em textosPlanos.ts (TEXTOS_ENVIO_IA).
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).
// Fase 1 Brasil, passo 6: dicionário { PT, BR }. Nos componentes: const { TEXTOS_... } = useTextos(DICIONARIO_COMPRAS)
// (lib/textos.ts), que escolhe pelo país da conta. Fora da app (páginas públicas) é sempre o PT.

import type { Dicionario, Traducao } from "./textos";

const PT = {
  TEXTOS_COMPRAS: {
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
  } as const,

  // Revisão do talão antes de gravar (RevisaoTalao, POST /compras).
  TEXTOS_REVISAO_TALAO: {
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
  } as const,
};

export type TextosCompras = Traducao<typeof PT>;

// ===== BR (PT-BR) =====
// Textos PT-BR do copywriter (passo 7). Mesmas chaves e mesmos {placeholders} do PT; o tipo obriga a ter todas
// as chaves (o `npx tsc --noEmit` falha se faltar alguma).
const BR: TextosCompras = {
  TEXTOS_COMPRAS: {
    etiquetaTopo: "Notas fiscais lidas pela IA",
    titulo: "Minhas compras",
    fotografar: "📷 Fotografar nota fiscal",
    aLer: "A IA está lendo a nota fiscal...",
    erroCarregar: "Não foi possível carregar as compras. Confira se a API está rodando.",
    erroLer: "Não foi possível ler a foto. Tente de novo.",
    gravada: "Compra salva: {loja}, {total}. Já aparece nas Movimentações.",
    aCarregar: "Carregando...",
    vazio: "Você ainda não tem compras. Fotografe uma nota fiscal para começar.",
    vazioSemTaloes: "Você ainda não tem compras.", // no Free, onde não se fotografam talões
    resumoCompra: "{data} · {n} produtos",
    quantidade: " × {quantidade}",
  },

  // Revisão do talão antes de gravar (RevisaoTalao, POST /compras).
  TEXTOS_REVISAO_TALAO: {
    etiquetaTopo: "Lida pela IA",
    titulo: "Confira a nota fiscal antes de salvar",
    loja: "Loja",
    data: "Data",
    categoria: "Categoria",
    metodo: "Forma de pagamento",
    colunaProduto: "Produto",
    colunaQuantidade: "Qtd.",
    colunaPreco: "Preço ({simbolo})", // {simbolo}: € ou R$, conforme a moeda da conta
    rotuloProduto: "Produto",
    rotuloQuantidade: "Quantidade",
    rotuloPreco: "Preço",
    remover: "Remover {descricao}",
    total: "Total da nota ({simbolo})",
    soma: "Soma dos produtos: ",
    diferenca: "A soma dos produtos difere {diferenca} do total. Confira os preços na nota fiscal.",
    erroData: "A IA não conseguiu ler a data: escolha a data antes de salvar.",
    erroGravar: "Não foi possível salvar a compra. Confira os dados e tente de novo.",
    cancelar: "Cancelar",
    gravar: "Salvar compra",
    aGravar: "Salvando...",
  },
};

export const DICIONARIO_COMPRAS: Dicionario<TextosCompras> = { PT, BR };
