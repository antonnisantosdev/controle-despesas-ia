// Textos dos pagamentos que se repetem (GET /recorrentes, sem IA).
// Revistos pelo copywriter (versão A, Fase 2).
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).
// Fase 1 Brasil, passo 6: dicionário { PT, BR }. Nos componentes: const { TEXTOS_... } = useTextos(DICIONARIO_RECORRENTES)
// (lib/textos.ts), que escolhe pelo país da conta. Fora da app (páginas públicas) é sempre o PT.

import type { Dicionario, Traducao } from "./textos";

const PT = {
  TEXTOS_RECORRENTES: {
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
  },
};

export type TextosRecorrentes = Traducao<typeof PT>;

// ===== BR (PT-BR) =====
// Textos PT-BR do copywriter (passo 7). Mesmas chaves e mesmos {placeholders} do PT; o tipo obriga a ter todas
// as chaves (o `npx tsc --noEmit` falha se faltar alguma).
const BR: TextosRecorrentes = {
  TEXTOS_RECORRENTES: {
    titulo: "Pagamentos que se repetem",
    explicacao: "Assinaturas, academia, aluguel: as despesas que saem da sua conta todo mês. Aparecem aqui quando se repetem há pelo menos 3 meses seguidos, uma vez por mês, com a mesma descrição e um valor parecido. Não gasta pedidos à IA.",
    totalPorMes: "Cerca de {total} por mês",
    porMes: "{valor}/mês",
    detalhe: "Há {meses} meses seguidos · último em {data}",
    subiu: "Subiu de {antes} para {depois}",
    desceu: "Caiu de {antes} para {depois}",
    vazio: "Ainda não encontramos pagamentos que se repetem. Precisamos de pelo menos 3 meses seguidos de movimentações, incluindo o mês atual ou o anterior. Importe os extratos dos últimos meses para vê-los aqui.",
    erro: "Não foi possível carregar os pagamentos que se repetem.",
    aCarregar: "Buscando...",
    // Cartão do dashboard
    tituloCurto: "Pagamentos mensais",
    resumoCurto: "{quantos} pagamentos que se repetem, cerca de {total} por mês.",
    resumoCurtoUm: "1 pagamento que se repete, cerca de {total} por mês.",
    verTodos: "Ver no Planejamento",
  },
};

export const DICIONARIO_RECORRENTES: Dicionario<TextosRecorrentes> = { PT, BR };
