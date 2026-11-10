"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore, type FormEvent } from "react";

import Logo from "@/components/Logo";
import AvisoServidor from "@/components/AvisoServidor";
import BotaoGoogle from "@/components/BotaoGoogle";
import BotaoDemo from "@/components/BotaoDemo";
import RodapeLegal from "@/components/RodapeLegal";
import { API_URL, contaApagada, EVENTO_SESSAO, fetchComTentativas, guardarToken } from "@/lib/api";
import { TEXTOS_APAGAR_CONTA } from "@/lib/textosPlanos";

// Avisa o React quando a marca "a conta foi apagada" muda (ver terminarSessaoContaApagada em api.ts).
function subscrever(avisar: () => void) {
  window.addEventListener(EVENTO_SESSAO, avisar);
  return () => window.removeEventListener(EVENTO_SESSAO, avisar);
}

export default function PaginaLogin() {
  const router = useRouter();

  // Estado: quando uma destas variáveis muda (com o set...), a página redesenha-se sozinha.
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [erro, setErro] = useState("");
  const [aEntrar, setAEntrar] = useState(false);
  // Veio de apagar a conta (O meu plano): mostra a confirmação. No servidor é sempre false.
  const apagada = useSyncExternalStore(subscrever, contaApagada, () => false);

  // Acorda a API logo que a página abre: enquanto se escreve o email e a palavra-passe,
  // o Render já está a arrancar o servidor. A resposta não interessa, e um erro também não.
  useEffect(() => {
    fetch(`${API_URL}/`).catch(() => {});
  }, []);

  async function entrar(evento: FormEvent<HTMLFormElement>) {
    // Impede o envio clássico do formulário (que recarregava a página, como num form PHP).
    evento.preventDefault();
    setErro("");
    setAEntrar(true);

    try {
      const resposta = await fetchComTentativas(`${API_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (resposta.ok) {
        const dados = await resposta.json();
        guardarToken(dados.access_token);
        router.push("/dashboard");
      } else {
        // A API explica o problema no "detail" (palavra-passe errada, email por confirmar...).
        const corpo = await resposta.json().catch(() => null);
        setErro(typeof corpo?.detail === "string" ? corpo.detail : "Email ou palavra-passe inválidas.");
      }
    } catch {
      // O fetch só lança erro quando nem consegue falar com a API (desligada, CORS...).
      setErro("Não foi possível ligar ao servidor. Tenta outra vez daqui a um minuto.");
    } finally {
      setAEntrar(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center bg-fundo p-4">
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-borda bg-cartao p-6">
        <h1 className="flex justify-center pb-2">
          <Logo altura={48} />
        </h1>

        {apagada && (
          <p role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
            {TEXTOS_APAGAR_CONTA.apagada}
          </p>
        )}

        <BotaoGoogle comTermos />

        <form onSubmit={entrar} className="space-y-4">
          <label className="block">
            <span className="text-sm text-texto-suave">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-texto"
            />
          </label>

          <label className="block">
            <span className="text-sm text-texto-suave">Palavra-passe</span>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-texto"
            />
          </label>

          {/* Só aparece quando há um erro para mostrar. */}
          {erro && <p className="text-sm text-red-600 dark:text-red-400">{erro}</p>}

          <button
            type="submit"
            disabled={aEntrar}
            className="w-full rounded-md bg-destaque py-2 font-medium text-white hover:bg-destaque-hover disabled:opacity-50"
          >
            {aEntrar ? "A entrar..." : "Entrar"}
          </button>
        </form>

        {/* Demo para recrutadores: entra numa conta partilhada com dados inventados, só de leitura. */}
        <div className="border-t border-borda pt-4">
          <BotaoDemo />
        </div>

        <p className="text-center text-sm text-texto-suave">
          Ainda não tens conta?{" "}
          <Link href="/registo" className="font-medium text-destaque hover:underline">
            Cria uma grátis
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
        <RodapeLegal className="-mt-2" />
      </div>
      <AvisoServidor />
    </main>
  );
}
