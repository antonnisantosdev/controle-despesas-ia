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
  return await resposta.json();
}

// Faz um pedido à API com o token do login e devolve o JSON da resposta.
// Sem corpo é um GET; com corpo é um POST com esse objeto em JSON (ou outro método, se for indicado).
export async function pedirApi<T>(caminho: string, corpo?: object, metodo?: "POST" | "PATCH" | "PUT"): Promise<T> {
  const token = lerTokenOuFalhar();
  const resposta = await fetch(`${API_URL}${caminho}`, {
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
  const resposta = await fetch(`${API_URL}${caminho}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formulario,
  });
  return lerResposta<T>(resposta);
}
