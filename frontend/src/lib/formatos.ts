// Formatos de dinheiro, números e datas por país (PT/BR) e moeda (EUR/BRL). Fase 1 Brasil, passo 4.
// Funções puras: recebem o país e a moeda. Nos componentes da app usar useFormatos() (lib/conta.tsx),
// que já as traz ligadas à conta. Sem conta (páginas públicas) fica sempre PT/EUR.
// Em PT o resultado é igual ao que a app mostrava antes (toLocaleString("pt-PT", ...)).

export type Pais = "PT" | "BR";
export type Moeda = "EUR" | "BRL";
export type Conta = { pais: Pais; moeda: Moeda; paisesBancos: Pais[] };

export const CONTA_PADRAO: Conta = { pais: "PT", moeda: "EUR", paisesBancos: ["PT"] };

export function ePais(valor: unknown): valor is Pais {
  return valor === "PT" || valor === "BR";
}

export function eMoeda(valor: unknown): valor is Moeda {
  return valor === "EUR" || valor === "BRL";
}

// "pt-PT" ou "pt-BR": a língua do país onde a pessoa vive (decide vírgulas, espaços e nomes dos meses).
export function localeDe(pais: Pais): string {
  return pais === "BR" ? "pt-BR" : "pt-PT";
}

// "€" ou "R$" (para rótulos como "Valor (€)").
export function simboloMoeda(moeda: Moeda): string {
  return moeda === "BRL" ? "R$" : "€";
}

// "euros" ou "reais" (para frases como "Valor que juntaste, em euros").
export function nomeMoeda(moeda: Moeda): string {
  return moeda === "BRL" ? "reais" : "euros";
}

// casas: 2 (sempre, ex. "1234,56 €"), 0 (sem cêntimos, ex. "10 000 €") ou "auto" (sem ",00" nos valores certos).
export type Casas = 0 | 2 | "auto";

// PT/EUR: 1234.5 -> "1234,50 €". BR/BRL: 1234.5 -> "R$ 1.234,50".
export function dinheiro(valor: number, pais: Pais, moeda: Moeda, casas: Casas = 2): string {
  const n = casas === "auto" ? (Number.isInteger(valor) ? 0 : 2) : casas;
  return valor.toLocaleString(localeDe(pais), {
    style: "currency",
    currency: moeda,
    minimumFractionDigits: n,
    maximumFractionDigits: n,
  });
}

// O símbolo junto a um número já escrito, com um espaço normal, do lado em que o país o escreve
// (igual ao dinheiro()): PT depois ("1500 €", "1500 R$"), BR antes ("R$ 1.500", "€ 1.500").
// Os eixos e rótulos de PT sempre foram escritos assim à mão (`${v} €`), por isso ficam iguais.
// Sem país: o da moeda (EUR -> PT, BRL -> BR), como antes.
export function comSimbolo(texto: string, moeda: Moeda, pais?: Pais): string {
  const simbolo = simboloMoeda(moeda);
  const lado = pais ?? (moeda === "BRL" ? "BR" : "PT");
  return lado === "BR" ? `${simbolo} ${texto}` : `${texto} ${simbolo}`;
}

// Eixo dos gráficos (valores redondos escolhidos pelo Recharts). PT/EUR: 1500 -> "1500 €", 10000 -> "10 000 €".
// BR/BRL: 1500 -> "R$ 1.500". Não arredonda: o eixo mostra o valor que o gráfico dá.
export function dinheiroEixo(valor: number, pais: Pais, moeda: Moeda): string {
  return comSimbolo(numero(valor, pais), moeda, pais);
}

// Eixo do simulador, em forma curta para caber no eixo com valores grandes (até 10 000/mês durante 40 anos):
// PT/EUR: 450 -> "450 €", 12000 -> "12 mil €", 18459000 -> "18,5 M €". BR/BRL: "R$ 12 mil", "R$ 18,5 mi".
export function dinheiroMil(valor: number, pais: Pais, moeda: Moeda): string {
  const texto = (valor || 0) // "|| 0": sem "-0"
    .toLocaleString(localeDe(pais), { notation: "compact", maximumFractionDigits: 1 })
    .replace(/\s/g, " ");
  return comSimbolo(texto, moeda, pais);
}

// Números sem moeda: 1.5 -> "1,5" (quantidades, percentagens).
export function numero(valor: number, pais: Pais): string {
  return valor.toLocaleString(localeDe(pais));
}

// Datas. Aceita "AAAA-MM", "AAAA-MM-DD" (lidas na hora local), outro texto ISO (ex. timestamp) ou um Date.
// Sem opções: "28/10/2026" (dia/mês/ano nos dois países).
export function data(iso: string | Date, pais: Pais, opcoes?: Intl.DateTimeFormatOptions): string {
  return paraDate(iso).toLocaleDateString(localeDe(pais), opcoes);
}

function paraDate(iso: string | Date): Date {
  if (iso instanceof Date) return iso;
  if (/^\d{4}-\d{2}$/.test(iso)) return new Date(`${iso}-01T00:00:00`);
  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) return new Date(`${iso}T00:00:00`);
  return new Date(iso);
}

// As mesmas funções, já ligadas a uma conta (o que useFormatos() devolve).
export function criarFormatos(conta: Conta) {
  const { pais, moeda } = conta;
  return {
    pais,
    moeda,
    simbolo: simboloMoeda(moeda),
    nomeMoeda: nomeMoeda(moeda),
    comSimbolo: (texto: string) => comSimbolo(texto, moeda, pais),
    dinheiro: (valor: number, casas?: Casas) => dinheiro(valor, pais, moeda, casas),
    dinheiroEixo: (valor: number) => dinheiroEixo(valor, pais, moeda),
    dinheiroMil: (valor: number) => dinheiroMil(valor, pais, moeda),
    numero: (valor: number) => numero(valor, pais),
    data: (iso: string | Date, opcoes?: Intl.DateTimeFormatOptions) => data(iso, pais, opcoes),
    // "2026-10" -> "out. 2026" (seletores de mês e eixo do gráfico mensal)
    mesAno: (mes: string) => data(mes, pais, { month: "short", year: "numeric" }),
  };
}

export type Formatos = ReturnType<typeof criarFormatos>;

// Para código fora da app (páginas públicas) e valores por omissão.
export const FORMATOS_PADRAO: Formatos = criarFormatos(CONTA_PADRAO);
