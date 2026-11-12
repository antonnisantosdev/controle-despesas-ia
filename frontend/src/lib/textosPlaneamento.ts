// Textos da página Planeamento: orçamento por categoria e sugestão da IA.
// Passo 5 da Fase 1 Brasil: os textos saíram dos componentes .tsx sem mudar uma letra.
// Os pagamentos que se repetem estão em textosRecorrentes.ts e os alertas em textosPlanos.ts (TEXTOS_ALERTA_ORCAMENTO).
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).
// Fase 1 Brasil, passo 6: dicionário { PT, BR }. Nos componentes: const { TEXTOS_... } = useTextos(DICIONARIO_PLANEAMENTO)
// (lib/textos.ts), que escolhe pelo país da conta. Fora da app (páginas públicas) é sempre o PT.

import type { Dicionario, Traducao } from "./textos";

const PT = {
  TEXTOS_PLANEAMENTO: {
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
  } as const,

  // Uma linha do orçamento (LinhaPlaneamento).
  TEXTOS_LINHA_ORCAMENTO: {
    marcador: "Limite {simbolo}", // {simbolo}: € ou R$, conforme a moeda da conta
    rotuloCampo: "Orçamento mensal de {categoria}",
    guardar: "Guardar",
    semOrcamento: "Gastaste {gasto} · sem orçamento",
    passaste: "{gasto} de {limite} · passaste {diferenca}",
    faltam: "{gasto} de {limite} · faltam {diferenca}",
  } as const,

  // Sugestão de orçamento da IA (SugestoesIA). porMes vem a seguir ao nome da categoria (a negrito).
  TEXTOS_SUGESTOES: {
    titulo: "✨ Sugestão da IA",
    aceitarTodas: "Aceitar todas",
    fechar: "Fechar",
    semGastos: "Ainda não há gastos suficientes para sugerir um orçamento.",
    porMes: " · {valor} por mês",
    aceite: "✓ Aceite",
    aceitar: "Aceitar",
  } as const,
};

export type TextosPlaneamento = Traducao<typeof PT>;

// ===== BR (PT-BR) =====
// Textos PT-BR do copywriter (passo 7). Mesmas chaves e mesmos {placeholders} do PT; o tipo obriga a ter todas
// as chaves (o `npx tsc --noEmit` falha se faltar alguma).
const BR: TextosPlaneamento = {
  TEXTOS_PLANEAMENTO: {
    etiquetaTopo: "Orçamento mensal",
    titulo: "Planejamento",
    rotuloMes: "Mês",
    sugerir: "✨ Sugerir orçamento",
    aSugerir: "A IA está analisando...",
    erroCarregar: "Não foi possível carregar o planejamento. Confira se a API está rodando.",
    erroGuardar: "Não foi possível salvar o orçamento. Tente de novo.",
    erroSugestao: "Não foi possível pedir a sugestão. Tente de novo.",
    // "Nas categorias com orçamento, gastaste 120,00 € de 300,00 € previstos." (os valores, na moeda da conta, vão a negrito)
    totalAntes: "Nas categorias com orçamento, você gastou ",
    totalMeio: " de ",
    totalFim: " previstos.",
    aCarregar: "Carregando...",
    vazio: "Sem gastos nem orçamentos neste mês.",
    rotuloNovaCategoria: "Categoria para novo orçamento",
    adicionar: "+ Adicionar orçamento para...",
  },

  // Uma linha do orçamento (LinhaPlaneamento).
  TEXTOS_LINHA_ORCAMENTO: {
    marcador: "Limite {simbolo}", // {simbolo}: € ou R$, conforme a moeda da conta
    rotuloCampo: "Orçamento mensal de {categoria}",
    guardar: "Salvar",
    semOrcamento: "Você gastou {gasto} · sem orçamento",
    passaste: "{gasto} de {limite} · ultrapassou em {diferenca}",
    faltam: "{gasto} de {limite} · restam {diferenca}",
  },

  // Sugestão de orçamento da IA (SugestoesIA). porMes vem a seguir ao nome da categoria (a negrito).
  TEXTOS_SUGESTOES: {
    titulo: "✨ Sugestão da IA",
    aceitarTodas: "Aceitar todas",
    fechar: "Fechar",
    semGastos: "Ainda não há gastos suficientes para sugerir um orçamento.",
    porMes: " · {valor} por mês",
    aceite: "✓ Aceita",
    aceitar: "Aceitar",
  },
};

export const DICIONARIO_PLANEAMENTO: Dicionario<TextosPlaneamento> = { PT, BR };
