// Configuração dos planos: ordem, limites de reserva, preços e contactos para "Pedir acesso".
// As regras a sério (limites, quem tem acesso) estão no backend (limites.py, auth.py); isto é só para mostrar.

import type { EstadoPlano, Periodo } from "./api";
import type { Formatos } from "./formatos";
// Os textos chegam por argumento (t): nos componentes da app, useTextos(DICIONARIO_PLANOS); nas páginas públicas,
// DICIONARIO_PLANOS.PT.
import type { TextosPlanos } from "./textosPlanos";

export type IdPlano = "free" | "essencial" | "completo";

// Do mais pequeno para o maior: "planos superiores" são os que vêm depois do atual.
export const ORDEM_PLANOS: IdPlano[] = ["free", "essencial", "completo"];

export const NOMES_PLANOS: Record<IdPlano, string> = { free: "Free", essencial: "Essencial", completo: "Completo" };

// Pedidos à IA de um plano e o período em que se contam (o Free conta por mês, os pagos por dia),
// os extratos PDF por mês (0 no Free, que não importa PDF), os meses que o chat vê (null = todo o histórico)
// e as mensagens anteriores que o chat recebe (0 = cada pergunta à parte).
export type LimitePlano = {
  limite: number;
  periodo: Periodo;
  limitePdf: number;
  mesesHistorico: number | null;
  memoriaMensagens: number;
};

// Só para quando GET /planos falha ou a API ainda está a acordar. Os números certos vêm sempre da API
// (LIMITES_POR_PLANO, LIMITES_PDF_POR_PLANO e ConfigIA em limites.py); se lá mudarem, mudar também aqui.
export const LIMITES_RESERVA: Record<IdPlano, LimitePlano> = {
  free: { limite: 30, periodo: "mes", limitePdf: 0, mesesHistorico: 3, memoriaMensagens: 0 },
  essencial: { limite: 20, periodo: "dia", limitePdf: 15, mesesHistorico: 12, memoriaMensagens: 4 },
  completo: { limite: 50, periodo: "dia", limitePdf: 30, mesesHistorico: null, memoriaMensagens: 10 },
};

// "30 pedidos à IA por mês" / "20 pedidos à IA por dia".
export function textoDosPedidos({ limite, periodo }: LimitePlano, t: TextosPlanos): string {
  return preencher(periodo === "mes" ? t.TEXTOS_PRECOS.pedidosPorMes : t.TEXTOS_PRECOS.pedidosPorDia, { limite });
}

// "O chat vê o mês atual e os 2 anteriores" / "O chat vê todo o teu histórico".
export function textoDoHistorico(mesesHistorico: number | null, t: TextosPlanos): string {
  if (mesesHistorico === null) return t.TEXTOS_PRECOS.chatTodoHistorico;
  return preencher(t.TEXTOS_PRECOS.chatMeses, { anteriores: Math.max(mesesHistorico - 1, 0) });
}

// "O chat responde a cada pergunta à parte" / "O chat segue a conversa: lembra-se das últimas 4 mensagens".
export function textoDaMemoria(memoriaMensagens: number, t: TextosPlanos): string {
  if (memoriaMensagens <= 0) return t.TEXTOS_PRECOS.chatSemMemoria;
  return preencher(t.TEXTOS_PRECOS.chatMemoria, { n: memoriaMensagens });
}

// Os pontos de um cartão de plano: os pedidos à IA, a importação (PDF nos pagos, CSV no Free), o que o chat
// vê e guarda (e, no Completo, a análise mais cuidada) e os pontos fixos do cartão.
export function pontosDoCartao(id: IdPlano, limite: LimitePlano, t: TextosPlanos): string[] {
  const importacao =
    limite.limitePdf > 0 ? preencher(t.TEXTOS_PRECOS.pdfPorMes, { limitePdf: limite.limitePdf }) : t.TEXTOS_PRECOS.importarCsv;
  const analise = id === "completo" ? [t.TEXTOS_PRECOS.analiseCuidada] : [];
  return [
    textoDosPedidos(limite, t),
    importacao,
    textoDoHistorico(limite.mesesHistorico, t),
    textoDaMemoria(limite.memoriaMensagens, t),
    ...analise,
    ...t.TEXTOS_CARTOES[id].pontos,
  ];
}

// --- Aviso aos 80% dos pedidos à IA ---
// A API conta e bloqueia (429); isto só decide quando mostrar o aviso antes de o limite chegar.

export const PERCENTAGEM_AVISO_QUOTA = 0.8;

