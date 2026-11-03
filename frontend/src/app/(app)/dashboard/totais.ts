import type { ResumoMensal } from "@/lib/api";

export type Totais = {
  entradas: number; // dinheiro que entrou no mês escolhido
  despesas: number; // dinheiro que saiu no mês escolhido
  saldoMes: number; // entradas - despesas do mês escolhido
  saldoTotal: number; // entradas - despesas de todos os meses importados
};

// Calcula os números dos cartões a partir do /dashboard/mensal, que a página já carregou.
export function calcularTotais(mensal: ResumoMensal[], mes: string): Totais {
  const resumoMes = mensal.find((m) => m.mes === mes);
  // Cada mês já traz os totais prontos (números, não listas): basta lê-los.
  const entradas = resumoMes?.receitas ?? 0;
  const despesas = resumoMes?.despesas ?? 0;

  // O saldo acumulado não vem da API: soma-se o saldo de todos os meses.
  let saldoTotal = 0;
  for (const m of mensal) {
    saldoTotal += m.receitas - m.despesas;
  }

  return { entradas, despesas, saldoMes: entradas - despesas, saldoTotal };
}
