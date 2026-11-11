"use client";

import { useEffect, useState } from "react";

import { ID_NOTA_DEMO } from "@/components/NotaDemo";
import {
  eBloqueadoNaDemo,
  ErroApi,
  eSoPlanosPagos,
  pedirApi,
  SessaoExpirada,
  type JuncaoProdutos,
  type ProdutoResumo,
} from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { TEXTOS_PRECOS_LOJAS as T } from "@/lib/textosPrecosLojas";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

import {
  ESTILO_BOTAO,
  ESTILO_BOTAO_PRINCIPAL,
  ESTILO_CAMPO,
  ESTILO_ERRO,
  ESTILO_SUCESSO,
  textoLojas,
} from "./formatosPrecos";
import ListaJuncoes from "./ListaJuncoes";
import { useComAtraso } from "./useComAtraso";

type Props = {
  chave: string; // o produto aberto: é o destino (o outro passa a contar como este)
  nome: string;
  juncoes: JuncaoProdutos[]; // as que foram juntadas a este produto
  onMudou: () => void;
  onPlanoPago: (mensagem: string) => void;
  onSessaoExpirada: (e: unknown) => void;
};

type Candidatos = { pedido: string; produtos: ProdutoResumo[] | null };
type Mensagem = { tipo: "sucesso" | "erro"; texto: string } | null;

