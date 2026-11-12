"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import AvisoServidor from "@/components/AvisoServidor";
import AvisoTermos from "@/components/AvisoTermos";
import BotaoGoogle from "@/components/BotaoGoogle";
import Logo from "@/components/Logo";
import RodapeLegal from "@/components/RodapeLegal";
import { API_URL, fetchComTentativas } from "@/lib/api";
import { lerOrigem } from "@/lib/origem";
import { LIMITES_RESERVA, preencher, textoDosPedidos } from "@/lib/planos";
import { DICIONARIO_COMUNS } from "@/lib/textosComuns";
import { TEXTOS_REGISTO } from "@/lib/textosLogin";
import { DICIONARIO_PLANOS } from "@/lib/textosPlanos";
import CampoPalavraPasse from "@/components/CampoPalavraPasse";

// Página pública: sempre em PT-PT (decisão do CEO), seja qual for o país da conta.
const { TEXTOS_GERAIS } = DICIONARIO_COMUNS.PT;

const ESTILO_CAMPO = "mt-1 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-texto";

// Verifica o formulário antes de o enviar: devolve a mensagem de erro, ou "" se estiver tudo bem.
// É só para ajudar quem escreve. As regras a sério (email válido, 8+ caracteres) estão na API (NovaConta).
function erroDoFormulario(password: string, repetir: string): string {
  if (password.length < 8) return TEXTOS_REGISTO.erroCurta;
  if (password !== repetir) return TEXTOS_REGISTO.erroDiferentes;
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
        // origem: o canal do utm_source desta sessão (ou fica de fora).
        body: JSON.stringify({ email, password, origem: lerOrigem() }),
      });
      const corpo = await resposta.json().catch(() => null);

      if (resposta.ok) {
        setMensagem(corpo?.mensagem ?? TEXTOS_REGISTO.criada);
      } else if (resposta.status === 422) {
        // O Pydantic recusou os dados: na prática, um email mal escrito.
        setErro(TEXTOS_REGISTO.erroEmail);
      } else {
        setErro(typeof corpo?.detail === "string" ? corpo.detail : TEXTOS_REGISTO.erroCriar);
      }
    } catch {
      setErro(TEXTOS_GERAIS.semLigacao);
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
            <p className="font-medium text-texto">{TEXTOS_REGISTO.quaseLa}</p>
            <p className="text-sm text-texto-suave">{mensagem}</p>
            <p className="text-xs text-texto-suave">{TEXTOS_REGISTO.spam}</p>
            <Link href="/login" className="block text-sm font-medium text-destaque hover:underline">
              {TEXTOS_REGISTO.irLogin}
            </Link>
          </div>
        ) : (
          <form onSubmit={criarConta} className="space-y-4">
            <p className="text-center text-sm text-texto-suave">
              {preencher(TEXTOS_REGISTO.introducao, { pedidos: textoDosPedidos(LIMITES_RESERVA.free, DICIONARIO_PLANOS.PT) })}
            </p>
            {/* Antes das duas formas de criar conta (Google e email), para valer para as duas. */}
            <AvisoTermos />

            {/* Com o Google, a conta é criada no primeiro login (e entra no Free pelo mesmo gatilho). */}
            <BotaoGoogle />

            <label className="block">
              <span className="text-sm text-texto-suave">{TEXTOS_GERAIS.email}</span>
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
              <span className="text-sm text-texto-suave">{TEXTOS_REGISTO.palavraPasse}</span>
              <CampoPalavraPasse
                autoComplete="new-password"
                value={password}
                onChange={setPassword}
                className={ESTILO_CAMPO}
              />
            </label>

            <label className="block">
              <span className="text-sm text-texto-suave">{TEXTOS_REGISTO.repetir}</span>
              <CampoPalavraPasse
                autoComplete="new-password"
                value={repetir}
                onChange={setRepetir}
                className={ESTILO_CAMPO}
              />
            </label>

            {erro && <p className="text-sm text-red-600 dark:text-red-400">{erro}</p>}

            <button
              type="submit"
              disabled={aCriar}
              className="w-full rounded-md bg-destaque py-2 font-medium text-white hover:bg-destaque-hover disabled:opacity-50"
            >
              {aCriar ? TEXTOS_REGISTO.aCriar : TEXTOS_REGISTO.criar}
            </button>

            <p className="text-center text-sm text-texto-suave">
              {TEXTOS_REGISTO.jaTensConta}{" "}
              <Link href="/login" className="font-medium text-destaque hover:underline">
                {TEXTOS_REGISTO.entra}
              </Link>
            </p>
            <p className="-mt-2 text-center text-xs">
              <Link
                href="/precos"
                className="inline-flex min-h-11 items-center rounded-md px-2 text-texto-suave hover:text-texto hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
              >
                {TEXTOS_GERAIS.verPlanos}
              </Link>
            </p>
          </form>
        )}
        <RodapeLegal />
      </div>
      <AvisoServidor />
    </main>
  );
}
