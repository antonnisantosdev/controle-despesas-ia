"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import Logo from "@/components/Logo";
import { apagarToken } from "@/lib/api";

import CartaoPlano from "./CartaoPlano";

const LIGACOES = [
  { href: "/dashboard", nome: "Visão geral", icone: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" },
  { href: "/movimentacoes", nome: "Movimentações", icone: "M4 6h16M4 12h16M4 18h10" },
  { href: "/planeamento", nome: "Planeamento", icone: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" },
  { href: "/compras", nome: "Minhas compras", icone: "M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6M9 16h3" },
  { href: "/reserva", nome: "Minha reserva", icone: "M5 21V4h13l-3 4 3 4H5" },
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
  // No ecrã estreito, o tema e o sair ficam só com o ícone, ao lado do logo.
  const estiloIcone = "rounded-lg p-2 text-texto-suave hover:bg-fundo hover:text-texto";

  return (
    <aside className="flex shrink-0 flex-col gap-3 border-b border-borda bg-menu p-3 md:sticky md:top-0 md:h-screen md:w-60 md:gap-4 md:border-b-0 md:border-r md:p-4">
      <div className="flex items-center justify-between px-1 py-1">
        <Logo altura={36} />
        <div className="flex gap-1 md:hidden">
          <button type="button" onClick={alternarTema} aria-label="Mudar tema" title="Mudar tema" className={estiloIcone}>
            <Icone caminho="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z" />
          </button>
          <button type="button" onClick={sair} aria-label="Sair da conta" title="Sair da conta" className={estiloIcone}>
            <Icone caminho="M15 4h4v16h-4M10 8l-4 4 4 4M6 12h11" />
          </button>
        </div>
      </div>

      {/* No ecrã estreito, os links ficam numa só linha que desliza para o lado, em vez de se partirem.
          [scrollbar-width:none] e [&::-webkit-scrollbar]:hidden escondem a barra de deslocamento. */}
      <nav className="-mx-1 flex [scrollbar-width:none] [&::-webkit-scrollbar]:hidden gap-1 overflow-x-auto px-1 md:mx-0 md:flex-col md:overflow-visible md:px-0">
        {LIGACOES.map((ligacao) => {
          const ativa = pagina === ligacao.href;
          return (
            <Link
              key={ligacao.href}
              href={ligacao.href}
              // No telemóvel, se o link da página atual estiver fora da linha visível, desliza até ele.
              ref={ativa ? (link) => link?.scrollIntoView({ block: "nearest", inline: "nearest" }) : undefined}
              className={
                ativa
                  ? "flex shrink-0 items-center gap-2 whitespace-nowrap rounded-lg bg-destaque/15 px-3 py-2 text-sm font-medium text-destaque md:gap-3"
                  : "flex shrink-0 items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm text-texto-suave hover:bg-fundo hover:text-texto md:gap-3"
              }
            >
              <Icone caminho={ligacao.icone} />
              {ligacao.nome}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto hidden gap-1 md:flex md:flex-col">
        <CartaoPlano />
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
