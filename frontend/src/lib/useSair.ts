"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { apagarToken } from "./api";

// Sair da conta: apaga a sessão deste browser e vai para o login (menu lateral e questionário de boas-vindas).
export function useSair(): () => void {
  const router = useRouter();
  return useCallback(() => {
    apagarToken();
    router.replace("/login");
  }, [router]);
}
