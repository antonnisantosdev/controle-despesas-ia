"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { apagarToken, enviarFicheiro, ErroApi, pedirApi, SessaoExpirada, type Compra, type Talao } from "@/lib/api";
import { reduzirImagem } from "@/lib/imagem";

import { euros } from "../dashboard/formatos";
import RevisaoTalao from "./RevisaoTalao";

// "2026-10-28" -> "28/10/2026"
function dataCurta(data: string) {
  return new Date(`${data}T00:00:00`).toLocaleDateString("pt-PT");
}

export default function PaginaCompras() {
  const router = useRouter();
  const entradaFoto = useRef<HTMLInputElement>(null);
  const [compras, setCompras] = useState<Compra[] | null>(null); // null = ainda a carregar
  const [talao, setTalao] = useState<Talao | null>(null); // o que a IA leu, à espera de revisão
  const [aLer, setALer] = useState(false);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");

  function tratarSessao(e: unknown) {
    if (e instanceof SessaoExpirada) {
      apagarToken();
      router.replace("/login");
    }
  }

  useEffect(() => {
    pedirApi<Compra[]>("/compras")
      .then(setCompras)
      .catch((e) => {
        // Sessão expirada: vai para o login sem mostrar erro (senão a mensagem fica lá ao voltar à página).
        if (e instanceof SessaoExpirada) tratarSessao(e);
        else setErro("Não foi possível carregar as compras. Confirma que a API está a correr.");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function lerFoto(ficheiro: File) {
    setALer(true);
    setErro("");
    setAviso("");
    setTalao(null);
    try {
      const pequena = await reduzirImagem(ficheiro);
      setTalao(await enviarFicheiro<Talao>("/compras/ler", "foto", pequena));
    } catch (e) {
      if (e instanceof SessaoExpirada) tratarSessao(e);
      // 413/415/422 (foto inválida), 429 (limite diário) e 503 (IA em baixo) trazem uma explicação da API.
      else if (e instanceof ErroApi && typeof e.detalhe === "string") setErro(e.detalhe);
      else setErro("Não foi possível ler a fotografia. Tenta outra vez.");
    } finally {
      setALer(false);
      if (entradaFoto.current) entradaFoto.current.value = "";
    }
  }

  function gravada(compra: Compra) {
    setTalao(null);
    // A nova compra entra no topo da lista, sem voltar a pedir tudo à API.
    setCompras((anteriores) => [compra, ...(anteriores ?? [])]);
    setAviso(`Compra gravada: ${compra.loja}, ${euros(compra.total)}. Já aparece nas Movimentações.`);
  }

  return (
    <main className="p-4 sm:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-destaque">Talões lidos pela IA</p>
            <h1 className="text-2xl font-semibold text-texto">Minhas compras</h1>
          </div>
          {/* capture="environment": no telemóvel, abre logo a câmara traseira. No computador, escolhe-se um ficheiro. */}
          <input
            ref={entradaFoto}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            className="hidden"
            onChange={(e) => {
              const ficheiro = e.target.files?.[0];
              if (ficheiro) lerFoto(ficheiro);
            }}
          />
          <button
            type="button"
            disabled={aLer}
            onClick={() => entradaFoto.current?.click()}
            className="rounded-lg bg-destaque px-4 py-2 text-sm font-medium text-white hover:bg-destaque-hover disabled:opacity-50"
          >
            {aLer ? "A IA está a ler o talão..." : "📷 Fotografar talão"}
          </button>
        </header>

        {erro && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{erro}</p>}
        {aviso && (
          <p className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">
            {aviso}
          </p>
        )}

        {talao && (
          <RevisaoTalao talao={talao} onGravada={gravada} onCancelar={() => setTalao(null)} onSessaoExpirada={tratarSessao} />
        )}

        <section className="divide-y divide-borda rounded-xl border border-borda bg-cartao">
          {compras === null && !erro && <p className="p-6 text-sm text-texto-suave">A carregar...</p>}
          {compras?.length === 0 && (
            <p className="p-6 text-sm text-texto-suave">Ainda não tens compras. Fotografa um talão para começar.</p>
          )}
          {compras?.map((compra) => (
            // <details>: abre e fecha sozinho ao clicar no <summary>, sem precisar de estado em React.
            <details key={compra.id} className="group p-4">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
                <div>
                  <p className="font-medium text-texto">{compra.loja}</p>
                  <p className="text-xs text-texto-suave">
                    {dataCurta(compra.data)} · {compra.itens.length} produtos
                  </p>
                </div>
                <span className="font-semibold text-texto">{euros(compra.total)}</span>
              </summary>
              <ul className="mt-3 space-y-1 border-t border-borda pt-3 text-sm">
                {compra.itens.map((item, i) => (
                  <li key={i} className="flex justify-between gap-4 text-texto-suave">
                    <span>
                      {item.descricao}
                      {item.quantidade !== 1 && <span className="text-xs"> × {item.quantidade.toLocaleString("pt-PT")}</span>}
                    </span>
                    <span className="text-texto">{euros(item.preco)}</span>
                  </li>
                ))}
              </ul>
            </details>
          ))}
        </section>
      </div>
    </main>
  );
}
