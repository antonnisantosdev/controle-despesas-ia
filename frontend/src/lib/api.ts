import { ePais, eMoeda, type Moeda, type Pais } from "./formatos";
import { DICIONARIO_DEMO } from "./textosDemo";

// O texto do 423 da demo fica em PT: é igual à resposta da API (demo.py), que ainda só fala PT-PT.
const { TEXTOS_DEMO } = DICIONARIO_DEMO.PT;

// Endereço da API em FastAPI, lido do .env.local.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const CHAVE_TOKEN = "token";
// Marca de que o token guardado é da demo para recrutadores (POST /demo). Só serve para o ecrã
// (faixa, botões desligados, renovar o token): quem decide o que a demo pode fazer é a API.
const CHAVE_DEMO = "sessao-demo";

// A marca "a sessão da demo terminou" (só neste separador): o login mostra o aviso TEXTOS_DEMO.sessaoTerminou.
const CHAVE_DEMO_TERMINOU = "demo-terminou";

// A marca "a conta foi apagada" (só neste separador): o login mostra TEXTOS_APAGAR_CONTA.apagada.
const CHAVE_CONTA_APAGADA = "conta-apagada";

// Os componentes ouvem este evento para saberem que a sessão mudou (ex.: entrou ou saiu da demo).
export const EVENTO_SESSAO = "sessao-mudou";

// O token do login fica guardado no browser (localStorage) e é enviado em cada pedido à API.
// demo: true só para o token do POST /demo; um login normal apaga a marca da demo.
export function guardarToken(token: string, demo = false) {
  localStorage.setItem(CHAVE_TOKEN, token);
  sessionStorage.removeItem(CHAVE_DEMO_TERMINOU); // entrou de novo: o aviso "a sessão da demo terminou" sai
  sessionStorage.removeItem(CHAVE_CONTA_APAGADA); // e o aviso "a conta foi apagada" também
  if (demo) {
    localStorage.setItem(CHAVE_DEMO, "1");
  } else {
    localStorage.removeItem(CHAVE_DEMO);
  }
  window.dispatchEvent(new Event(EVENTO_SESSAO));
}

export function lerToken(): string | null {
  return localStorage.getItem(CHAVE_TOKEN);
}

// Sair (ou sessão expirada): apaga o token, a marca da demo e o aviso "a sessão da demo terminou".
// Exceção: quando a renovação da demo falha, o enviarComToken já apagou o token e só depois põe o aviso.
// A página chama a seguir apagarToken (sem token guardado) e o aviso fica para o login o mostrar.
export function apagarToken() {
  if (localStorage.getItem(CHAVE_TOKEN) !== null) sessionStorage.removeItem(CHAVE_DEMO_TERMINOU);
  localStorage.removeItem(CHAVE_TOKEN);
  localStorage.removeItem(CHAVE_DEMO);
  window.dispatchEvent(new Event(EVENTO_SESSAO));
}

// Depois de DELETE /conta: apaga a sessão e deixa a marca para o login mostrar que a conta foi apagada.
export function terminarSessaoContaApagada() {
  apagarToken();
  sessionStorage.setItem(CHAVE_CONTA_APAGADA, "1");
  window.dispatchEvent(new Event(EVENTO_SESSAO));
}

export function contaApagada(): boolean {
  return typeof window !== "undefined" && sessionStorage.getItem(CHAVE_CONTA_APAGADA) === "1";
}

// Se a sessão guardada é da demo. false no servidor (no Next, as páginas também se desenham sem browser).
export function eSessaoDemo(): boolean {
  return typeof window !== "undefined" && localStorage.getItem(CHAVE_DEMO) === "1";
}

