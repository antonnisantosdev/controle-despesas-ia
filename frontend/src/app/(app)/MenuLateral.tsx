"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import Logo from "@/components/Logo";
import RodapeLegal from "@/components/RodapeLegal";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_BOAS_VINDAS } from "@/lib/textosBoasVindas";
import { DICIONARIO_COMUNS, type TextosComuns } from "@/lib/textosComuns";
import { DICIONARIO_RELATORIO } from "@/lib/textosRelatorio";
import { useSair } from "@/lib/useSair";

import CartaoPlano from "./CartaoPlano";
import { CAMINHO_BOAS_VINDAS } from "./IrParaBoasVindas";

// Ícone das definições (três barras com marcadores).
const ICONE_DEFINICOES = "M4 6h9M17 6h3M15 4v4M4 12h3M11 12h9M9 10v4M4 18h11M19 18h1M17 16v4";

// Os nomes vêm do país da conta (useTextos no MenuLateral).
function ligacoes(menu: TextosComuns["TEXTOS_MENU"], resumoAnual: string) {
  return [
    { href: "/dashboard", nome: menu.visaoGeral, icone: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" },
    { href: "/movimentacoes", nome: menu.movimentacoes, icone: "M4 6h16M4 12h16M4 18h10" },
    { href: "/planeamento", nome: menu.planeamento, icone: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" },
    { href: "/compras", nome: menu.compras, icone: "M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6M9 16h3" },
    { href: "/reserva", nome: menu.reserva, icone: "M5 21V4h13l-3 4 3 4H5" },
    { href: "/relatorio", nome: resumoAnual, icone: "M4 5h16v15H4zM4 9h16M8 3v4M16 3v4M8 13h3M8 16h6" },
  ];
}

function Icone({ caminho }: { caminho: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
      <path d={caminho} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function MenuLateral() {
  const { TEXTOS_MENU } = useTextos(DICIONARIO_COMUNS);
  const { TEXTOS_RELATORIO } = useTextos(DICIONARIO_RELATORIO);
  const LIGACOES = ligacoes(TEXTOS_MENU, TEXTOS_RELATORIO.menu);
  const { TEXTOS_DEFINICOES } = useTextos(DICIONARIO_BOAS_VINDAS);
  const pagina = usePathname();
  const sair = useSair();

  function alternarTema() {
    const escuro = document.documentElement.classList.toggle("dark");
    // Guarda a escolha: o script do layout.tsx lê-a da próxima vez que a página abrir.
    localStorage.setItem("tema", escuro ? "escuro" : "claro");
  }


  const foco = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque";
  const estiloBotao = `flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-texto-suave hover:bg-fundo hover:text-texto ${foco}`;
  // A ligação das Definições, quando é a página atual, fica com o mesmo destaque dos links do menu.
  const estiloBotaoAtivo = `flex w-full items-center gap-3 rounded-lg bg-destaque/15 px-3 py-2 text-sm font-medium text-destaque ${foco}`;
  // No ecrã estreito, as definições, o tema e o sair ficam só com o ícone, ao lado do logo (alvo de toque de 44 px).
  const estiloIcone = `inline-flex h-11 w-11 items-center justify-center rounded-lg text-texto-suave hover:bg-fundo hover:text-texto ${foco}`;
  const estiloIconeAtivo = `inline-flex h-11 w-11 items-center justify-center rounded-lg bg-destaque/15 text-destaque ${foco}`;
  const naDefinicoes = pagina === "/definicoes";

  // No questionário de boas-vindas o menu não aparece: um ecrã de cada vez, sem saídas a meio.
  if (pagina === CAMINHO_BOAS_VINDAS) return null;

  return (
    <aside className="flex shrink-0 print:hidden flex-col gap-3 border-b border-borda bg-menu p-3 md:sticky md:top-0 md:h-screen md:w-60 md:gap-4 md:border-b-0 md:border-r md:p-4">
      <div className="flex items-center justify-between px-1 py-1">
        <Logo altura={36} />
        <div className="-my-1 flex gap-0.5 md:hidden">
          <Link
            href="/definicoes"
            aria-label={TEXTOS_DEFINICOES.menu}
            title={TEXTOS_DEFINICOES.menu}
            aria-current={naDefinicoes ? "page" : undefined}
            className={naDefinicoes ? estiloIconeAtivo : estiloIcone}
          >
            <Icone caminho={ICONE_DEFINICOES} />
          </Link>
          <button type="button" onClick={alternarTema} aria-label={TEXTOS_MENU.mudarTema} title={TEXTOS_MENU.mudarTema} className={estiloIcone}>
            <Icone caminho="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z" />
          </button>
          <button type="button" onClick={sair} aria-label={TEXTOS_MENU.sair} title={TEXTOS_MENU.sair} className={estiloIcone}>
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

      {/* O cartão do plano aparece nos dois tamanhos: no computador fica no fundo do menu,
          no telemóvel por baixo dos links. Um só cartão, para não pedir o /plano duas vezes. */}
      <div className="md:mt-auto">
        <CartaoPlano />
      </div>

      <div className="hidden gap-1 md:flex md:flex-col">
        <Link
          href="/definicoes"
          aria-current={naDefinicoes ? "page" : undefined}
          className={naDefinicoes ? estiloBotaoAtivo : estiloBotao}
        >
          <Icone caminho={ICONE_DEFINICOES} />
          {TEXTOS_DEFINICOES.menu}
        </Link>
        <button type="button" onClick={alternarTema} className={estiloBotao}>
          <Icone caminho="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z" />
          {TEXTOS_MENU.mudarTema}
        </button>
        <button type="button" onClick={sair} className={estiloBotao}>
          <Icone caminho="M15 4h4v16h-4M10 8l-4 4 4 4M6 12h11" />
          {TEXTOS_MENU.sair}
        </button>
        <RodapeLegal className="justify-start" />
      </div>
    </aside>
  );
}
