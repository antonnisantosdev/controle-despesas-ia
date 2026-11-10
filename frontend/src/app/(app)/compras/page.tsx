"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import AvisoLimite from "@/components/AvisoLimite";
import AvisoPlanoPago from "@/components/AvisoPlanoPago";
import NotaDemo, { ID_NOTA_DEMO } from "@/components/NotaDemo";
import {
  eBloqueadoNaDemo,
  apagarToken,
  eLimiteDiario,
  enviarFicheiro,
  ErroApi,
  eSoPlanosPagos,
  pedirApi,
  pedirEstadoPlano,
  SessaoExpirada,
  type Compra,
  type Talao,
} from "@/lib/api";
import { reduzirImagem } from "@/lib/imagem";
import { temFuncoesPagas } from "@/lib/planos";
import { TEXTOS_PLANO_PAGO } from "@/lib/textosPlanos";
import { TEXTOS_PRECOS_LOJAS } from "@/lib/textosPrecosLojas";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

import { euros } from "../dashboard/formatos";
import PrecosPorLoja from "./PrecosPorLoja";
import RevisaoTalao from "./RevisaoTalao";

type Separador = "taloes" | "precos";
const SEPARADORES: { id: Separador; nome: string }[] = [
  { id: "taloes", nome: TEXTOS_PRECOS_LOJAS.separadorTaloes },
  { id: "precos", nome: TEXTOS_PRECOS_LOJAS.separadorPrecos },
];

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
  // Na demo (só leitura) não se leem talões novos; a API recusa-os na mesma (423).
  const demo = useSessaoDemo();
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [semPedidos, setSemPedidos] = useState(false); // 429: chegou ao limite de pedidos à IA
  // Ler talões é só dos planos pagos: no Free fica a mensagem do aviso e o botão desaparece.
  const [soPlanosPagos, setSoPlanosPagos] = useState<string | null>(null);
  // O botão só aparece depois de o /plano responder (ou falhar): assim o Free não o vê piscar.
  const [planoVerificado, setPlanoVerificado] = useState(false);
  const [eFree, setEFree] = useState(false);
  const [separador, setSeparador] = useState<Separador>("taloes");
  // O separador Preços só pede à API quando é aberto pela primeira vez; depois fica montado (guarda a pesquisa).
  const [precosAbertos, setPrecosAbertos] = useState(false);
  const botoesSeparador = useRef<(HTMLButtonElement | null)[]>([]);

  function mudarSeparador(novo: Separador) {
    setSeparador(novo);
    if (novo === "precos") setPrecosAbertos(true);
  }

  // Setas esquerda/direita mudam de separador (padrão dos separadores para teclado e leitores de ecrã).
  function teclaSeparador(e: React.KeyboardEvent, indice: number) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const seguinte = (indice + (e.key === "ArrowRight" ? 1 : -1) + SEPARADORES.length) % SEPARADORES.length;
    mudarSeparador(SEPARADORES[seguinte].id);
    botoesSeparador.current[seguinte]?.focus();
  }

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
    // Avisa logo no Free, sem esperar que a leitura falhe. Se o /plano falhar, o botão fica:
    // a API responde 402 na mesma, e o aviso aparece nessa altura.
    pedirEstadoPlano()
      .then((estado) => {
        if (!temFuncoesPagas(estado.plano)) {
          setSoPlanosPagos(TEXTOS_PLANO_PAGO.talao);
          setEFree(true);
        }
      })
      .catch(() => {}) // a sessão expirada já é tratada pelo pedido das compras
      .finally(() => setPlanoVerificado(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function lerFoto(ficheiro: File) {
    setALer(true);
    setErro("");
    setAviso("");
    setSemPedidos(false);
    setTalao(null);
    try {
      const pequena = await reduzirImagem(ficheiro);
      setTalao(await enviarFicheiro<Talao>("/compras/ler", "foto", pequena));
    } catch (e) {
      if (e instanceof SessaoExpirada) tratarSessao(e);
      else if (eBloqueadoNaDemo(e)) return; // 423 da demo: a faixa já explica
      else if (eLimiteDiario(e)) setSemPedidos(true);
      else if (eSoPlanosPagos(e)) setSoPlanosPagos(typeof e.detalhe === "string" ? e.detalhe : TEXTOS_PLANO_PAGO.talao);
      // 413/415/422 (foto inválida) e 503 (IA em baixo) trazem uma explicação da API.
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
          {separador === "taloes" && planoVerificado && !soPlanosPagos && (
            <button
              type="button"
              disabled={aLer || demo}
              aria-describedby={demo ? ID_NOTA_DEMO : undefined}
              onClick={() => entradaFoto.current?.click()}
              className="rounded-lg bg-destaque px-4 py-2 text-sm font-medium text-white hover:bg-destaque-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {aLer ? "A IA está a ler o talão..." : "📷 Fotografar talão"}
            </button>
          )}
        </header>

        <NotaDemo />

        <div role="tablist" aria-label={TEXTOS_PRECOS_LOJAS.rotuloSeparadores} className="flex gap-1 border-b border-borda">
          {SEPARADORES.map(({ id, nome }, indice) => {
            const ativo = separador === id;
            return (
              <button
                key={id}
                ref={(botao) => {
                  botoesSeparador.current[indice] = botao;
                }}
                type="button"
                role="tab"
                id={`separador-${id}`}
                aria-selected={ativo}
                aria-controls={`painel-${id}`}
                tabIndex={ativo ? 0 : -1}
                onClick={() => mudarSeparador(id)}
                onKeyDown={(e) => teclaSeparador(e, indice)}
                className={`-mb-px min-h-11 border-b-2 px-4 text-sm font-medium focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-destaque ${
                  ativo ? "border-destaque font-semibold text-texto" : "border-transparent text-texto-suave hover:text-texto"
                }`}
              >
                {nome}
              </button>
            );
          })}
        </div>

        <div
          role="tabpanel"
          id="painel-taloes"
          aria-labelledby="separador-taloes"
          hidden={separador !== "taloes"}
          className="space-y-6"
        >
          {erro && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{erro}</p>}
          {semPedidos && <AvisoLimite />}
          {soPlanosPagos && <AvisoPlanoPago mensagem={soPlanosPagos} />}
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
              <p className="p-6 text-sm text-texto-suave">
                {soPlanosPagos ? "Ainda não tens compras." : "Ainda não tens compras. Fotografa um talão para começar."}
              </p>
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

        <div role="tabpanel" id="painel-precos" aria-labelledby="separador-precos" hidden={separador !== "precos"}>
          {precosAbertos && <PrecosPorLoja eFree={eFree} onSessaoExpirada={tratarSessao} />}
        </div>
      </div>
    </main>
  );
}
