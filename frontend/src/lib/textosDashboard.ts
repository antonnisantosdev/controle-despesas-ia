// Textos do dashboard (Visão geral): cartões, gráficos, resumo do mês e chat.
// Passo 5 da Fase 1 Brasil: os textos saíram dos componentes .tsx sem mudar uma letra.
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).
// Fase 1 Brasil, passo 6: dicionário { PT, BR }. Nos componentes: const { TEXTOS_... } = useTextos(DICIONARIO_DASHBOARD)
// (lib/textos.ts), que escolhe pelo país da conta. Fora da app (páginas públicas) é sempre o PT.

import type { Dicionario, Traducao } from "./textos";

const PT = {
  TEXTOS_DASHBOARD: {
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
  } as const,

  // Legendas e textos dos gráficos do dashboard (GraficoMensal e GraficoCategorias).
  TEXTOS_GRAFICOS: {
    receitas: "Receitas",
    despesas: "Despesas",
    total: "Total",
    semDespesas: "Sem despesas neste mês.",
    // A fatia que junta as categorias mais pequenas (não é a categoria "outros").
    restoSoma: "Restantes categorias",
  } as const,

  // Cartão "Resumo do mês" (ResumoCartao, GET /resumo).
  TEXTOS_RESUMO_MES: {
    titulo: "Resumo do mês",
    aCarregar: "A IA está a analisar o mês...",
    erro: "O resumo não está disponível. Tenta mais tarde.",
    atencao: "⚠ Atenção: ",
    nota: "ℹ Nota: ",
  } as const,

  // Chat do dashboard. Os exemplos aparecem entre aspas, separados por vírgulas e "ou" antes do último.
  TEXTOS_CHAT: {
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
  } as const,

  // Cartões das propostas do chat (CartaoProposta): a IA propõe, a pessoa confirma. {valor} e {data} já formatados.
  // TEXTO NOVO (todo o bloco)
  TEXTOS_PROPOSTAS: {
    rotulo: "Proposta da IA",
    criar: "Criar: \"{descricao}\" ({data}, {valor}) em {categoria}. Método: {metodo}.",
    criarNota: "Com a nota \"{nota}\".",
    mudarCategoria: "Mudar a categoria de \"{descricao}\" ({data}, {valor}) de {de} para {para}.",
    semCategoria: "(sem categoria)",
    mudarNota: "Mudar a nota de \"{descricao}\" ({data}, {valor}) para \"{nota}\".",
    apagarNota: "Apagar a nota de \"{descricao}\" ({data}, {valor}).",
    apagar: "Apagar: \"{descricao}\" ({data}, {valor}).",
    aviso: "Proposto pela IA: confere os valores. Nada muda até carregares em Confirmar.",
    confirmar: "Confirmar",
    aGravar: "A guardar...",
    cancelar: "Cancelar",
    feito: "Feito.",
    cancelado: "Cancelado.",
    naoExiste: "Esta movimentação já não existe.",
    erro: "Não foi possível fazer esta alteração. Tenta outra vez.",
  } as const,
};

export type TextosDashboard = Traducao<typeof PT>;

// ===== BR (PT-BR) =====
// Textos PT-BR do copywriter (passo 7). Mesmas chaves e mesmos {placeholders} do PT; o tipo obriga a ter todas
// as chaves (o `npx tsc --noEmit` falha se faltar alguma).
const BR: TextosDashboard = {
  TEXTOS_DASHBOARD: {
    etiquetaTopo: "Resumo financeiro",
    titulo: "Visão geral",
    rotuloMes: "Mês",
    erroCarregar: "Não foi possível carregar os dados. Confira se a API está rodando.",

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
  },

  // Legendas e textos dos gráficos do dashboard (GraficoMensal e GraficoCategorias).
  TEXTOS_GRAFICOS: {
    receitas: "Receitas",
    despesas: "Despesas",
    total: "Total",
    semDespesas: "Sem despesas neste mês.",
    restoSoma: "Demais categorias",
  },

  // Cartão "Resumo do mês" (ResumoCartao, GET /resumo).
  TEXTOS_RESUMO_MES: {
    titulo: "Resumo do mês",
    aCarregar: "A IA está analisando o mês...",
    erro: "O resumo não está disponível. Tente mais tarde.",
    atencao: "⚠ Atenção: ",
    nota: "ℹ Nota: ",
  },

  // Chat do dashboard. Os exemplos aparecem entre aspas, separados por vírgulas e "ou" antes do último.
  TEXTOS_CHAT: {
    titulo: "Pergunte sobre suas finanças",
    exemplos: [
      "Com o que eu gastei mais este mês?",
      "Quanto transferi para a Rita este mês?",
      "Quanto gastei com combustível nos últimos 3 meses?",
    ],
    experimenta: "Experimente: {exemplos}",
    ou: "ou",
    aPensar: "Consultando seus dados...",
    erro: "O chat falhou. Tente mais tarde.",
    marcador: "Escreva uma pergunta...",
    enviar: "Enviar",
  },

  // Cartões das propostas do chat (CartaoProposta): a IA propõe, a pessoa confirma.
  // TEXTO NOVO (todo o bloco)
  TEXTOS_PROPOSTAS: {
    rotulo: "Proposta da IA",
    criar: "Criar: \"{descricao}\" ({data}, {valor}) em {categoria}. Forma de pagamento: {metodo}.",
    criarNota: "Com a nota \"{nota}\".",
    mudarCategoria: "Mudar a categoria de \"{descricao}\" ({data}, {valor}) de {de} para {para}.",
    semCategoria: "(sem categoria)",
    mudarNota: "Mudar a nota de \"{descricao}\" ({data}, {valor}) para \"{nota}\".",
    apagarNota: "Apagar a nota de \"{descricao}\" ({data}, {valor}).",
    apagar: "Apagar: \"{descricao}\" ({data}, {valor}).",
    aviso: "Proposto pela IA: confira os valores. Nada muda até você clicar em Confirmar.",
    confirmar: "Confirmar",
    aGravar: "Salvando...",
    cancelar: "Cancelar",
    feito: "Feito.",
    cancelado: "Cancelado.",
    naoExiste: "Esta movimentação não existe mais.",
    erro: "Não foi possível fazer esta alteração. Tente de novo.",
  },
};

export const DICIONARIO_DASHBOARD: Dicionario<TextosDashboard> = { PT, BR };