// Formatos das respostas do dashboard (os mesmos modelos Pydantic do backend, em TypeScript).
export type ResumoMensal = { mes: string; receitas: number; despesas: number };
export type GastoCategoria = { categoria: string; total: number };
export type RespostaChat = { resposta: string };
// Uma mensagem anterior do chat, enviada em POST /chat (memória só da sessão; a API corta-a para o plano).
export type MensagemHistorico = { papel: "utilizador" | "ia"; texto: string };
// Um pagamento que se repete todos os meses (GET /recorrentes, sem IA). ultimo_pagamento em ISO.
export type Recorrente = {
  descricao: string;
  categoria: string | null;
  valor_mensal: number;
  // O valor antes de uma mudança de preço (ex.: a assinatura subiu); null ou ausente se não mudou.
  valor_anterior?: number | null;
  meses_seguidos: number;
  ultimo_pagamento: string;
};
export type Transacao = {
  id: number;
  data: string;
  descricao: string;
  valor: number;
  categoria: string | null;
  metodo_pagamento: string | null;
};
export type LinhaOrcamento = { categoria: string; limite: number | null; gasto: number };
// Alertas de orçamento do mês atual de Lisboa (GET /orcamentos/alertas, sem IA).
export type AlertaOrcamento = { categoria: string; gasto: number; limite: number; nivel: "perto" | "atingido" };
export type AlertasOrcamento = { mes: string; alertas: AlertaOrcamento[] };
export type SugestaoCategoria = { categoria: string; limite: number; explicacao: string };
export type SugestaoOrcamento = { sugestoes: SugestaoCategoria[] };
// aviso: texto para mostrar (ex.: importou sem categorias porque acabaram os pedidos à IA). Uma API antiga não o envia.
export type ResultadoImportacao = {
  importadas: number;
  duplicadas: number;
  transacoes: Transacao[];
  aviso?: string | null;
};
export type Alerta = { nivel: "info" | "atencao"; mensagem: string };
export type ResumoMes = { resumo: string; alertas: Alerta[] };
// nome_generico: o nome "limpo" que a IA deu ao produto (para os preços por loja); unidade: un, kg ou l.
// Opcionais: uma API antiga não os envia.
export type ItemTalao = {
  descricao: string;
  quantidade: number;
  preco: number;
  nome_generico?: string | null;
  unidade?: "un" | "kg" | "l";
};
// O que a IA leu da fotografia (POST /compras/ler). A data vem null se não for legível.
export type Talao = { loja: string; data: string | null; itens: ItemTalao[]; total: number; categoria: string };
export type Compra = { id: number; transacao_id: number; loja: string; data: string; total: number; itens: ItemTalao[] };
// Preços por loja (separador Preços em Minhas compras). Só nos planos pagos: 402 no Free.
// Unidade do preço unitário: por unidade, por quilo ou por litro.
export type UnidadePreco = "un" | "kg" | "l";
// GET /compras/produtos?q=texto: máx. 50, dos comprados há menos tempo para os mais antigos.
export type ProdutoResumo = {
  chave: string;
  nome: string;
  unidades: UnidadePreco[];
  ultima_data: string;
  n_lojas: number;
  n_compras: number;
};
export type PrecoNaLoja = {
  loja: string;
  preco_recente: number;
  data_recente: string;
  preco_minimo: number;
  preco_medio: number;
  n_compras: number;
};
export type PrecoHistorico = { data: string; loja: string; preco_unitario: number };
// lojas: da mais barata agora para a mais cara. historico: do mais recente para o mais antigo (máx. 100).
export type PrecosPorUnidade = { unidade: UnidadePreco; lojas: PrecoNaLoja[]; historico: PrecoHistorico[] };
// GET /compras/produtos/{chave} (com encodeURIComponent). 404 se não existir.
export type PrecosDoProduto = { chave: string; nome: string; por_unidade: PrecosPorUnidade[] };
// GET /compras/produtos/juntar: as junções do utilizador, da mais recente para a mais antiga.
export type JuncaoProdutos = {
  chave_origem: string;
  nome_origem: string;
  chave_destino: string;
  nome_destino: string;
  criado_em: string;
};
export type Objetivo = { id: number; nome: string; valor_alvo: number; data_alvo: string; valor_poupado: number };
export type CorteSugerido = { categoria: string; valor_mensal: number; motivo: string };
export type PlanoPoupanca = { viavel: boolean; explicacao: string; cortes: CorteSugerido[] };
// Um ano do simulador de poupança (GET /simulador).
export type AnoSimulado = { ano: number; depositado: number; valor: number };
// Resumo anual (GET /relatorio?ano=AAAA). Saídas sempre positivas. Mostrar sempre a etiqueta, nunca a categoria.
export type TotaisAno = { entradas: number; saidas: number; saldo: number };
export type MesRelatorio = { mes: string; entradas: number; saidas: number; saldo: number; com_dados: boolean };
export type CategoriaRelatorio = { categoria: string; etiqueta: string; total: number; percentagem: number };
export type CategoriaComparada = {
  categoria: string;
  etiqueta: string;
  total: number;
  total_anterior: number;
  diferenca: number;
};
export type ComparacaoAno = {
  ano: number;
  meses_comparados: string[];
  meses_com_dados: number;
  totais: TotaisAno;
  categorias: CategoriaComparada[];
};
export type SaidaRelatorio = { data: string; descricao: string; valor: number; categoria: string | null; etiqueta: string };
export type RecorrenteAno = {
  descricao: string;
  categoria: string | null;
  etiqueta: string;
  valor_mensal: number;
  pagamentos_no_ano: number;
  total_no_ano: number;
};
export type ObjetivoRelatorio = {
  nome: string;
  valor_alvo: number;
  valor_poupado: number;
  data_alvo: string;
  percentagem: number;
};
export type RelatorioAnual = {
  ano: number;
  titulo: string;
  aviso: string;
  nota_categorias: string;
  ate_mes: string;
  ano_incompleto: boolean;
  meses_sem_dados: string[];
  totais: TotaisAno;
  meses: MesRelatorio[];
  categorias: CategoriaRelatorio[];
  comparacao: ComparacaoAno | null;
  maiores_saidas: SaidaRelatorio[];
  recorrentes: RecorrenteAno[];
  objetivos: ObjetivoRelatorio[];
};
export type ResumoAnualIA = { resumo: string };
// "dia" nos planos pagos, "mes" no Free: o período em que se contam os pedidos à IA (limites.py).
export type Periodo = "dia" | "mes";
// O plano do utilizador, os pedidos à IA que já fez no período e o último dia do plano (GET /plano),
// já normalizado por normalizarEstadoPlano(). ativo_ate vem em ISO ("2026-12-31"), ou null no Free (não acaba).
// plano_terminado e terminou_em: o plano pago que chegou ao fim (a conta está no Free), ou null.
// pdf_usados e pdf_limite: extratos PDF deste mês (pdf_limite 0 no Free).
// memoria_mensagens: mensagens anteriores que o chat recebe (0 no Free). meses_historico: meses que o chat vê (null = todos).
// pais: onde a pessoa vive (língua e formatos). paises_bancos: países dos cartões e contas. moeda: a moeda principal.
export type EstadoPlano = {
  plano: string | null;
  limite: number;
  periodo: Periodo;
  usadas: number;
  ativo_ate: string | null;
  plano_terminado: string | null;
  terminou_em: string | null;
  pdf_usados: number;
  pdf_limite: number;
  memoria_mensagens: number;
  meses_historico: number | null;
  pais: Pais;
  paises_bancos: Pais[];
  moeda: Moeda;
};
// O que GET /plano devolve. Uma API antiga (durante o deploy) só traz usadas_hoje e não traz periodo,
// nem os campos do plano terminado e dos PDF.
type EstadoPlanoDaApi = Pick<EstadoPlano, "plano" | "limite" | "ativo_ate"> & {
  usadas?: number;
  usadas_hoje?: number;
  periodo?: Periodo;
  plano_terminado?: string | null;
  terminou_em?: string | null;
  pdf_usados?: number;
  pdf_limite?: number;
  memoria_mensagens?: number;
  meses_historico?: number | null;
  pais?: string;
  paises_bancos?: string[];
  moeda?: string;
};

