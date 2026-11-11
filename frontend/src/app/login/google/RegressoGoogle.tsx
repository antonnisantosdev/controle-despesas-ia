"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { API_URL, fetchComTentativas, guardarToken } from "@/lib/api";
import { lerOrigem, type Origem } from "@/lib/origem";
import { apagarVerifier, lerVerifier } from "@/lib/pkceGoogle";
import { TEXTOS_GOOGLE } from "@/lib/textosLogin";

// origem: o canal do utm_source; a API só o guarda se a conta for nova (primeiro login).
type PedidoTroca = { code: string; code_verifier: string; origem?: Origem };

// O que o Supabase mandou no regresso do Google: o código (?code=...) ou um erro.
// Os erros podem vir na query ou no fragmento (?error=...&error_description=...).
// eRegresso: se o endereço traz um código ou um erro (é mesmo o regresso de um login começado);
// codigo: o código, ou null se houve erro ou não veio código.
function lerRegresso(query: string, hash: string): { eRegresso: boolean; codigo: string | null } {
  const parametros = new URLSearchParams(query);
  const fragmento = new URLSearchParams(hash.replace(/^#/, ""));
  const temErro = parametros.has("error") || fragmento.has("error");
  const codigo = parametros.get("code") || null;
  return { eRegresso: temErro || codigo !== null, codigo: temErro ? null : codigo };
}

// A troca falhou. mensagem: o "detail" da API quando vale a pena mostrá-lo (429, muitas tentativas);
// nos outros erros fica null e a página mostra a mensagem genérica.
class TrocaFalhou extends Error {
  constructor(readonly mensagem: string | null) {
    super("Troca do código recusada");
  }
}

// Troca o código pelo token na API (POST /login/google/troca), com o segredo PKCE guardado neste browser.
// O refresh_token fica de fora, como no login com email: quando o token expirar, faz-se login outra vez.
async function trocarCodigo(pedido: PedidoTroca): Promise<string> {
  const resposta = await fetchComTentativas(`${API_URL}/login/google/troca`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(pedido),
  });
  const corpo = await resposta.json().catch(() => null);
  if (resposta.status === 429 && typeof corpo?.detail === "string") throw new TrocaFalhou(corpo.detail);
  if (!resposta.ok || typeof corpo?.access_token !== "string") throw new TrocaFalhou(null);
  return corpo.access_token;
}

// Só corre no browser (a page.tsx carrega-o com ssr: false), por isso pode ler o window.location logo ao abrir.
export default function RegressoGoogle() {
  const router = useRouter();
  // Lido uma só vez, quando o componente aparece (antes de o endereço ser limpo e o segredo apagado).
  // Sem o segredo deste browser não há troca: pode ser um link de um atacante com o código da conta dele
  // (ver lib/pkceGoogle.ts). A sessão que já existir fica intacta.
  const [{ eRegresso, pedido }] = useState<{ eRegresso: boolean; pedido: PedidoTroca | null }>(() => {
    const regresso = lerRegresso(window.location.search, window.location.hash);
    const verifier = lerVerifier();
    const pedido = regresso.codigo && verifier ? { code: regresso.codigo, code_verifier: verifier, origem: lerOrigem() } : null;
    return { eRegresso: regresso.eRegresso, pedido };
  });
  const [falhou, setFalhou] = useState(false);
  // O texto do erro quando a API explica o problema (429); null mostra TEXTOS_GOOGLE.erroEntrar.
  const [mensagemErro, setMensagemErro] = useState<string | null>(null);
  // O código só serve uma vez: em desenvolvimento o React corre o efeito duas vezes, e a segunda troca falharia.
  const jaTrocou = useRef(false);

  useEffect(() => {
    // Tira logo o código do endereço, para não ficar no histórico nem ser copiado com o link.
    window.history.replaceState(null, "", window.location.pathname);
    // O segredo só se gasta num regresso a sério (com código ou erro). Abrir /login/google sem nada
    // (ex.: noutro separador, a meio de um login) mostra o erro mas não estraga o login que está a decorrer.
    if (eRegresso) apagarVerifier();
    if (!pedido || jaTrocou.current) return;
    jaTrocou.current = true;
    trocarCodigo(pedido)
      .then((token) => {
        guardarToken(token);
        // O mesmo destino do login com email. Se o plano tiver terminado, a API responde 403
        // no dashboard e o pedirApi manda para /assinatura-expirada, como no login normal.
        router.replace("/dashboard");
      })
      .catch((erro: unknown) => {
        setMensagemErro(erro instanceof TrocaFalhou ? erro.mensagem : null);
        setFalhou(true);
      });
  }, [eRegresso, pedido, router]);

  if (pedido && !falhou) {
    return (
      <p className="text-sm text-texto-suave" aria-live="polite">
        {TEXTOS_GOOGLE.aEntrar}
      </p>
    );
  }

  return (
    <>
      <p role="alert" className="text-sm text-texto">
        {mensagemErro ?? TEXTOS_GOOGLE.erroEntrar}
      </p>
      <Link
        href="/login"
        className="flex min-h-11 w-full items-center justify-center rounded-md bg-destaque px-4 text-sm font-semibold text-white transition-colors hover:bg-destaque-hover dark:text-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
      >
        {TEXTOS_GOOGLE.voltarLogin}
      </Link>
    </>
  );
}
