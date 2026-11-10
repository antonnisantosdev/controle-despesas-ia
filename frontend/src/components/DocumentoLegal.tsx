import Link from "next/link";
import type { ReactNode } from "react";

// Desenha o Markdown simples dos textos legais (lib/textosLegais.ts), sem dependências novas.
// Só o que esses textos usam: # e ## (títulos), parágrafos, listas com "- ", tabelas com "|",
// **negrito**, [links](/caminho ou https://...) e as marcas [A PREENCHER: ...] / [A confirmar pelo jurista...],
// que ficam destacadas a âmbar até o CEO as preencher.

type Bloco =
  | { tipo: "h1" | "h2"; texto: string }
  | { tipo: "p"; linhas: string[] }
  | { tipo: "lista"; itens: string[] }
  | { tipo: "tabela"; cabecalho: string[]; linhas: string[][] };

function celulas(linha: string): string[] {
  return linha
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((celula) => celula.trim());
}

// Linha separadora de uma tabela: |---|---|
const SEPARADOR_TABELA = /^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$/;

export function lerBlocos(markdown: string): Bloco[] {
  const blocos: Bloco[] = [];
  const linhas = markdown.split("\n");
  let i = 0;
  while (i < linhas.length) {
    const linha = linhas[i].trim();
    if (!linha) {
      i++;
    } else if (linha.startsWith("## ")) {
      blocos.push({ tipo: "h2", texto: linha.slice(3) });
      i++;
    } else if (linha.startsWith("# ")) {
      blocos.push({ tipo: "h1", texto: linha.slice(2) });
      i++;
    } else if (linha.startsWith("- ")) {
      const itens: string[] = [];
      while (i < linhas.length && linhas[i].trim().startsWith("- ")) itens.push(linhas[i++].trim().slice(2));
      blocos.push({ tipo: "lista", itens });
    } else if (linha.startsWith("|")) {
      const cabecalho = celulas(linha);
      i++;
      if (i < linhas.length && SEPARADOR_TABELA.test(linhas[i].trim())) i++;
      const corpo: string[][] = [];
      while (i < linhas.length && linhas[i].trim().startsWith("|")) corpo.push(celulas(linhas[i++]));
      blocos.push({ tipo: "tabela", cabecalho, linhas: corpo });
    } else {
      // Parágrafo: linhas seguidas até uma linha vazia ou outro tipo de bloco (cada linha numa linha nova).
      const doParagrafo: string[] = [];
      while (i < linhas.length) {
        const atual = linhas[i].trim();
        if (!atual || atual.startsWith("#") || atual.startsWith("- ") || atual.startsWith("|")) break;
        doParagrafo.push(atual);
        i++;
      }
      blocos.push({ tipo: "p", linhas: doParagrafo });
    }
  }
  return blocos;
}

const ESTILO_LINK =
  "font-medium text-destaque-hover underline hover:no-underline focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque";
const ESTILO_A_PREENCHER =
  "rounded bg-amber-100 px-1 font-medium text-amber-900 ring-1 ring-amber-300 dark:bg-amber-950/60 dark:text-amber-200 dark:ring-amber-800";

// **negrito** | [texto](endereço) | [A PREENCHER...] ou [A confirmar...] (sem endereço a seguir).
const EM_LINHA = /\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)\s]+)\)|\[((?:A PREENCHER|A confirmar)[^\]]*)\]/g;

function emLinha(texto: string, chave = "t"): ReactNode[] {
  const partes: ReactNode[] = [];
  let ultimo = 0;
  for (const marca of texto.matchAll(EM_LINHA)) {
    const inicio = marca.index ?? 0;
    if (inicio > ultimo) partes.push(texto.slice(ultimo, inicio));
    const k = `${chave}-${inicio}`;
    const [inteira, negrito, textoLink, endereco, aPreencher] = marca;
    if (negrito !== undefined) {
      partes.push(
        <strong key={k} className="font-semibold text-texto">
          {emLinha(negrito, k)}
        </strong>,
      );
    } else if (endereco !== undefined) {
      partes.push(
        // Só links internos ("/x", nunca "//dominio") ou https:// e mailto:; outro esquema (ex. javascript:) fica como texto.
        endereco.startsWith("/") && !endereco.startsWith("//") ? (
          <Link key={k} href={endereco} className={ESTILO_LINK}>
            {textoLink}
          </Link>
        ) : endereco.startsWith("https://") || endereco.startsWith("mailto:") ? (
          <a key={k} href={endereco} rel="noopener noreferrer" className={ESTILO_LINK}>
            {textoLink}
          </a>
        ) : (
          <span key={k}>{textoLink}</span>
        ),
      );
    } else if (aPreencher !== undefined) {
      partes.push(
        <mark key={k} className={ESTILO_A_PREENCHER}>
          [{aPreencher}]
        </mark>,
      );
    } else {
      partes.push(inteira);
    }
    ultimo = inicio + inteira.length;
  }
  if (ultimo < texto.length) partes.push(texto.slice(ultimo));
  return partes;
}

// Um texto legal inteiro. O "Rascunho v0.1" (primeiro parágrafo a seguir ao título) fica destacado.
export default function DocumentoLegal({ markdown }: { markdown: string }) {
  const blocos = lerBlocos(markdown);
  return (
    <article className="space-y-4 text-sm leading-relaxed text-texto-suave sm:text-base">
      {blocos.map((bloco, indice) => {
        const k = `b${indice}`;
        switch (bloco.tipo) {
          case "h1":
            return (
              <h1 key={k} className="text-2xl font-semibold text-texto sm:text-3xl">
                {emLinha(bloco.texto, k)}
              </h1>
            );
          case "h2":
            return (
              <h2 key={k} className="pt-4 text-lg font-semibold text-texto sm:text-xl">
                {emLinha(bloco.texto, k)}
              </h2>
            );
          case "lista":
            return (
              <ul key={k} className="list-disc space-y-1.5 pl-5">
                {bloco.itens.map((item, j) => (
                  <li key={j}>{emLinha(item, `${k}-${j}`)}</li>
                ))}
              </ul>
            );
          case "tabela":
            return (
              // No telemóvel a tabela desliza para o lado, em vez de sair do ecrã.
              <div key={k} className="overflow-x-auto rounded-lg border border-borda">
                <table className="w-full min-w-[32rem] text-left text-sm">
                  <thead className="bg-fundo text-texto">
                    <tr>
                      {bloco.cabecalho.map((celula, j) => (
                        <th key={j} scope="col" className="px-3 py-2 font-semibold">
                          {emLinha(celula, `${k}-h${j}`)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {bloco.linhas.map((linha, j) => (
                      <tr key={j} className="border-t border-borda align-top">
                        {linha.map((celula, c) => (
                          <td key={c} className={`px-3 py-2 ${c === 0 ? "font-medium text-texto" : ""}`}>
                            {emLinha(celula, `${k}-${j}-${c}`)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          case "p": {
            const rascunho = indice === 1 && bloco.linhas[0]?.includes("Rascunho");
            return (
              <p
                key={k}
                className={
                  rascunho
                    ? "rounded-md border border-amber-300 bg-amber-50 p-3 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
                    : undefined
                }
              >
                {bloco.linhas.map((linha, j) => (
                  <span key={j}>
                    {j > 0 && <br />}
                    {emLinha(linha, `${k}-${j}`)}
                  </span>
                ))}
              </p>
            );
          }
        }
      })}
    </article>
  );
}