// Põe o estado sempre na forma nova, para nenhum ecrã fazer contas com undefined (NaN).
// Sem periodo, conta por dia (era assim antes de o Free passar a contar por mês).
export function normalizarEstadoPlano(bruto: EstadoPlanoDaApi): EstadoPlano {
  return {
    plano: bruto.plano,
    limite: bruto.limite,
    periodo: bruto.periodo === "mes" ? "mes" : "dia",
    usadas: bruto.usadas ?? bruto.usadas_hoje ?? 0,
    ativo_ate: bruto.ativo_ate,
    plano_terminado: bruto.plano_terminado ?? null,
    terminou_em: bruto.terminou_em ?? null,
    pdf_usados: bruto.pdf_usados ?? 0,
    pdf_limite: bruto.pdf_limite ?? 0,
    // Uma API antiga não envia a memória: sem ela, o chat não manda mensagens anteriores.
    memoria_mensagens: bruto.memoria_mensagens ?? 0,
    meses_historico: bruto.meses_historico ?? null,
    // Uma API antiga (ou um valor desconhecido) fica em Portugal e euros, como a app era antes.
    pais: ePais(bruto.pais) ? bruto.pais : "PT",
    paises_bancos: paisesDosBancos(bruto.paises_bancos),
    moeda: eMoeda(bruto.moeda) ? bruto.moeda : "EUR",
  };
}