// "É o mesmo produto": junta outro produto da lista a este, com confirmação; mostra os já juntados (com desfazer).
// Na demo os botões ficam desligados (a API responderia 423) e a NotaDemo do topo explica porquê.
export default function JuntarProdutos(props: Props) {
  const { chave, nome, juncoes, onMudou, onPlanoPago, onSessaoExpirada } = props;
  const demo = useSessaoDemo();
  const f = useFormatos();
  const [aberto, setAberto] = useState(false);
  const [termo, setTermo] = useState("");
  const termoAtrasado = useComAtraso(termo.trim());
  const [candidatos, setCandidatos] = useState<Candidatos | null>(null);
  const [escolhido, setEscolhido] = useState<ProdutoResumo | null>(null);
  const [aConfirmar, setAConfirmar] = useState(false);
  const [aEnviar, setAEnviar] = useState(false);
  const [mensagem, setMensagem] = useState<Mensagem>(null);

  const pedido = termoAtrasado;

  useEffect(() => {
    if (!aberto) return;
    let cancelado = false;
    const q = termoAtrasado ? `?q=${encodeURIComponent(termoAtrasado)}` : "";
    pedirApi<ProdutoResumo[]>(`/compras/produtos${q}`)
      .then((produtos) => {
        if (!cancelado) setCandidatos({ pedido, produtos: produtos.filter((p) => p.chave !== chave) });
      })
      .catch((e) => {
        if (cancelado) return;
        if (e instanceof SessaoExpirada) onSessaoExpirada(e);
        else if (eSoPlanosPagos(e)) onPlanoPago(typeof e.detalhe === "string" ? e.detalhe : T.soPlanosPagos);
        else setCandidatos({ pedido, produtos: null });
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aberto, pedido, chave]);

  function fechar() {
    setAberto(false);
    setTermo("");
    setEscolhido(null);
    setAConfirmar(false);
  }

  function tratarErro(e: unknown, generica: string) {
    if (e instanceof SessaoExpirada) onSessaoExpirada(e);
    else if (eBloqueadoNaDemo(e)) return; // a faixa da demo já explica
    else if (eSoPlanosPagos(e)) onPlanoPago(typeof e.detalhe === "string" ? e.detalhe : T.soPlanosPagos);
    // 404/422 trazem uma explicação da API (ex.: "Estes produtos já estão juntos ao contrário.").
    else if (e instanceof ErroApi && typeof e.detalhe === "string") setMensagem({ tipo: "erro", texto: e.detalhe });
    else setMensagem({ tipo: "erro", texto: generica });
  }

  async function juntar() {
    if (!escolhido) return;
    setAEnviar(true);
    setMensagem(null);
    try {
      await pedirApi<void>("/compras/produtos/juntar", { chave_origem: escolhido.chave, chave_destino: chave });
      setMensagem({ tipo: "sucesso", texto: preencher(T.juntado, { origem: escolhido.nome, destino: nome }) });
      fechar();
      onMudou();
    } catch (e) {
      tratarErro(e, T.erroJuntar);
      setAConfirmar(false);
    } finally {
      setAEnviar(false);
    }
  }

  const aCarregar = aberto && candidatos?.pedido !== pedido;
  const lista = candidatos?.produtos ?? null;
  const descricaoDemo = demo ? ID_NOTA_DEMO : undefined;

  return (
    <section aria-labelledby="juntar-titulo" className="space-y-3 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
      <h3 id="juntar-titulo" className="text-base font-semibold text-texto">
        {T.juntarTitulo}
      </h3>
      <p className="text-sm text-texto-suave">{T.juntarExplicacao}</p>

      <div aria-live="polite">
        {mensagem && <p className={mensagem.tipo === "erro" ? ESTILO_ERRO : ESTILO_SUCESSO}>{mensagem.texto}</p>}
      </div>

      {juncoes.length > 0 && <h4 className="text-sm font-semibold text-texto">{T.juntadosAqui}</h4>}
      <ListaJuncoes juncoes={juncoes} onMudou={onMudou} onPlanoPago={onPlanoPago} onSessaoExpirada={onSessaoExpirada} />

      {!aberto && (
        <button
          type="button"
          disabled={demo}
          aria-describedby={descricaoDemo}
          onClick={() => {
            setMensagem(null);
            setAberto(true);
          }}
          className={`${ESTILO_BOTAO} w-full sm:w-auto`}
        >
          {T.juntarAbrir}
        </button>
      )}

      {aberto && (
        <div className="space-y-3 border-t border-borda pt-3">
          <label className="block">
            <span className="text-sm text-texto-suave">{T.juntarPesquisa}</span>
            <input
              type="search"
              value={termo}
              maxLength={100}
              onChange={(e) => {
                setTermo(e.target.value);
                setAConfirmar(false);
              }}
              placeholder={T.marcadorPesquisa}
              autoComplete="off"
              className={`${ESTILO_CAMPO} min-h-11`}
            />
          </label>

          <fieldset>
            <legend className="mb-2 text-sm text-texto">{preencher(T.juntarEscolher, { nome })}</legend>
            <div aria-live="polite" aria-busy={aCarregar}>
              {aCarregar && <p className="text-sm text-texto-suave">{T.aProcurar}</p>}
              {!aCarregar && candidatos && lista === null && <p className={ESTILO_ERRO}>{T.erroLista}</p>}
              {!aCarregar && lista?.length === 0 && <p className="text-sm text-texto-suave">{T.juntarSemOutros}</p>}
            </div>
            {!aCarregar && lista && lista.length > 0 && (
              <ul className="max-h-72 divide-y divide-borda overflow-y-auto rounded-lg border border-borda">
                {lista.map((produto) => (
                  <li key={produto.chave}>
                    <label className="flex min-h-11 cursor-pointer items-start gap-3 p-3 hover:bg-fundo has-[:checked]:bg-fundo">
                      <input
                        type="radio"
                        name="produto-igual"
                        value={produto.chave}
                        checked={escolhido?.chave === produto.chave}
                        onChange={() => {
                          setEscolhido(produto);
                          setAConfirmar(false);
                        }}
                        className="mt-1 h-4 w-4 shrink-0 accent-destaque"
                      />
                      <span className="min-w-0">
                        <span className="block break-words text-sm font-medium text-texto">{produto.nome}</span>
                        <span className="block text-xs text-texto-suave">
                          {textoLojas(produto.n_lojas)} · {preencher(T.ultimaCompra, { data: f.data(produto.ultima_data) })}
                        </span>
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </fieldset>

          {/* Confirmação no próprio ecrã (sem window.confirm): diz exatamente o que vai acontecer. */}
          {aConfirmar && escolhido ? (
            <div role="alert" className="space-y-3 rounded-lg border border-amber-300 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950/40">
              <p className="break-words text-sm text-amber-900 dark:text-amber-200">
                {preencher(T.juntarConfirmar, { origem: escolhido.nome, destino: nome })}
              </p>
              <div className="flex flex-col gap-2 sm:flex-row">
                <button type="button" disabled={aEnviar} onClick={juntar} className={ESTILO_BOTAO_PRINCIPAL}>
                  {aEnviar ? T.aJuntar : T.juntarSim}
                </button>
                <button type="button" disabled={aEnviar} onClick={() => setAConfirmar(false)} className={ESTILO_BOTAO}>
                  {T.juntarNao}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-2 sm:flex-row">
              <button
                type="button"
                disabled={!escolhido || demo}
                aria-describedby={descricaoDemo}
                onClick={() => setAConfirmar(true)}
                className={ESTILO_BOTAO_PRINCIPAL}
              >
                {T.juntarBotao}
              </button>
              <button type="button" onClick={fechar} className={ESTILO_BOTAO}>
                {T.juntarFechar}
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
