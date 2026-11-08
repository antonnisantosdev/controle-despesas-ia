"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { pedirApi, type EstadoPlano } from "@/lib/api";

const NOMES_PLANOS: Record<string, string> = { free: "Free", essencial: "Essencial", completo: "Completo" };

// A cor da barra conforme as perguntas já feitas hoje: avisa antes de o limite chegar.
function corDaBarra(usadas: number, limite: number): string {
  // Limite 0 = plano desconhecido, sem IA (limite_do_plano no backend): avisa logo a vermelho.
  // Verificar antes de dividir também evita a divisão por zero.
  if (limite === 0) return "bg-red-500";
  const percentagem = usadas / limite;
  if (percentagem >= 1) return "bg-red-500"; // acabou por hoje
  if (percentagem >= 0.8) return "bg-amber-500"; // quase no fim
  return "bg-destaque"; // à vontade
}

// O plano e as perguntas à IA que restam hoje, no fundo do menu lateral.
export default function CartaoPlano() {
  const pagina = usePathname();
  const [estado, setEstado] = useState<EstadoPlano | null>(null);

  // O menu não se desmonta ao mudar de página, por isso volta a pedir o estado a cada página nova:
  // assim o número acompanha as perguntas feitas no chat, nas importações, etc.
  useEffect(() => {
    pedirApi<EstadoPlano>("/plano")
      .then(setEstado)
      .catch(() => setEstado(null)); // Se falhar, o cartão simplesmente não aparece (a página trata da sessão).
  }, [pagina]);

  if (!estado) return null;

  const usadas = Math.min(estado.usadas_hoje, estado.limite);
  const percentagem = estado.limite > 0 ? (usadas / estado.limite) * 100 : 100;
  const nome = estado.plano ? (NOMES_PLANOS[estado.plano] ?? estado.plano) : "Sem plano";

  return (
    <div className="mb-2 rounded-lg border border-borda bg-cartao p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-destaque">Plano {nome}</p>
      <p className="mt-1 text-sm text-texto">
        {usadas} de {estado.limite} perguntas à IA hoje
      </p>
      <div
        className="mt-2 h-1.5 overflow-hidden rounded-full bg-fundo"
        role="progressbar"
        aria-valuenow={usadas}
        aria-valuemin={0}
        aria-valuemax={estado.limite}
        aria-label="Perguntas à IA usadas hoje"
      >
        <div className={`h-full rounded-full ${corDaBarra(usadas, estado.limite)}`} style={{ width: `${percentagem}%` }} />
      </div>
    </div>
  );
}