// Se já se usou 80% (ou mais) dos pedidos do período, mas ainda não todos (aí aparece o AvisoLimite).
export function deveAvisarQuota({ usadas, limite }: Pick<EstadoPlano, "usadas" | "limite">): boolean {
  return limite > 0 && usadas >= limite * PERCENTAGEM_AVISO_QUOTA && usadas < limite;
}

// O texto completo do aviso (topo do chat) e se leva o link "Mudar de plano" (no Completo não há plano maior).
export function avisoDeQuota(estado: EstadoPlano, t: TextosPlanos): { texto: string; mostrarLink: boolean } | null {
  if (!deveAvisarQuota(estado)) return null;
  const valores = { usadas: estado.usadas, limite: estado.limite };
  if (estado.plano === "completo") {
    return { texto: preencher(t.TEXTOS_AVISO_QUOTA.avisoCompleto, valores), mostrarLink: false };
  }
  const modelo = estado.periodo === "mes" ? t.TEXTOS_AVISO_QUOTA.avisoMes : t.TEXTOS_AVISO_QUOTA.avisoDia;
  return { texto: preencher(modelo, valores), mostrarLink: true };
}

// O texto curto, para o cartão do menu lateral: "Faltam 4 pedidos à IA".
export function avisoCurtoDeQuota(estado: EstadoPlano, t: TextosPlanos): string | null {
  if (!deveAvisarQuota(estado)) return null;
  const restantes = estado.limite - estado.usadas;
  if (restantes === 1) return t.TEXTOS_AVISO_QUOTA.avisoCurtoUm;
  return preencher(t.TEXTOS_AVISO_QUOTA.avisoCurto, { restantes });
}

// Importar PDF e ler talões são só dos planos pagos (FUNCOES_PAGAS em limites.py). Isto só decide o que se
// mostra: quem decide a sério é a API (responde 402).
export function temFuncoesPagas(plano: string | null | undefined): boolean {
  return plano === "essencial" || plano === "completo";
}

// Preço de cada plano pago, em euros com IVA incluído: por mês e por ano (preço de lançamento).
// null = ainda não definido (mostra "Preço em breve").
// Quem define os preços é o CEO: não mudar estes valores sem o OK dele.
export type Preco = { mensal: number; anual: number };
export const PRECOS: Record<Exclude<IdPlano, "free">, Preco | null> = {
  essencial: { mensal: 4.99, anual: 49 },
  completo: { mensal: 8.99, anual: 89 },
};

