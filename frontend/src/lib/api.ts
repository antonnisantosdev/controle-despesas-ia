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

// Lançado quando a API responde 401: o token não existe, é inválido ou expirou.
export class SessaoExpirada extends Error {}

// Faz um GET à API com o token do login e devolve o JSON da resposta.
export async function pedirApi<T>(caminho: string): Promise<T> {
  const token = lerToken();
  if (!token) {
    throw new SessaoExpirada();
  }

  const resposta = await fetch(`${API_URL}${caminho}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (resposta.status === 401) {
    throw new SessaoExpirada();
  }
  if (!resposta.ok) {
    throw new Error(`A API respondeu ${resposta.status} em ${caminho}`);
  }
  return await resposta.json();
}
