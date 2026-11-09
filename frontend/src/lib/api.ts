// Endereço da API em FastAPI, lido do .env.local.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const CHAVE_TOKEN = "token";

// O token do login fica guardado no browser (localStorage) e é enviado em cada pedido à API.
export function guardarToken(token: string) {
  localStorage.setItem(CHAVE_TOKEN, token);
}

export function lerToken(): string | null {
  return localStorage.getItem(CHAVE_TOKEN);
}

export function apagarToken() {
  localStorage.removeItem(CHAVE_TOKEN);
}

// Formatos das respostas do dashboard (os mesmos modelos Pydantic do backend, em TypeScript).
export type ResumoMensal = { mes: string; receitas: number; despesas: number };
export type GastoCategoria = { categoria: string; total: number };
export type RespostaChat = { resposta: string };
export type Transacao = {
  id: number;
  data: string;
  descricao: string;
  valor: number;
  categoria: string | null;
  metodo_pagamento: string | null;
};
export type LinhaOrcamento = { categoria: string; limite: number | null; gasto: number };
export type SugestaoCategoria = { categoria: string; limite: number; explicacao: string };
export type SugestaoOrcamento = { sugestoes: SugestaoCategoria[] };
export type ResultadoImportacao = { importadas: number; duplicadas: number; transacoes: Transacao[] };
export type Alerta = { nivel: "info" | "atencao"; mensagem: string };
export type ResumoMes = { resumo: string; alertas: Alerta[] };
export type ItemTalao = { descricao: string; quantidade: number; preco: number };
// O que a IA leu da fotografia (POST /compras/ler). A data vem null se não for legível.
export type Talao = { loja: string; data: string | null; itens: ItemTalao[]; total: number; categoria: string };
export type Compra = { id: number; transacao_id: number; loja: string; data: string; total: number; itens: ItemTalao[] };
export type Objetivo = { id: number; nome: string; valor_alvo: number; data_alvo: string; valor_poupado: number };
export type CorteSugerido = { categoria: string; valor_mensal: number; motivo: string };
export type PlanoPoupanca = { viavel: boolean; explicacao: string; cortes: CorteSugerido[] };
// Um ano do simulador de poupança (GET /simulador).
export type AnoSimulado = { ano: number; depositado: number; valor: number };
// O plano do utilizador, os pedidos à IA que já fez hoje e o último dia do plano (GET /plano).
// ativo_ate vem em ISO ("2026-12-31"), ou null no Free (não acaba).
export type EstadoPlano = { plano: string | null; limite: number; usadas_hoje: number; ativo_ate: string | null };
// Um plano à venda e o seu limite diário (GET /planos, público).
export type PlanoDisponivel = { plano: string; limite_diario: number };

// O email da conta, lido do próprio token do Supabase (um JWT: a parte do meio é JSON em base64url).
// Serve só para pré-preencher mensagens; não é verificação nenhuma (essa é feita pela API).
export function emailDaSessao(): string | null {
  const token = lerToken();
  const parte = token?.split(".")[1];
  if (!parte) return null;
  try {
    // base64url -> base64 (com o "=" final que o JWT corta) -> bytes -> texto em UTF-8.
    // O atob sozinho devolve um byte por letra e estragava emails com acentos (ex.: "joão@...").
    const base64 = parte.replace(/-/g, "+").replace(/_/g, "/");
    const completo = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    const bytes = Uint8Array.from(atob(completo), (letra) => letra.charCodeAt(0));
    const dados = JSON.parse(new TextDecoder().decode(bytes));
    return typeof dados.email === "string" ? dados.email : null;
  } catch {
    return null;
  }
}

// Lançado quando a API responde 401: o token não existe, é inválido ou expirou.
export class SessaoExpirada extends Error {}

// Lançado quando a API responde com outro erro. Guarda o código (422, 503...) e o "detail"
// que o FastAPI enviou, para a página poder mostrar a explicação certa.
export class ErroApi extends Error {
  status: number;
  detalhe: unknown;

  constructor(status: number, detalhe: unknown) {
    super(`A API respondeu ${status}`);
    this.status = status;
    this.detalhe = detalhe;
  }
}

function lerTokenOuFalhar(): string {
  const token = lerToken();
  if (!token) {
    throw new SessaoExpirada();
  }
  return token;
}

// O que todas as respostas têm em comum: 401 -> SessaoExpirada, outro erro -> ErroApi, sucesso -> JSON.
async function lerResposta<T>(resposta: Response): Promise<T> {
  if (resposta.status === 401) {
    throw new SessaoExpirada();
  }
  // 403 = sem assinatura ativa. Vale para a app inteira, por isso trata-se aqui e não em cada página.
  if (resposta.status === 403) {
    // Aqui não há useRouter (não é um componente). Um recarregamento completo da página
    // não faz mal: só acontece quando o acesso termina.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign("/assinatura-expirada");
  }
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null);
    throw new ErroApi(resposta.status, corpo?.detail);
  }
  // 204 No Content (ex.: depois de apagar): não há corpo, e resposta.json() daria erro.
  if (resposta.status === 204) {
    return undefined as T;
  }
  return await resposta.json();
}

// --- Novas tentativas quando a API está a acordar ---
// No plano gratuito do Render, a API adormece depois de 15 minutos sem pedidos e demora até
// um minuto a arrancar. Entretanto, os pedidos falham por rede ou com 502/503/504.
// Em vez de mostrar logo um erro, a app espera e tenta outra vez.

