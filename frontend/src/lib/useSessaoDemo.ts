"use client";

import { useSyncExternalStore } from "react";

import { eSessaoDemo, EVENTO_SESSAO } from "./api";

// Avisa o React quando a sessão muda: neste separador (guardarToken/apagarToken) ou noutro (evento "storage").
function subscrever(avisar: () => void) {
  window.addEventListener(EVENTO_SESSAO, avisar);
  window.addEventListener("storage", avisar);
  return () => {
    window.removeEventListener(EVENTO_SESSAO, avisar);
    window.removeEventListener("storage", avisar);
  };
}

// Se a sessão é da demo para recrutadores. No servidor é sempre false (não há localStorage);
// no browser lê-se logo a seguir, sem erros de "hydration".
// Só muda o ecrã (faixa, botões desligados): a API recusa as alterações da demo na mesma (423).
export function useSessaoDemo(): boolean {
  return useSyncExternalStore(subscrever, eSessaoDemo, () => false);
}
