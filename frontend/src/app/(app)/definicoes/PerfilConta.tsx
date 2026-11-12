"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { ID_NOTA_DEMO } from "@/components/NotaDemo";
import OpcaoGrande, { BOTAO_PRINCIPAL, BOTAO_SECUNDARIO } from "@/components/OpcaoGrande";
import {
  apagarRespostasBoasVindas,
  apagarToken,
  eBloqueadoNaDemo,
  eSessaoDemo,
  ErroApi,
  lerBoasVindas,
  responderBoasVindas,
  SessaoExpirada,
  type BoasVindasGuardadas,
} from "@/lib/api";
import { bancosDe, moedaDosBancos, paisesDosBancos, type Bancos } from "@/lib/boasVindas";
import { useAplicarPerfil, useConta, useEstadoPlano } from "@/lib/conta";
import type { Moeda, Pais } from "@/lib/formatos";
import { useTextos } from "@/lib/textos";
import {
  DICIONARIO_BOAS_VINDAS,
  MOTIVOS,
  OBJETIVOS,
  OBJETIVOS_POR_PAIS,
  TEXTOS_PAIS,
  type Motivo,
  type Objetivo,
} from "@/lib/textosBoasVindas";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

// Campos com 44 px de altura (toque), a mesma largura das opções por baixo e o foco visível da app.
const ESTILO_CAMPO =
  "mt-1.5 block min-h-11 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-base text-texto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:cursor-not-allowed disabled:opacity-50";
const ESTILO_ROTULO = "block text-sm font-medium text-texto";
const ESTILO_AJUDA = "mt-1.5 block text-xs text-texto-suave";

type Formulario = { pais: Pais; bancos: Bancos; moeda: Moeda; motivo: Motivo | null; objetivos: Objetivo[] };

function formularioDe(dados: Pick<BoasVindasGuardadas, "pais" | "paises_bancos" | "moeda" | "motivo" | "objetivos">): Formulario {
  return {
    pais: dados.pais,
    bancos: bancosDe(dados.paises_bancos),
    moeda: dados.moeda,
    motivo: dados.motivo,
    objetivos: dados.objetivos ?? [],
  };
}