// Só os países conhecidos, sem repetidos; vazio ou em falta -> ["PT"].
function paisesDosBancos(bruto: string[] | undefined): Pais[] {
  const paises = [...new Set((bruto ?? []).filter(ePais))];
  return paises.length > 0 ? paises : ["PT"];
}

// GET /plano, já normalizado. Usar sempre esta em vez de pedirApi("/plano").
export async function pedirEstadoPlano(): Promise<EstadoPlano> {
  return normalizarEstadoPlano(await pedirApi<EstadoPlanoDaApi>("/plano"));
}
// Um plano à venda e o seu limite de pedidos à IA no período (GET /planos, público).
// limite_diario é o nome antigo: no Free é o limite do mês.
// limite_pdf: extratos PDF por mês (uma API antiga não o envia).
// memoria_mensagens e meses_historico: o que o chat de cada plano guarda e vê (uma API antiga não os envia).
export type PlanoDisponivel = {
  plano: string;
  limite_diario: number;
  periodo: Periodo;
  limite_pdf?: number;
  memoria_mensagens?: number;
  meses_historico?: number | null;
};

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

// A mensagem que a API mandou num 422 (ex. "Chegaste ao máximo de 20 000 movimentações…"),
// ou o texto genérico quando não há uma mensagem de texto para mostrar.
// Na demo, o 423 (alteração recusada) tem sempre o texto da demo.
export function mensagemDaApi(e: unknown, generica: string): string {
  if (eBloqueadoNaDemo(e)) return TEXTOS_DEMO.bloqueado;
  if (e instanceof ErroApi && e.status === 422 && typeof e.detalhe === "string") return e.detalhe;
  return generica;
}

// Se o erro é o 423 da demo: a conta de demo tentou mudar alguma coisa (a API só a deixa ver e usar o chat).
// Nunca segue o caminho do 403 (que manda para /assinatura-expirada).
export function eBloqueadoNaDemo(erro: unknown): erro is ErroApi {
  return erro instanceof ErroApi && erro.status === 423;
}

