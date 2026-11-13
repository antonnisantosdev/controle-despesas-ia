"use client";

import { useEffect, useState } from "react";

import AvisoTermos from "@/components/AvisoTermos";
import { API_URL, fetchComTentativas } from "@/lib/api";
import { calcularChallenge, gerarVerifier, guardarVerifier } from "@/lib/pkceGoogle";
import { useTextosPublicos } from "@/lib/paisPublico";
import { DICIONARIO_LOGIN } from "@/lib/textosLogin";

// min-h-11 = 44 px (alvo de toque). Foco visível ao navegar com o teclado.
// Botão com contorno (como os secundários do projeto), para o "Entrar" continuar a ser o principal.
const ESTILO_BOTAO =
  "flex min-h-11 w-full items-center justify-center gap-3 rounded-md border border-borda bg-cartao px-4 py-2 text-sm font-medium text-texto transition-colors hover:bg-fundo disabled:cursor-wait disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque";

// O "G" do Google, com as quatro cores da marca. aria-hidden: o texto do botão já diz tudo.
function LogoGoogle() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

// "Continuar com Google" e, por baixo, o separador "ou" antes do formulário de email.
// A API devolve o endereço do Supabase (GET /login/google); o browser vai para lá e,
// depois de escolher a conta Google, volta à página /login/google com um código (?code=).
// comTermos: mostra por baixo a frase dos termos (no login, onde o primeiro login com o Google cria a conta).
export default function BotaoGoogle({ comTermos = false }: { comTermos?: boolean }) {
  const { TEXTOS_GOOGLE } = useTextosPublicos(DICIONARIO_LOGIN);
  const [aAbrir, setAAbrir] = useState(false);
  const [erro, setErro] = useState("");

  // Se a pessoa voltar do Google com o botão "Anterior", o browser pode mostrar a página
  // guardada em memória, ainda com o botão desativado. O pageshow reativa-o.
  useEffect(() => {
    function aoMostrar(evento: PageTransitionEvent) {
      if (evento.persisted) setAAbrir(false);
    }
    window.addEventListener("pageshow", aoMostrar);
    return () => window.removeEventListener("pageshow", aoMostrar);
  }, []);

  async function continuarComGoogle() {
    setErro("");
    setAAbrir(true);
    try {
      // Segredo PKCE deste login (ver lib/pkceGoogle.ts): à API só vai o SHA-256 dele.
      const verifier = gerarVerifier();
      const challenge = await calcularChallenge(verifier);
      const destino = `${window.location.origin}/login/google`;
      const parametros = new URLSearchParams({ destino, code_challenge: challenge });
      const resposta = await fetchComTentativas(`${API_URL}/login/google?${parametros}`);
      const corpo = await resposta.json().catch(() => null);
      // 429: muitas tentativas a partir desta rede. A API explica no "detail" quando se pode tentar outra vez.
      if (resposta.status === 429 && typeof corpo?.detail === "string") {
        setErro(corpo.detail);
        setAAbrir(false);
        return;
      }
      if (!resposta.ok || typeof corpo?.url !== "string") throw new Error("Sem endereço do login");
      // Guarda o segredo neste browser. Só depois sai para o Google; o aAbrir fica true até a página mudar.
      guardarVerifier(verifier);
      window.location.href = corpo.url;
    } catch {
      setErro(TEXTOS_GOOGLE.erroAbrir);
      setAAbrir(false);
    }
  }

  return (
    <div className="space-y-4">
      <button type="button" onClick={continuarComGoogle} disabled={aAbrir} className={ESTILO_BOTAO}>
        <LogoGoogle />
        {aAbrir ? TEXTOS_GOOGLE.aAbrir : TEXTOS_GOOGLE.botao}
      </button>
      {comTermos && <AvisoTermos />}
      {erro && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {erro}
        </p>
      )}
      <div className="flex items-center gap-3 text-xs text-texto-suave">
        <span className="h-px flex-1 bg-borda" aria-hidden="true" />
        {TEXTOS_GOOGLE.separador}
        <span className="h-px flex-1 bg-borda" aria-hidden="true" />
      </div>
    </div>
  );
}
