// Formatação partilhada pelos cartões e gráficos do dashboard.

export function euros(valor: number) {
  return valor.toLocaleString("pt-PT", { style: "currency", currency: "EUR" });
}

// "2026-10" -> "out. 2026"
export function nomeMes(mes: string) {
  return new Date(`${mes}-01T00:00:00`).toLocaleDateString("pt-PT", { month: "short", year: "numeric" });
}

// Caixa que aparece ao passar o rato, com as cores do tema.
export const ESTILO_TOOLTIP = {
  background: "var(--cartao)",
  borderColor: "var(--borda)",
  color: "var(--texto)",
  borderRadius: 8,
  fontSize: 13,
};
