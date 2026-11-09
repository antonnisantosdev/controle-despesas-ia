"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import AvisoServidor from "@/components/AvisoServidor";
import Logo from "@/components/Logo";
import { API_URL, fetchComTentativas } from "@/lib/api";

const ESTILO_CAMPO = "mt-1 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-texto";

// Verifica o formulário antes de o enviar: devolve a mensagem de erro, ou "" se estiver tudo bem.
// É só para ajudar quem escreve. As regras a sério (email válido, 8+ caracteres) estão na API (NovaConta).
function erroDoFormulario(password: string, repetir: string): string {
  if (password.length < 8) return "A palavra-passe tem de ter pelo menos 8 caracteres.";
  if (password !== repetir) return "As palavras-passe não coincidem.";
  return "";
}

export default function PaginaRegisto() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repetir, setRepetir] = useState("");
  const [erro, setErro] = useState("");
  const [aCriar, setACriar] = useState(false);
  const [mensagem, setMensagem] = useState(""); // a resposta da API depois de a conta ser criada

  // Acorda a API enquanto a pessoa preenche o formulário (como no login).
  useEffect(() => {
    fetch(`${API_URL}/`).catch(() => {});
  }, []);

  async function criarConta(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const problema = erroDoFormulario(password, repetir);
    setErro(problema);
    if (problema) return;

    setACriar(true);
    try {
      const resposta = await fetchComTentativas(`${API_URL}/registo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const corpo = await resposta.json().catch(() => null);

      if (resposta.ok) {
        setMensagem(corpo?.mensagem ?? "Conta criada. Confirma o email para entrar.");
      } else if (resposta.status === 422) {
        // O Pydantic recusou os dados: na prática, um email mal escrito.
        setErro("Confirma que o email está bem escrito.");
      } else {
        setErro(typeof corpo?.detail === "string" ? corpo.detail : "Não foi possível criar a conta.");
      }
    } catch {
      setErro("Não foi possível ligar ao servidor. Tenta outra vez daqui a um minuto.");
    } finally {
      setACriar(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center bg-fundo p-4">
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-borda bg-cartao p-6">
        <h1 className="flex justify-center pb-2">
          <Logo altura={48} />
        </h1>

        {mensagem ? (
          // Depois de criar a conta, o formulário dá lugar ao aviso do email.
          <div className="space-y-4 text-center">
            <p className="font-medium text-texto">Quase lá!</p>
            <p className="text-sm text-texto-suave">{mensagem}</p>
            <p className="text-xs text-texto-suave">Não chegou? Vê na pasta de spam.</p>
            <Link href="/login" className="block text-sm font-medium text-destaque hover:underline">
              Ir para o login
            </Link>
          </div>
        ) : (
          <form onSubmit={criarConta} className="space-y-4">
            <p className="text-center text-sm text-texto-suave">
              Cria a tua conta grátis. O plano Free inclui 5 pedidos à IA por dia.
            </p>

            <label className="block">
              <span className="text-sm text-texto-suave">Email</span>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={ESTILO_CAMPO}
              />
            </label>

            <label className="block">
              <span className="text-sm text-texto-suave">Palavra-passe (mínimo 8 caracteres)</span>
              <input
                type="password"
                required
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={ESTILO_CAMPO}
              />
            </label>

            <label className="block">
              <span className="text-sm text-texto-suave">Repetir a palavra-passe</span>
              <input
                type="password"
                required
                autoComplete="new-password"
                value={repetir}
                onChange={(e) => setRepetir(e.target.value)}
                className={ESTILO_CAMPO}
              />
            </label>

            {erro && <p className="text-sm text-red-600 dark:text-red-400">{erro}</p>}

            <button
              type="submit"
              disabled={aCriar}
              className="w-full rounded-md bg-destaque py-2 font-medium text-white hover:bg-destaque-hover disabled:opacity-50"
            >
              {aCriar ? "A criar a conta..." : "Criar conta"}
            </button>

            <p className="text-center text-sm text-texto-suave">
              Já tens conta?{" "}
              <Link href="/login" className="font-medium text-destaque hover:underline">
                Entra
              </Link>
            </p>
            <p className="-mt-2 text-center text-xs">
              <Link
                href="/precos"
                className="inline-flex min-h-11 items-center rounded-md px-2 text-texto-suave hover:text-texto hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
              >
                Ver planos
              </Link>
            </p>
          </form>
        )}
      </div>
      <AvisoServidor />
    </main>
  );
}
