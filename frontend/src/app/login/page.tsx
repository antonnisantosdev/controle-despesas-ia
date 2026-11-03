"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { API_URL, guardarToken } from "@/lib/api";

export default function PaginaLogin() {
  const router = useRouter();

  // Estado: quando uma destas variáveis muda (com o set...), a página redesenha-se sozinha.
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [erro, setErro] = useState("");
  const [aEntrar, setAEntrar] = useState(false);

  async function entrar(evento: FormEvent<HTMLFormElement>) {
    // Impede o envio clássico do formulário (que recarregava a página, como num form PHP).
    evento.preventDefault();
    setErro("");
    setAEntrar(true);

    try {
      const resposta = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (resposta.ok) {
        const dados = await resposta.json();
        guardarToken(dados.access_token);
        router.push("/dashboard");
      } else {
        setErro("Email ou palavra-passe inválidas.");
      }
    } catch {
      // O fetch só lança erro quando nem consegue falar com a API (desligada, CORS...).
      setErro("Não foi possível ligar à API. Confirma que o fastapi dev está a correr.");
    } finally {
      setAEntrar(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center bg-fundo p-4">
      <form onSubmit={entrar} className="w-full max-w-sm space-y-4 rounded-xl border border-borda bg-cartao p-6">
        <h1 className="text-xl font-semibold text-texto">Control Prices</h1>

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
    </main>
  );
}
