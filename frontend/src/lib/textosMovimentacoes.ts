// Textos da página Movimentações: lista, importação de extratos e nova movimentação.
// Passo 5 da Fase 1 Brasil: os textos saíram dos componentes .tsx sem mudar uma letra.
// Os textos de categorizar, apagar e envio à IA estão em textosPlanos.ts (TEXTOS_CATEGORIZAR, TEXTOS_APAGAR_MOVIMENTO,
// TEXTOS_ENVIO_IA). As categorias e os métodos de pagamento estão em opcoes.ts (iguais ao backend).
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).
// Fase 1 Brasil, passo 6: dicionário { PT, BR }. Nos componentes: const { TEXTOS_... } = useTextos(DICIONARIO_MOVIMENTACOES)
// (lib/textos.ts), que escolhe pelo país da conta. Fora da app (páginas públicas) é sempre o PT.

import type { Dicionario, Traducao } from "./textos";

const PT = {
  TEXTOS_MOVIMENTACOES: {
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

    // Nota pessoal de cada movimentação (CampoNota, PATCH /transacoes/{id}). A descrição do banco não muda.
    prefixoNota: "Nota:", // TEXTO NOVO (só para leitores de ecrã, antes da nota)
    adicionarNota: "Adicionar nota", // TEXTO NOVO
    editarNota: "Editar nota", // TEXTO NOVO
    rotuloAdicionarNota: "Adicionar nota a {descricao}", // TEXTO NOVO
    rotuloEditarNota: "Editar a nota de {descricao}", // TEXTO NOVO
    rotuloCampoNota: "Nota de {descricao}", // TEXTO NOVO
    contadorNota: "{n} de {maximo} caracteres", // TEXTO NOVO
    ajudaNota: "Para apagar a nota, deixa o campo vazio e carrega em Guardar.",
    guardarNota: "Guardar", // TEXTO NOVO
    aGuardarNota: "A guardar...", // TEXTO NOVO
    cancelarNota: "Cancelar", // TEXTO NOVO
    erroNota: "Não foi possível guardar a nota. Tenta outra vez.", // TEXTO NOVO
  } as const,

  // Botão "Importar extrato" (BotaoImportar, POST /transacoes/importar).
  TEXTOS_IMPORTAR: {
    botao: "Importar extrato",
    aImportar: "A importar e a categorizar...",
    linhasInvalidas: "O extrato tem linhas inválidas. Corrige-as e volta a importar.",
    semApi: "Não foi possível ligar à API. Confirma que o fastapi dev está a correr.",
  } as const,

  // Formulário "Nova movimentação" (FormNovaMovimentacao, POST /transacoes).
  TEXTOS_NOVA_MOVIMENTACAO: {
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
    erroValorMaximo: "O valor máximo é {maximo}.", // {maximo}: 1 000 000 000 € (ou R$)
    erroGuardar: "Não foi possível guardar. Confirma os dados e tenta outra vez.",
    guardar: "Guardar",
    aGuardar: "A guardar...",
    aCategorizar: "A IA está a categorizar...",
    nota: "Nota (opcional)", // TEXTO NOVO
    marcadorNota: "Ex.: jantar de anos da Rita", // TEXTO NOVO
    contadorNota: "{n} de {maximo} caracteres", // TEXTO NOVO
  } as const,
};

export type TextosMovimentacoes = Traducao<typeof PT>;

// ===== BR (PT-BR) =====
// Textos PT-BR do copywriter (passo 7). Mesmas chaves e mesmos {placeholders} do PT; o tipo obriga a ter todas
// as chaves (o `npx tsc --noEmit` falha se faltar alguma).
const BR: TextosMovimentacoes = {
  TEXTOS_MOVIMENTACOES: {
    etiquetaTopo: "Suas transações",
    titulo: "Movimentações",
    rotuloMes: "Mês",
    novaMovimentacao: "+ Nova movimentação",
    erroCarregar: "Não foi possível carregar as movimentações. Confira se a API está rodando.",
    erroCategoria: "Não foi possível salvar a categoria. Tente de novo.",
    importadas: "{importadas} importada(s), {duplicadas} já existia(m).",
    fecharAviso: "Fechar aviso",
    aCarregar: "Carregando...",
    vazio: "Sem movimentações neste mês.",

    // Tabela
    colunaData: "Data",
    colunaDescricao: "Descrição",
    colunaCategoria: "Categoria",
    colunaMetodo: "Forma",
    colunaValor: "Valor",
    colunaAcoes: "Ações", // só para leitores de ecrã
    rotuloCategoria: "Categoria de {descricao}",
    semCategoria: "sem categoria",

    // Nota pessoal de cada movimentação (CampoNota, PATCH /transacoes/{id}).
    prefixoNota: "Nota:", // TEXTO NOVO
    adicionarNota: "Adicionar nota", // TEXTO NOVO
    editarNota: "Editar nota", // TEXTO NOVO
    rotuloAdicionarNota: "Adicionar nota a {descricao}", // TEXTO NOVO
    rotuloEditarNota: "Editar a nota de {descricao}", // TEXTO NOVO
    rotuloCampoNota: "Nota de {descricao}", // TEXTO NOVO
    contadorNota: "{n} de {maximo} caracteres", // TEXTO NOVO
    ajudaNota: "Para apagar a nota, deixe o campo vazio e clique em Salvar.",
    guardarNota: "Salvar", // TEXTO NOVO
    aGuardarNota: "Salvando...", // TEXTO NOVO
    cancelarNota: "Cancelar", // TEXTO NOVO
    erroNota: "Não foi possível salvar a nota. Tente de novo.", // TEXTO NOVO
  },

  // Botão "Importar extrato" (BotaoImportar, POST /transacoes/importar).
  TEXTOS_IMPORTAR: {
    botao: "Importar extrato",
    aImportar: "Importando e categorizando...",
    linhasInvalidas: "O extrato tem linhas inválidas. Corrija e importe de novo.",
    semApi: "Não foi possível conectar à API. Confira se o fastapi dev está rodando.",
  },

  // Formulário "Nova movimentação" (FormNovaMovimentacao, POST /transacoes).
  TEXTOS_NOVA_MOVIMENTACAO: {
    titulo: "Nova movimentação",
    cancelar: "Cancelar",
    despesa: "Despesa",
    entrada: "Entrada",
    descricao: "Descrição",
    marcadorDescricao: "Ex.: Café com o João",
    valor: "Valor ({simbolo})", // {simbolo}: € ou R$, conforme a moeda da conta
    marcadorValor: "0,00",
    data: "Data",
    metodo: "Forma de pagamento",
    categoria: "Categoria",
    iaEscolhe: "✨ Deixar a IA escolher",
    erroValor: "Digite um valor maior que zero.",
    erroValorMaximo: "O valor máximo é {maximo}.",
    erroGuardar: "Não foi possível salvar. Confira os dados e tente de novo.",
    guardar: "Salvar",
    aGuardar: "Salvando...",
    aCategorizar: "A IA está categorizando...",
    nota: "Nota (opcional)", // TEXTO NOVO
    marcadorNota: "Ex.: jantar de aniversário da Rita", // TEXTO NOVO
    contadorNota: "{n} de {maximo} caracteres", // TEXTO NOVO
  },
};

export const DICIONARIO_MOVIMENTACOES: Dicionario<TextosMovimentacoes> = { PT, BR };
