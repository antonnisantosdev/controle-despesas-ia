"use client";

import { useEffect, useState } from "react";

import AvisoPlanoPago from "@/components/AvisoPlanoPago";
import { eSoPlanosPagos, pedirApi, SessaoExpirada, type JuncaoProdutos, type ProdutoResumo } from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { TEXTOS_PRECOS_LOJAS as T } from "@/lib/textosPrecosLojas";

import DetalheProduto from "./DetalheProduto";
import { ESTILO_BOTAO, ESTILO_CAMPO, ESTILO_ERRO, textoCompras, textoLojas } from "./formatosPrecos";
import ListaJuncoes from "./ListaJuncoes";
import { useComAtraso } from "./useComAtraso";

const MAX_PRODUTOS = 50; // o máximo que a API devolve

type Props = {
  // O /plano já disse que é Free: mostra logo o aviso, sem pedir à API.
  eFree: boolean;
  onSessaoExpirada: (e: unknown) => void;
};

// Resposta da lista, com o pedido a que corresponde: enquanto não bate certo com o pedido atual, está a carregar.
type Resultado = { pedido: string; produtos: ProdutoResumo[] | null; erro: boolean };

export default function PrecosPorLoja({ eFree, onSessaoExpirada }: Props) {
  const f = useFormatos();
  const [termo, setTermo] = useState("");
  const termoAtrasado = useComAtraso(termo.trim());
  const [versao, setVersao] = useState(0); // muda para pedir outra vez (tentar outra vez, depois de juntar)
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [planoPago, setPlanoPago] = useState<string | null>(null); // a mensagem do 402
  const [aberto, setAberto] = useState<{ chave: string; nome: string } | null>(null);
  // As junções do utilizador (GET /compras/produtos/juntar), pedidas outra vez sempre que algo muda.
  const [juncoes, setJuncoes] = useState<{ versao: number; lista: JuncaoProdutos[] | null } | null>(null);
  // Depois de desfazer a última junção, a secção fica (com a mensagem) até sair da página.
  const [teveJuncoes, setTeveJuncoes] = useState(false);

  const avisoPlano = planoPago ?? (eFree ? T.soPlanosPagos : null);
  const pedido = `${versao}|${termoAtrasado}`;

  useEffect(() => {
    if (avisoPlano) return;
    let cancelado = false;
    const q = termoAtrasado ? `?q=${encodeURIComponent(termoAtrasado)}` : "";
    pedirApi<ProdutoResumo[]>(`/compras/produtos${q}`)
      .then((produtos) => {
        if (!cancelado) setResultado({ pedido, produtos, erro: false });
      })
      .catch((e) => {
        if (cancelado) return;
        if (e instanceof SessaoExpirada) onSessaoExpirada(e);
        else if (eSoPlanosPagos(e)) setPlanoPago(typeof e.detalhe === "string" ? e.detalhe : T.soPlanosPagos);
        else setResultado({ pedido, produtos: null, erro: true });
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pedido, avisoPlano]);

  useEffect(() => {
    if (avisoPlano) return;
    let cancelado = false;
    pedirApi<JuncaoProdutos[]>("/compras/produtos/juntar")
      .then((lista) => {
        if (cancelado) return;
        setJuncoes({ versao, lista });
        if (lista.length > 0) setTeveJuncoes(true);
      })
      .catch((e) => {
        if (cancelado) return;
        if (e instanceof SessaoExpirada) onSessaoExpirada(e);
        else if (eSoPlanosPagos(e)) setPlanoPago(typeof e.detalhe === "string" ? e.detalhe : T.soPlanosPagos);
        else setJuncoes({ versao, lista: null });
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [versao, avisoPlano]);

  const mudou = () => setVersao((v) => v + 1);
  const listaJuncoes = juncoes?.lista ?? [];

  if (avisoPlano) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-texto-suave">{T.explicacao}</p>
        <AvisoPlanoPago mensagem={avisoPlano} />
      </div>
    );
  }

  if (aberto) {
    return (
      <DetalheProduto
        chave={aberto.chave}
        nomeInicial={aberto.nome}
        juncoes={listaJuncoes}
        onVoltar={() => setAberto(null)}
        onMudou={mudou}
        onPlanoPago={setPlanoPago}
        onSessaoExpirada={onSessaoExpirada}
      />
    );
  }

  const aCarregar = resultado?.pedido !== pedido;
  // Enquanto o pedido novo não chega, a lista anterior fica à vista (sem piscar).
  const produtos = resultado?.produtos ?? null;

  return (
    <div className="space-y-4">
      <p className="text-sm text-texto-suave">{T.explicacao}</p>

      <label className="block">
        <span className="text-sm text-texto-suave">{T.rotuloPesquisa}</span>
        <input
          type="search"
          value={termo}
          maxLength={100}
          onChange={(e) => setTermo(e.target.value)}
          placeholder={T.marcadorPesquisa}
          autoComplete="off"
          className={`${ESTILO_CAMPO} min-h-11`}
        />
      </label>

      {/* aria-live: quem usa leitor de ecrã ouve "A procurar..." e o resultado sem sair do campo. */}
      <div aria-live="polite" aria-busy={aCarregar}>
        {aCarregar && !produtos && <p className="text-sm text-texto-suave">{T.aCarregar}</p>}
        {aCarregar && produtos && <p className="text-sm text-texto-suave">{T.aProcurar}</p>}

        {!aCarregar && resultado?.erro && (
          <div className={`${ESTILO_ERRO} flex flex-wrap items-center justify-between gap-2`}>
            <p>{T.erroLista}</p>
            <button type="button" onClick={() => setVersao((v) => v + 1)} className={ESTILO_BOTAO}>
              {T.tentarOutraVez}
            </button>
          </div>
        )}

        {!aCarregar && produtos?.length === 0 && (
          <p className="rounded-xl border border-borda bg-cartao p-6 text-sm text-texto-suave">
            {termoAtrasado ? preencher(T.semResultados, { termo: termoAtrasado }) : T.vazio}
          </p>
        )}
      </div>

      {produtos && produtos.length > 0 && !(resultado?.erro && !aCarregar) && (
        <ul className="divide-y divide-borda rounded-xl border border-borda bg-cartao">
          {produtos.map((produto) => (
            <li key={produto.chave}>
              <button
                type="button"
                onClick={() => setAberto({ chave: produto.chave, nome: produto.nome })}
                className="flex min-h-11 w-full items-center justify-between gap-3 p-4 text-left hover:bg-fundo focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-destaque"
              >
                <span className="min-w-0">
                  <span className="block break-words font-medium text-texto">{produto.nome}</span>
                  <span className="block text-xs text-texto-suave">
                    {textoLojas(produto.n_lojas)} · {textoCompras(produto.n_compras)} ·{" "}
                    {preencher(T.ultimaCompra, { data: f.data(produto.ultima_data) })}
                  </span>
                </span>
                <span aria-hidden="true" className="shrink-0 text-texto-suave">
                  ›
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {produtos?.length === MAX_PRODUTOS && <p className="text-xs text-texto-suave">{T.maximo}</p>}

      {juncoes?.lista === null && <p className={ESTILO_ERRO}>{T.juntadosErro}</p>}
      {(listaJuncoes.length > 0 || teveJuncoes) && (
        // Recolhível: é uma ferramenta de correção, não o principal do ecrã.
        <details className="rounded-xl border border-borda bg-cartao p-4">
          <summary className="flex min-h-11 cursor-pointer items-center text-sm font-semibold text-texto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque">
            {preencher(T.juntadosTitulo, { n: listaJuncoes.length })}
          </summary>
          <p className="mb-2 text-sm text-texto-suave">{T.juntadosExplicacao}</p>
          <ListaJuncoes
            juncoes={listaJuncoes}
            onMudou={mudou}
            onPlanoPago={setPlanoPago}
            onSessaoExpirada={onSessaoExpirada}
          />
        </details>
      )}
    </div>
  );
}
