"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import Logo from "@/components/Logo";
import AvisoServidor from "@/components/AvisoServidor";
import { API_URL, fetchComTentativas, guardarToken } from "@/lib/api";

export default function PaginaLogin() {
  const router = useRouter();

  // Estado: quando uma destas variáveis muda (com o set...), a página redesenha-se sozinha.
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [erro, setErro] = useState("");
  const [aEntrar, setAEntrar] = useState(false);

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
      <form onSubmit={entrar} className="w-full max-w-sm space-y-4 rounded-xl border border-borda bg-cartao p-6">
        <h1 className="flex justify-center pb-2">
          <Logo altura={48} />
        </h1>

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

        <p className="text-center text-sm text-texto-suave">
          Ainda não tens conta?{" "}
          <Link href="/registo" className="font-medium text-destaque hover:underline">
            Cria uma grátis
          </Link>
        </p>
      </form>
      <AvisoServidor />
    </main>
  );
}
