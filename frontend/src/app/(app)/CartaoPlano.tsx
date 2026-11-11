"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useEstadoPlano } from "@/lib/conta";
import { avisoCurtoDeQuota, nomeDoPlano, preencher } from "@/lib/planos";
import { TEXTOS_CARTAO_PLANO } from "@/lib/textosComuns";
import { TEXTOS_DEMO } from "@/lib/textosDemo";
import { TEXTOS_MEU_PLANO } from "@/lib/textosPlanos";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

// A cor da barra conforme os pedidos à IA já feitos no período: avisa antes de o limite chegar.
export function corDaBarra(usadas: number, limite: number): string {
  // Limite 0 = plano desconhecido, sem IA (limite_do_plano no backend): avisa logo a vermelho.
  // Verificar antes de dividir também evita a divisão por zero.
  if (limite === 0) return "bg-red-500";
  const percentagem = usadas / limite;
  if (percentagem >= 1) return "bg-red-500"; // acabou por hoje
  if (percentagem >= 0.8) return "bg-amber-500"; // quase no fim
  return "bg-destaque"; // à vontade
}

// O plano e os pedidos à IA usados hoje (ou este mês, no Free), no fundo do menu lateral. Leva ao "O meu plano" (/plano).
// Na demo, só "Conta de demonstração" e as 5 perguntas por dia: o contador do plano é partilhado
// por todos os visitantes e não diz nada a quem está a ver.
export default function CartaoPlano() {
  const pagina = usePathname();
  const demo = useSessaoDemo();
  // O ProvedorConta (layout da app) volta a pedir o estado a cada página nova: assim o número acompanha
  // os pedidos feitos no chat, nas importações, etc. Se falhar, é null e o cartão não aparece.
  const estado = useEstadoPlano();

  if (demo) {
    const ativoDemo = pagina === "/plano";
    return (
      <Link
        href="/plano"
        aria-current={ativoDemo ? "page" : undefined}
        className={`block rounded-lg border bg-cartao p-3 transition-colors hover:border-destaque focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque ${ativoDemo ? "border-destaque" : "border-borda"}`}
      >
        <p className="text-xs font-semibold uppercase tracking-wide text-destaque-hover">{TEXTOS_DEMO.planoDemoNome}</p>
        <p className="mt-1 text-sm text-texto">{TEXTOS_DEMO.planoDemoChat}</p>
      </Link>
    );
  }

  if (!estado) return null;

  const usadas = Math.min(estado.usadas, estado.limite);
  const percentagem = estado.limite > 0 ? (usadas / estado.limite) * 100 : 100;
  const nome = nomeDoPlano(estado.plano) ?? TEXTOS_MEU_PLANO.nomeSemPlano;
  const ativo = pagina === "/plano";
  // O Free conta os pedidos por mês; os pagos, por dia.
  const doMes = estado.periodo === "mes";
  const texto = preencher(doMes ? TEXTOS_MEU_PLANO.cartaoMes : TEXTOS_MEU_PLANO.cartaoHoje, { usadas, limite: estado.limite });
  // A partir de 80% dos pedidos (e antes do limite): "Faltam 4 pedidos à IA". O cartão já leva a /plano.
  const avisoCurto = avisoCurtoDeQuota(estado);

  return (
    <Link
      href="/plano"
      aria-current={ativo ? "page" : undefined}
      className={`block rounded-lg border bg-cartao p-3 transition-colors hover:border-destaque focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque ${ativo ? "border-destaque" : "border-borda"}`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-destaque-hover">{preencher(TEXTOS_CARTAO_PLANO.plano, { nome })}</p>
      <p className="mt-1 text-sm text-texto">{texto}</p>
      <div
        className="mt-2 h-1.5 overflow-hidden rounded-full bg-fundo"
        role="progressbar"
        aria-valuenow={usadas}
        aria-valuemin={0}
        aria-valuemax={estado.limite}
        aria-label={doMes ? TEXTOS_CARTAO_PLANO.barraMes : TEXTOS_CARTAO_PLANO.barraHoje}
      >
        <div className={`h-full rounded-full ${corDaBarra(usadas, estado.limite)}`} style={{ width: `${percentagem}%` }} />
      </div>
      {avisoCurto && (
        <p className="mt-2 rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
          {avisoCurto}
        </p>
      )}
    </Link>
  );
}