// Os componentes ouvem este evento para mostrar a mensagem do 423 (FaixaDemo.tsx).
export const EVENTO_BLOQUEADO_DEMO = "api-bloqueado-demo";

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
  // 423 = a conta de demo tentou mudar alguma coisa. Avisa a faixa da demo e segue como um erro normal.
  if (resposta.status === 423) {
    window.dispatchEvent(new CustomEvent(EVENTO_BLOQUEADO_DEMO));
    throw new ErroApi(423, TEXTOS_DEMO.bloqueado);
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
function deveTentarOutraVez(metodo: string, resposta: Response | null): boolean {
  const status = resposta?.status ?? null;

  // 502/503/504 do Render (página HTML): a API nem recebeu o pedido. Repetir é seguro com qualquer método.
  // Um 503 em JSON vem da nossa API (ex. a IA falhou) e o pedido à IA já foi contado:
  // repetir gastaria mais pedidos do utilizador, por isso não se repete.
  if (status === 502 || status === 503 || status === 504) {
    const vemDaApi = resposta?.headers.get("content-type")?.includes("application/json") ?? false;
    return !vemDaApi;
  }

  // Sem resposta: não se sabe se o pedido chegou à API. Só se repetem os métodos idempotentes
  // (repetir dá o mesmo resultado). Um POST repetido podia gravar duas vezes ou contar duas perguntas à IA.
  if (status === null) return metodo === "GET" || metodo === "PUT" || metodo === "DELETE";

  // 401, 403, 422, 429...: respostas da própria API, que não mudam se se tentar outra vez.
  return false;
}

// Um fetch que, se a API estiver a acordar, espera e tenta outra vez (até ao fim de ESPERAS_SEGUNDOS).
async function fetchComEsperas(url: string, opcoes: RequestInit = {}): Promise<Response> {
  const metodo = (opcoes.method ?? "GET").toUpperCase();
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
      if (esgotou || !deveTentarOutraVez(metodo, resposta)) {
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

// Durante quanto tempo, depois de um GET / com 200, se considera que a API está acordada.
// O Render só adormece ao fim de 15 minutos sem pedidos, por isso 5 minutos é uma margem segura.
const MINUTOS_ACORDADA = 5;

// Até quando (Date.now(), em milissegundos) a API está de certeza acordada. 0 = não se sabe.
let acordadaAte = 0;

// Acorda a API com um GET / (não grava nada nem gasta pedidos), com as mesmas esperas e o mesmo aviso
// "A acordar o servidor...". Se falhar, não faz mal: o pedido a seguir mostra o erro verdadeiro.
async function acordarApi(): Promise<void> {
  if (Date.now() < acordadaAte) return;
  try {
    const resposta = await fetchComEsperas(`${API_URL}/`);
    if (resposta.status === 200) acordadaAte = Date.now() + MINUTOS_ACORDADA * 60 * 1000;
  } catch {
    // Sem rede: o POST a seguir falha e a página mostra o erro.
  }
}

// GET, PUT e DELETE: repetem-se enquanto a API acorda (repetir dá o mesmo resultado).
// POST e PATCH: primeiro acorda-se a API com um GET /, e só depois o pedido é enviado, uma única vez.
// Repetir um POST podia gravar duas vezes ou gastar dois pedidos à IA do utilizador.
export async function fetchComTentativas(url: string, opcoes: RequestInit = {}): Promise<Response> {
  const metodo = (opcoes.method ?? "GET").toUpperCase();
  if (metodo === "POST" || metodo === "PATCH") {
    await acordarApi();
    return fetch(url, opcoes);
  }
  return fetchComEsperas(url, opcoes);
}

// --- Demo para recrutadores ---

// POST /demo (público): devolve o token da conta de demo, ou lança ErroApi (429, 503...).
export async function pedirTokenDemo(): Promise<string> {
  const resposta = await fetchComTentativas(`${API_URL}/demo`, { method: "POST" });
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null);
    throw new ErroApi(resposta.status, corpo?.detail);
  }
  const dados = await resposta.json();
  return dados.access_token;
}

// A renovação em curso: vários pedidos com 401 ao mesmo tempo (o dashboard faz uns 6) partilham
// um só POST /demo, para não gastarem as entradas por hora do IP.
// O token da demo dura 60 minutos e não se renova: quando dá 401, pede-se um novo ao POST /demo.
// falhou: o token que deu 401. Se, entretanto, o token guardado mudou (ex.: login noutro separador),
// o novo da demo não se guarda (não se pisa essa sessão) e devolve null.
let renovacaoDemo: Promise<string | null> | null = null;

function renovarTokenDemo(falhou: string): Promise<string | null> {
  if (!renovacaoDemo) {
    renovacaoDemo = pedirTokenDemo()
      .then((token) => {
        if (lerToken() !== falhou) return null;
        guardarToken(token, true);
        return token;
      })
      .finally(() => {
        renovacaoDemo = null;
      });
  }
  return renovacaoDemo;
}

export function demoTerminou(): boolean {
  return typeof window !== "undefined" && sessionStorage.getItem(CHAVE_DEMO_TERMINOU) === "1";
}

// Envia o pedido com o token guardado. Numa sessão de demo, um 401 (token expirado) pede um token novo
// uma única vez e repete o pedido. O 401 quer dizer que a API não fez nada, por isso repetir é seguro.
async function enviarComToken(enviar: (token: string) => Promise<Response>): Promise<Response> {
  const usado = lerTokenOuFalhar();
  const resposta = await enviar(usado);
  if (resposta.status !== 401 || !eSessaoDemo()) return resposta;
  let novo: string | null;
  try {
    novo = await renovarTokenDemo(usado);
  } catch {
    // Não deu para renovar: segue o 401 (SessaoExpirada) e o login explica que a sessão da demo terminou.
    // Primeiro apaga-se o token, depois põe-se o aviso (ver apagarToken).
    if (lerToken() === usado) apagarToken();
    sessionStorage.setItem(CHAVE_DEMO_TERMINOU, "1");
    window.dispatchEvent(new Event(EVENTO_SESSAO));
    return resposta;
  }
  // Entretanto entrou outra sessão neste browser (ex.: login noutro separador): não se repete o pedido
  // com o token dela. Segue o 401 original.
  if (novo === null) return resposta;
  return enviar(novo);
}

// Faz um pedido à API com o token do login e devolve o JSON da resposta.
// Sem corpo é um GET; com corpo é um POST com esse objeto em JSON (ou outro método, se for indicado).
export async function pedirApi<T>(caminho: string, corpo?: object, metodo?: "POST" | "PATCH" | "PUT" | "DELETE"): Promise<T> {
  const resposta = await enviarComToken((token) =>
    fetchComTentativas(`${API_URL}${caminho}`, {
      method: metodo ?? (corpo ? "POST" : "GET"),
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: corpo ? JSON.stringify(corpo) : undefined,
    }),
  );
  return lerResposta<T>(resposta);
}

// GET com o token que devolve um ficheiro (ex.: o CSV do resumo anual) em vez de JSON.
// Os erros (401, 402, 423...) seguem o mesmo caminho do pedirApi.
export async function descarregarFicheiro(caminho: string): Promise<Blob> {
  const resposta = await enviarComToken((token) =>
    fetchComTentativas(`${API_URL}${caminho}`, { headers: { Authorization: `Bearer ${token}` } }),
  );
  if (resposta.ok) return await resposta.blob();
  return lerResposta<never>(resposta); // não é ok: lança SessaoExpirada ou ErroApi
}

// Envia um ficheiro (multipart/form-data, como um <form enctype="multipart/form-data"> em PHP).
// Não se põe "Content-Type": o browser escreve-o sozinho, com a "fronteira" entre as partes.
export async function enviarFicheiro<T>(caminho: string, campo: string, ficheiro: File): Promise<T> {
  const formulario = new FormData();
  formulario.append(campo, ficheiro);
  const resposta = await enviarComToken((token) =>
    fetchComTentativas(`${API_URL}${caminho}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formulario,
    }),
  );
  return lerResposta<T>(resposta);
}

// Se o erro é o 429 do limite de extratos PDF do mês. Distingue-se do limite de pedidos pelo texto da API
// (mensagem_do_limite_pdf em limites.py, igual a TEXTOS_LIMITE_PDF.textoApi).
export function eLimitePdf(erro: unknown): erro is ErroApi {
  return (
    erro instanceof ErroApi && erro.status === 429 && typeof erro.detalhe === "string" && erro.detalhe.includes("extratos PDF")
  );
}

// Se o erro é o 429 do limite de pedidos à IA (limites.py). Os ecrãs usam-no para mostrar o AvisoLimite.
export function eLimiteDiario(erro: unknown): boolean {
  return erro instanceof ErroApi && erro.status === 429 && !eLimitePdf(erro);
}

// Se o erro é o 402 de uma função só dos planos pagos (PDF, talões). Os ecrãs mostram o AvisoPlanoPago.
// (402 e não 403: o 403 é a conta sem assinatura, que manda para /assinatura-expirada.)
export function eSoPlanosPagos(erro: unknown): erro is ErroApi {
  return erro instanceof ErroApi && erro.status === 402;
}

// A sessão vista por uma página pública (ex.: /precos), segundo a resposta de GET /plano:
// - "sem-sessao": não há token, ou a API respondeu 401 (token inválido ou expirado);
// - "ativa": 200, com o plano de quem entrou;
// - "plano-terminado": 403, o login está certo mas a conta não tem assinatura;
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
    return { tipo: "ativa", estado: normalizarEstadoPlano(await resposta.json()) };
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
