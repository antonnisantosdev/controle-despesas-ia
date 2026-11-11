"use client";

import { useEffect } from "react";

import { guardarOrigemDoEndereco } from "@/lib/origem";

// No layout: à chegada a qualquer página, guarda o canal do ?utm_source= (ver lib/origem.ts). Não desenha nada.
export default function GuardarOrigem() {
  useEffect(() => {
    guardarOrigemDoEndereco(window.location.search);
  }, []);
  return null;
}
