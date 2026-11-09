"use client";

import { useEffect, useState } from "react";

import { planosDisponiveis } from "./api";
import { juntarLimites, LIMITES_RESERVA } from "./planos";

// Os limites diários de cada plano. Começa logo com os de reserva (a página não fica à espera
// enquanto a API acorda) e troca pelos de GET /planos quando chegarem.
export function useLimitesPlanos() {
  const [limites, setLimites] = useState(LIMITES_RESERVA);

  useEffect(() => {
    planosDisponiveis().then((lista) => setLimites(juntarLimites(lista)));
  }, []);

  return limites;
}