// Segundos de espera antes de cada nova tentativa: cerca de 1 minuto no total.
const ESPERAS_SEGUNDOS = [2, 4, 8, 15, 15, 15];

// Os componentes ouvem este evento para mostrar "A acordar o servidor..." (AvisoServidor.tsx).
export const EVENTO_A_ACORDAR = "api-a-acordar";

function avisarAAcordar(aAcordar: boolean) {
  window.dispatchEvent(new CustomEvent(EVENTO_A_ACORDAR, { detail: aAcordar }));
}

// Decide se um pedido que falhou deve ser repetido.
// status é null quando nem houve resposta (erro de rede, ou o browser bloqueou-a por CORS).
function deveTentarOutraVez(metodo: string, status: number | null): boolean {
  // 502/503/504: quem respondeu foi o Render, a API nem recebeu o pedido. Repetir é seguro com qualquer método.
  if (status === 502 || status === 503 || status === 504) return true;

  // Sem resposta: não se sabe se o pedido chegou à API. Só se repetem os métodos idempotentes
  // (repetir dá o mesmo resultado). Um POST repetido podia gravar duas vezes ou contar duas perguntas à IA.
  if (status === null) return metodo === "GET" || metodo === "PUT" || metodo === "DELETE";

  // 401, 403, 422, 429...: respostas da própria API, que não mudam se se tentar outra vez.
  return false;
}

// Um fetch que, se a API estiver a acordar, espera e tenta outra vez (até ao fim de ESPERAS_SEGUNDOS).
export async function fetchComTentativas(url: string, opcoes: RequestInit = {}): Promise<Response> {
  const metodo = opcoes.method ?? "GET";
  try {
    for (let tentativa = 0; ; tentativa++) {
      let resposta: Response | null = null;
      let erroRede: unknown = null;
      try {
        resposta = await fetch(url, opcoes);
      } catch (e) {
        erroRede = e;
      }

      const esgotou = tentativa >= ESPERAS_SEGUNDOS.length;
      if (esgotou || !deveTentarOutraVez(metodo, resposta?.status ?? null)) {
        if (resposta) return resposta;
        throw erroRede;
      }

      avisarAAcordar(true);
      await new Promise((r) => setTimeout(r, ESPERAS_SEGUNDOS[tentativa] * 1000));
    }
  } finally {
    avisarAAcordar(false);
  }
}

// Faz um pedido à API com o token do login e devolve o JSON da resposta.
// Sem corpo é um GET; com corpo é um POST com esse objeto em JSON (ou outro método, se for indicado).
export async function pedirApi<T>(caminho: string, corpo?: object, metodo?: "POST" | "PATCH" | "PUT" | "DELETE"): Promise<T> {
  const token = lerTokenOuFalhar();
  const resposta = await fetchComTentativas(`${API_URL}${caminho}`, {
    method: metodo ?? (corpo ? "POST" : "GET"),
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  return lerResposta<T>(resposta);
}

// Envia um ficheiro (multipart/form-data, como um <form enctype="multipart/form-data"> em PHP).
// Não se põe "Content-Type": o browser escreve-o sozinho, com a "fronteira" entre as partes.
export async function enviarFicheiro<T>(caminho: string, campo: string, ficheiro: File): Promise<T> {
  const token = lerTokenOuFalhar();
  const formulario = new FormData();
  formulario.append(campo, ficheiro);
  const resposta = await fetchComTentativas(`${API_URL}${caminho}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formulario,
  });
  return lerResposta<T>(resposta);
}

// Se o erro é o 429 do limite diário de pedidos à IA (limites.py). Os ecrãs usam-no para mostrar o AvisoLimite.
export function eLimiteDiario(erro: unknown): boolean {
  return erro instanceof ErroApi && erro.status === 429;
}

// A sessão vista por uma página pública (ex.: /precos), segundo a resposta de GET /plano:
// - "sem-sessao": não há token, ou a API respondeu 401 (token inválido ou expirado);
// - "ativa": 200, com o plano de quem entrou;
// - "plano-terminado": 403, o login está certo mas o acesso acabou;
// - "desconhecida": a API falhou (rede, 5xx); não se sabe mais do que "há um token".
export type SessaoPublica =
  | { tipo: "sem-sessao" }
  | { tipo: "ativa"; estado: EstadoPlano }
  | { tipo: "plano-terminado" }
  | { tipo: "desconhecida" };

// Ao contrário do pedirApi, um 401 ou 403 não manda para outra página: só diz em que estado está a sessão.
export async function sessaoPublica(): Promise<SessaoPublica> {
  const token = lerToken();
  if (!token) return { tipo: "sem-sessao" };
  try {
    const resposta = await fetchComTentativas(`${API_URL}/plano`, { headers: { Authorization: `Bearer ${token}` } });
    if (resposta.status === 401) return { tipo: "sem-sessao" };
    if (resposta.status === 403) return { tipo: "plano-terminado" };
    if (!resposta.ok) return { tipo: "desconhecida" };
    return { tipo: "ativa", estado: await resposta.json() };
  } catch {
    return { tipo: "desconhecida" };
  }
}

// Os planos e os limites (GET /planos, público, sem token). null se a API falhar.
export async function planosDisponiveis(): Promise<PlanoDisponivel[] | null> {
  try {
    const resposta = await fetchComTentativas(`${API_URL}/planos`);
    return resposta.ok ? await resposta.json() : null;
  } catch {
    return null;
  }
}