// "O teu perfil" (GET e PUT /conta/boas-vindas): país, bancos, moeda (só muda numa conta sem dados),
// motivo e objetivos, e o botão para apagar as duas respostas opcionais (DELETE). Na demo fica desligado.
export default function PerfilConta() {
  const { TEXTOS_DEFINICOES: T, TEXTOS_BOAS_VINDAS } = useTextos(DICIONARIO_BOAS_VINDAS);
  const conta = useConta();
  const brasilDisponivel = useEstadoPlano()?.brasil_disponivel === true;
  const demo = useSessaoDemo();
  const aplicarPerfil = useAplicarPerfil();
  const router = useRouter();
  const [form, setForm] = useState<Formulario | null>(null);
  const [erroCarregar, setErroCarregar] = useState(false);
  const [aGuardar, setAGuardar] = useState(false);
  const [mensagem, setMensagem] = useState<{ ok: boolean; texto: string }[]>([]);

  // Na demo não se pede nada (a API responde 423): mostra-se o perfil da conta, desligado.
  const dados: Formulario | null = demo
    ? { pais: conta.pais, bancos: bancosDe(conta.paisesBancos), moeda: conta.moeda, motivo: null, objetivos: [] }
    : form;

  useEffect(() => {
    // eSessaoDemo() lê já o browser: o useSessaoDemo() começa em false ao carregar a página do zero.
    if (demo || eSessaoDemo()) return;
    let cancelado = false;
    lerBoasVindas()
      .then((lidas) => {
        if (!cancelado) setForm(formularioDe(lidas));
      })
      .catch((e) => {
        if (cancelado) return;
        if (e instanceof SessaoExpirada) {
          apagarToken();
          router.replace("/login");
        } else {
          setErroCarregar(true);
        }
      });
    return () => {
      cancelado = true;
    };
  }, [demo, router]);

  function mudar(campos: Partial<Formulario>) {
    setMensagem([]);
    setForm((atual) => (atual ? { ...atual, ...campos } : atual));
  }

  function tratarErro(e: unknown) {
    if (e instanceof SessaoExpirada) {
      apagarToken();
      router.replace("/login");
    } else if (!eBloqueadoNaDemo(e)) {
      // 429 e 503 trazem a explicação da API, no país da conta.
      const temTexto = e instanceof ErroApi && e.status !== 422 && typeof e.detalhe === "string";
      setMensagem([{ ok: false, texto: temTexto ? (e.detalhe as string) : TEXTOS_BOAS_VINDAS.erroGuardar }]);
    }
  }

  async function guardar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!form || demo || aGuardar) return;
    setMensagem([]);
    setAGuardar(true);
    try {
      const guardadas = await responderBoasVindas({
        pais: form.pais,
        paises_bancos: paisesDosBancos(form.bancos),
        moeda: moedaDosBancos(form.bancos, form.moeda),
        motivo: form.motivo,
        objetivos: form.objetivos.length > 0 ? form.objetivos : null,
      });
      aplicarPerfil(guardadas); // a língua, o fuso e os formatos mudam logo
      setForm(formularioDe(guardadas));
      // A moeda não mudou (a conta já tem dados): o resto ficou guardado. Os textos vêm do país novo no próximo desenho.
      const textos = DICIONARIO_BOAS_VINDAS[guardadas.pais].TEXTOS_DEFINICOES;
      setMensagem([
        { ok: true, texto: textos.guardado },
        ...(guardadas.aviso ? [{ ok: false, texto: textos.erroMoedaComDados }] : []),
      ]);
    } catch (e) {
      tratarErro(e);
    } finally {
      setAGuardar(false);
    }
  }

  async function apagarRespostas() {
    if (!form || demo || aGuardar) return;
    setMensagem([]);
    setAGuardar(true);
    try {
      await apagarRespostasBoasVindas();
      setForm({ ...form, motivo: null, objetivos: [] });
      setMensagem([{ ok: true, texto: T.guardado }]);
    } catch (e) {
      tratarErro(e);
    } finally {
      setAGuardar(false);
    }
  }

  const desligado = demo || aGuardar || !dados;
  // Os objetivos do país, mais os que já estiverem escolhidos (ex.: quem mudou de Portugal para o Brasil).
  const listaObjetivos = dados
    ? OBJETIVOS.filter((o) => OBJETIVOS_POR_PAIS[conta.pais].includes(o) || dados.objetivos.includes(o))
    : [];
  const temRespostas = !!form && (form.motivo !== null || form.objetivos.length > 0);
  const descrito = demo ? ID_NOTA_DEMO : undefined;

  return (
    <section aria-labelledby="titulo-perfil" className="space-y-4 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
      <div className="space-y-1">
        <h2 id="titulo-perfil" className="text-lg font-semibold text-texto">
          {T.tituloPerfil}
        </h2>
        <p className="text-sm text-texto-suave">{T.descricaoPerfil}</p>
      </div>

      {erroCarregar && (
        <p role="alert" className="max-w-xl rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
          {T.erroCarregar}
        </p>
      )}
      {!dados && !erroCarregar && (
        <p role="status" className="max-w-xl rounded-md bg-fundo p-3 text-sm text-texto-suave motion-safe:animate-pulse">
          {T.aCarregar}
        </p>
      )}

      {dados && (
        <form onSubmit={guardar} className="max-w-xl space-y-5" aria-busy={aGuardar}>
          <div>
            <label htmlFor="perfil-pais" className={ESTILO_ROTULO}>
              {T.rotuloPais}
            </label>
            <select
              id="perfil-pais"
              value={dados.pais}
              onChange={(e) => mudar({ pais: e.target.value as Pais })}
              disabled={desligado}
              aria-describedby={descrito ? `ajuda-pais ${descrito}` : "ajuda-pais"}
              className={ESTILO_CAMPO}
            >
              <option value="PT">{TEXTOS_PAIS.opcaoPortugal}</option>
              {/* Brasil fechado (até haver termos para a LGPD): só para quem o pode escolher ou já o tem. */}
              {(brasilDisponivel || dados.pais === "BR") && <option value="BR">{TEXTOS_PAIS.opcaoBrasil}</option>}
            </select>
            <p id="ajuda-pais" className={ESTILO_AJUDA}>
              {T.ajudaPais}
            </p>
          </div>

          <div>
            <label htmlFor="perfil-bancos" className={ESTILO_ROTULO}>
              {T.rotuloBancos}
            </label>
            <select
              id="perfil-bancos"
              value={dados.bancos}
              onChange={(e) => mudar({ bancos: e.target.value as Bancos })}
              disabled={desligado}
              aria-describedby={descrito}
              className={ESTILO_CAMPO}
            >
              <option value="PT">{TEXTOS_BOAS_VINDAS.bancosPortugal}</option>
              <option value="BR">{TEXTOS_BOAS_VINDAS.bancosBrasil}</option>
              <option value="ambos">{TEXTOS_BOAS_VINDAS.bancosOsDois}</option>
            </select>
          </div>

          {/* Com bancos de um só país a moeda é a desse país (fica desligada, só a mostrar). */}
          <div>
            <label htmlFor="perfil-moeda" className={ESTILO_ROTULO}>
              {T.rotuloMoeda}
            </label>
            <select
              id="perfil-moeda"
              value={moedaDosBancos(dados.bancos, dados.moeda) ?? dados.moeda}
              onChange={(e) => mudar({ moeda: e.target.value as Moeda })}
              disabled={desligado || dados.bancos !== "ambos"}
              aria-describedby={descrito ? `ajuda-moeda ${descrito}` : "ajuda-moeda"}
              className={ESTILO_CAMPO}
            >
              <option value="EUR">{TEXTOS_BOAS_VINDAS.moedaEuro}</option>
              <option value="BRL">{TEXTOS_BOAS_VINDAS.moedaReal}</option>
            </select>
            <p id="ajuda-moeda" className={ESTILO_AJUDA}>
              {T.ajudaMoeda}
            </p>
          </div>

          <div>
            <label htmlFor="perfil-motivo" className={ESTILO_ROTULO}>
              {T.rotuloMotivo}
            </label>
            <select
              id="perfil-motivo"
              value={dados.motivo ?? ""}
              onChange={(e) => mudar({ motivo: (e.target.value || null) as Motivo | null })}
              disabled={desligado}
              aria-describedby={descrito}
              className={ESTILO_CAMPO}
            >
              <option value="">{T.semResposta}</option>
              {MOTIVOS.map((chave) => (
                <option key={chave} value={chave}>
                  {TEXTOS_BOAS_VINDAS.motivos[chave]}
                </option>
              ))}
            </select>
          </div>

          <fieldset>
            <legend className={ESTILO_ROTULO}>{T.rotuloObjetivos}</legend>
            {dados.objetivos.length === 0 && <p className={ESTILO_AJUDA}>{T.semResposta}</p>}
            <div className="mt-2 space-y-2">
              {listaObjetivos.map((chave) => (
                <OpcaoGrande
                  key={chave}
                  tipo="checkbox"
                  nome="objetivos"
                  marcada={dados.objetivos.includes(chave)}
                  desligada={desligado}
                  aoMudar={() =>
                    mudar({
                      objetivos: dados.objetivos.includes(chave)
                        ? dados.objetivos.filter((o) => o !== chave)
                        : [...dados.objetivos, chave],
                    })
                  }
                >
                  {TEXTOS_BOAS_VINDAS.objetivos[chave]}
                </OpcaoGrande>
              ))}
            </div>
          </fieldset>

          {mensagem.map((linha) => (
            <p
              key={linha.texto}
              role={linha.ok ? "status" : "alert"}
              className={
                linha.ok
                  ? "rounded-md bg-emerald-50 p-3 text-sm text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200"
                  : "rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300"
              }
            >
              {linha.texto}
            </p>
          ))}

          <div className="flex flex-col gap-3 border-t border-borda pt-5 sm:flex-row">
            <button type="submit" disabled={desligado} aria-busy={aGuardar} aria-describedby={descrito} className={BOTAO_PRINCIPAL}>
              {aGuardar ? TEXTOS_BOAS_VINDAS.aGuardar : T.guardar}
            </button>
            <button
              type="button"
              onClick={apagarRespostas}
              disabled={desligado || !temRespostas}
              aria-describedby={descrito}
              className={BOTAO_SECUNDARIO}
            >
              {T.limparRespostas}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
