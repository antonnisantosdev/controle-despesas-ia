"use client";

import { useSyncExternalStore } from "react";

import { contaDoTexto, lerContaGuardada } from "./contaGuardada";
import type { Pais } from "./formatos";
import type { Dicionario } from "./textos";

// O país das páginas públicas (login, registo, Google, rodapé), onde ainda não há conta com sessão:
// 1. o da última conta que entrou neste browser (contaGuardada), se houver;
// 2. senão, a língua do browser: pt-BR -> BR; tudo o resto -> PT.
// No servidor (e no 1.º desenho) é sempre PT; o browser troca logo a seguir. Decisão do CEO (2026-11-13).
export function paisDoBrowser(): Pais {
  const guardada = contaDoTexto(lerContaGuardada());
  if (guardada) return guardada.pais;
  try {
    const linguas = navigator.languages?.length ? navigator.languages : [navigator.language];
    return linguas[0]?.toLowerCase() === "pt-br" ? "BR" : "PT";
  } catch {
    return "PT";
  }
}

// O país só muda se a pessoa mudar a língua do browser ou entrar noutra conta noutro separador.
function subscrever(avisar: () => void) {
  window.addEventListener("languagechange", avisar);
  window.addEventListener("storage", avisar);
  return () => {
    window.removeEventListener("languagechange", avisar);
    window.removeEventListener("storage", avisar);
  };
}

export function usePaisPublico(): Pais {
  return useSyncExternalStore(subscrever, paisDoBrowser, () => "PT");
}

// Como useTextos (lib/textos.ts), mas pelo país das páginas públicas.
export function useTextosPublicos<T>(dicionario: Dicionario<T>): T {
  return dicionario[usePaisPublico()] ?? dicionario.PT;
}