// 4.99 -> "4,99 €" e 49 -> "49 €" (sem ",00" nos valores certos).
export function formatarEuros(valor: number): string {
  const casas = Number.isInteger(valor) ? 0 : 2;
  return valor.toLocaleString("pt-PT", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

export function eIdPlano(valor: string | null | undefined): valor is IdPlano {
  return valor === "free" || valor === "essencial" || valor === "completo";
}

export function nomeDoPlano(plano: string | null | undefined): string | null {
  if (!plano) return null;
  return eIdPlano(plano) ? NOMES_PLANOS[plano] : plano;
}

// Os planos acima do atual (sem plano conhecido: todos os pagos).
export function planosSuperiores(atual: string | null | undefined): IdPlano[] {
  const posicao = eIdPlano(atual) ? ORDEM_PLANOS.indexOf(atual) : 0;
  return ORDEM_PLANOS.slice(posicao + 1);
}

// Troca {chave} pelo valor: preencher("Ativo até {data}", { data: "1/1" }) -> "Ativo até 1/1".
export function preencher(texto: string, valores: Record<string, string | number>): string {
  return texto.replace(/\{(\w+)\}/g, (inteira, chave: string) => (chave in valores ? String(valores[chave]) : inteira));
}

// --- Contactos ---
// Lidos do .env.local (NEXT_PUBLIC_ chega ao browser: só contactos públicos, nunca segredos).
// O Next.js troca process.env.NEXT_PUBLIC_... pelo valor na compilação, por isso têm de estar escritos por extenso.

export type Contactos = { whatsapp: string | null; email: string | null };

export function lerContactos(
  whatsapp = process.env.NEXT_PUBLIC_CONTACTO_WHATSAPP,
  email = process.env.NEXT_PUBLIC_CONTACTO_EMAIL,
): Contactos {
  const digitos = (whatsapp ?? "").replace(/\D/g, ""); // wa.me só aceita dígitos (ex.: 351912345678)
  const limpo = (email ?? "").trim();
  return { whatsapp: digitos || null, email: limpo || null };
}

export const CONTACTOS = lerContactos();

export type Pedido = { plano: IdPlano; renovar: boolean; emailConta: string | null };

// A mensagem pré-preenchida. Sem email da conta (página pública sem sessão), a frase do email sai.
export function mensagemDoPedido({ plano, renovar, emailConta }: Pedido, t: TextosPlanos): string {
  const modelo = renovar ? t.TEXTOS_MENSAGEM.mensagemRenovar : t.TEXTOS_MENSAGEM.mensagem;
  const semEmail = emailConta ? modelo : modelo.replace(t.FRASE_EMAIL, "");
  return preencher(semEmail, { plano: NOMES_PLANOS[plano], email: emailConta ?? "" });
}

export function assuntoDoPedido({ plano, renovar }: Pedido, t: TextosPlanos): string {
  const modelo = renovar ? t.TEXTOS_MENSAGEM.emailAssuntoRenovar : t.TEXTOS_MENSAGEM.emailAssunto;
  return preencher(modelo, { plano: NOMES_PLANOS[plano] });
}

export function linkWhatsapp(numero: string, pedido: Pedido, t: TextosPlanos): string {
  return `https://wa.me/${numero}?text=${encodeURIComponent(mensagemDoPedido(pedido, t))}`;
}

export function linkEmail(email: string, pedido: Pedido, t: TextosPlanos): string {
  const assunto = encodeURIComponent(assuntoDoPedido(pedido, t));
  const corpo = encodeURIComponent(mensagemDoPedido(pedido, t));
  return `mailto:${email}?subject=${assunto}&body=${corpo}`;
}

// --- Datas ---

// "2026-12-31" -> "31 de dezembro de 2026". f: os formatos da conta (useFormatos(); FORMATOS_PADRAO fora da app).
export function dataPorExtenso(iso: string, f: Formatos): string {
  return f.data(iso, { day: "numeric", month: "long", year: "numeric" });
}

// Dias que faltam até ao último dia do plano (0 = acaba hoje; negativo = já acabou).
export function diasAteAoFim(iso: string, hoje: Date = new Date()): number {
  const fim = new Date(`${iso}T00:00:00`);
  const inicioHoje = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate());
  return Math.round((fim.getTime() - inicioHoje.getTime()) / 86_400_000);
}

// O aviso de renovar aparece nos últimos 7 dias do plano: faltam 6 dias, 5... até ao próprio dia (0).
export function deveAvisarRenovar(iso: string | null, hoje: Date = new Date()): boolean {
  if (!iso) return false;
  const dias = diasAteAoFim(iso, hoje);
  return dias >= 0 && dias < 7;
}

// Junta os limites que vieram de GET /planos aos de reserva (um plano em falta fica com o de reserva).
// Uma API antiga, sem periodo, conta por dia (era assim antes de o Free passar a contar por mês);
// sem limite_pdf, meses_historico ou memoria_mensagens, fica o de reserva (meses_historico null = todo o histórico).
export function juntarLimites(
  lista:
    | {
        plano: string;
        limite_diario: number;
        periodo?: Periodo;
        limite_pdf?: number;
        meses_historico?: number | null;
        memoria_mensagens?: number;
      }[]
    | null,
): Record<IdPlano, LimitePlano> {
  const limites = { ...LIMITES_RESERVA };
  for (const { plano, limite_diario, periodo, limite_pdf, meses_historico, memoria_mensagens } of lista ?? []) {
    if (eIdPlano(plano)) {
      const reserva = LIMITES_RESERVA[plano];
      limites[plano] = {
        limite: limite_diario,
        periodo: periodo === "mes" ? "mes" : "dia",
        limitePdf: typeof limite_pdf === "number" ? limite_pdf : reserva.limitePdf,
        // Só null (todo o histórico) ou um inteiro >= 1; outro valor fica com o de reserva.
        mesesHistorico:
          meses_historico === null || (Number.isInteger(meses_historico) && (meses_historico as number) >= 1)
            ? (meses_historico as number | null)
            : reserva.mesesHistorico,
        // A API corta a memória por pares (pergunta + resposta), por isso o texto mostra um número par.
        memoriaMensagens:
          Number.isInteger(memoria_mensagens) && (memoria_mensagens as number) >= 0
            ? (memoria_mensagens as number) - ((memoria_mensagens as number) % 2)
            : reserva.memoriaMensagens,
      };
    }
  }
  return limites;
}

// O mês atual no formato da API ("AAAA-MM"). Serve de mês inicial numa conta ainda sem movimentações.
export function mesAtual(agora: Date = new Date()): string {
  return `${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, "0")}`;
}
