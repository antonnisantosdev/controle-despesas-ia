"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import Logo from "@/components/Logo";
import { apagarToken } from "@/lib/api";

const LIGACOES = [
  { href: "/dashboard", nome: "Visão geral", icone: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" },
  { href: "/movimentacoes", nome: "Movimentações", icone: "M4 6h16M4 12h16M4 18h10" },
  { href: "/planeamento", nome: "Planeamento", icone: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" },
];

function Icone({ caminho }: { caminho: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
      <path d={caminho} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function MenuLateral() {
  const pagina = usePathname();
  const router = useRouter();

  function alternarTema() {
    const escuro = document.documentElement.classList.toggle("dark");
    // Guarda a escolha: o script do layout.tsx lê-a da próxima vez que a página abrir.
    localStorage.setItem("tema", escuro ? "escuro" : "claro");
  }

  function sair() {
    apagarToken();
    router.replace("/login");
  }

  const estiloBotao =
    "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-texto-suave hover:bg-fundo hover:text-texto";

  return (
    <aside className="flex shrink-0 flex-col gap-4 border-b border-borda bg-menu p-4 md:sticky md:top-0 md:h-screen md:w-60 md:border-b-0 md:border-r">
      <div className="px-1 py-1">
        <Logo altura={36} />
      </div>

      <nav className="flex gap-1 md:flex-col">
        {LIGACOES.map((ligacao) => {
          const ativa = pagina === ligacao.href;
          return (
            <Link
              key={ligacao.href}
              href={ligacao.href}
              className={
                ativa
                  ? "flex items-center gap-3 rounded-lg bg-destaque/15 px-3 py-2 text-sm font-medium text-destaque"
                  : "flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-texto-suave hover:bg-fundo hover:text-texto"
              }
            >
              <Icone caminho={ligacao.icone} />
              {ligacao.nome}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto flex gap-1 md:flex-col">
        <button type="button" onClick={alternarTema} className={estiloBotao}>
          <Icone caminho="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z" />
          Mudar tema
        </button>
        <button type="button" onClick={sair} className={estiloBotao}>
          <Icone caminho="M15 4h4v16h-4M10 8l-4 4 4 4M6 12h11" />
          Sair da conta
        </button>
      </div>
    </aside>
  );
}
