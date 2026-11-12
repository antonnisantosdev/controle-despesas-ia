"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import Logo from "@/components/Logo";
import Opcao, { BOTAO_PRINCIPAL, BOTAO_TEXTO } from "@/components/OpcaoGrande";
import RodapeLegal from "@/components/RodapeLegal";
import { apagarToken, eBloqueadoNaDemo, ErroApi, responderBoasVindas, SessaoExpirada } from "@/lib/api";
import { moedaDosBancos, paisesDosBancos, type Bancos } from "@/lib/boasVindas";
import { useAplicarPerfil, useEstadoPlano } from "@/lib/conta";
import type { Moeda, Pais } from "@/lib/formatos";
import { preencher } from "@/lib/planos";
import { useTextos } from "@/lib/textos";
import {
  DICIONARIO_BOAS_VINDAS,
  MOTIVOS,
  OBJETIVOS_POR_PAIS,
  TEXTOS_PAIS,
  type Motivo,
  type Objetivo,
} from "@/lib/textosBoasVindas";
import { DICIONARIO_COMUNS } from "@/lib/textosComuns";
import { useSair } from "@/lib/useSair";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

const TOTAL_PASSOS = 4;

// Questionário de boas-vindas (contas novas, uma só vez): 1 país, 2 cartões e contas (e moeda, se forem dos dois
// países), 3 motivo (opcional), 4 objetivos (opcional). Uma pergunta por ecrã. Só grava no fim (PUT /conta/boas-vindas).
// O ecrã 1 é neutro; os seguintes vêm já na língua do país escolhido. A IA não usa estas respostas.
export default function PaginaBoasVindas() {
  const router = useRouter();
  const demo = useSessaoDemo();
  const estado = useEstadoPlano();
  const aplicarPerfil = useAplicarPerfil();
  const [passo, setPasso] = useState(1);
  const [pais, setPais] = useState<Pais | null>(null);
  const [bancos, setBancos] = useState<Bancos | null>(null);
  const [moeda, setMoeda] = useState<Moeda | null>(null);
  const [motivo, setMotivo] = useState<Motivo | null>(null);
  const [objetivos, setObjetivos] = useState<Objetivo[]>([]);
  const [erro, setErro] = useState("");
  const [aGuardar, setAGuardar] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [moedaNaoMudou, setMoedaNaoMudou] = useState(false);
  const titulo = useRef<HTMLHeadingElement>(null);

  const { TEXTOS_BOAS_VINDAS: T, TEXTOS_DEFINICOES } = DICIONARIO_BOAS_VINDAS[pais ?? "PT"];

  // Quem não tem o questionário por fazer (contas antigas, demo, ou quem acabou de o gravar) vai para a app.
  useEffect(() => {
    if (enviado) return;
    if (demo || (estado && !estado.boas_vindas_pendente)) router.replace("/dashboard");
  }, [demo, estado, enviado, router]);

  // Em cada ecrã novo, o foco vai para a pergunta (leitores de ecrã e teclado começam por ela).
  useEffect(() => {
    titulo.current?.focus();
  }, [passo]);

  function irPara(novo: number) {
    setErro("");
    setPasso(novo);
  }

  function continuarPais() {
    if (!pais) return setErro(TEXTOS_PAIS.erroPais);
    irPara(2);
  }

  function continuarBancos() {
    if (!bancos) return setErro(T.erroBancos);
    if (bancos === "ambos" && !moeda) return setErro(T.erroMoeda);
    irPara(3);
  }

  async function terminar(comObjetivos: boolean) {
    if (!pais || !bancos || aGuardar) return;
    // Só os objetivos que aparecem no país escolhido (quem voltou ao ecrã 1 e mudou de país).
    const escolhidos = objetivos.filter((objetivo) => OBJETIVOS_POR_PAIS[pais].includes(objetivo));
    setErro("");
    setAGuardar(true);
    setEnviado(true);
    try {
      const guardadas = await responderBoasVindas({
        pais,
        paises_bancos: paisesDosBancos(bancos),
        moeda: moedaDosBancos(bancos, moeda),
        motivo,
        objetivos: comObjetivos && escolhidos.length > 0 ? escolhidos : null,
      });
      aplicarPerfil(guardadas); // os textos e os formatos da app passam já ao país escolhido
      if (guardadas.aviso) {
        // Raro numa conta nova: a moeda não mudou porque a conta já tem dados. O resto ficou gravado.
        setMoedaNaoMudou(true);
        setAGuardar(false);
        return;
      }
      router.replace("/dashboard");
    } catch (e) {
      setAGuardar(false);
      setEnviado(false);
      if (e instanceof SessaoExpirada) {
        apagarToken();
        router.replace("/login");
      } else if (eBloqueadoNaDemo(e)) {
        router.replace("/dashboard");
      } else {
        // 429 e 503 trazem uma explicação da API no país da conta; o resto fica com o texto geral.
        const temTexto = e instanceof ErroApi && e.status !== 422 && typeof e.detalhe === "string";
        setErro(temTexto ? (e.detalhe as string) : T.erroGuardar);
      }
    }
  }

  function alternarObjetivo(objetivo: Objetivo) {
    setObjetivos((atuais) => (atuais.includes(objetivo) ? atuais.filter((o) => o !== objetivo) : [...atuais, objetivo]));
  }

  if (moedaNaoMudou) {
    return (
      <Moldura passo={TOTAL_PASSOS} progresso={T.progresso}>
        <p role="alert" className="rounded-md bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
          {TEXTOS_DEFINICOES.erroMoedaComDados}
        </p>
        <button type="button" onClick={() => router.replace("/dashboard")} className={`${BOTAO_PRINCIPAL} sm:ml-auto`}>
          {T.continuar}
        </button>
      </Moldura>
    );
  }

  // Enquanto o /plano não chega (ou na demo / conta sem questionário por fazer) não se mostra o ecrã 1 por instantes.
  if (!enviado && (demo || !estado || !estado.boas_vindas_pendente)) return null;

  return (
    <Moldura passo={passo} progresso={T.progresso}>
      {passo === 1 && (
        <Pergunta titulo={TEXTOS_PAIS.tituloPais} subtitulo={TEXTOS_PAIS.subtituloPais} refTitulo={titulo}>
          <Opcao tipo="radio" nome="pais" marcada={pais === "PT"} aoMudar={() => setPais("PT")}>
            {TEXTOS_PAIS.opcaoPortugal}
          </Opcao>
          <Opcao tipo="radio" nome="pais" marcada={pais === "BR"} aoMudar={() => setPais("BR")}>
            {TEXTOS_PAIS.opcaoBrasil}
          </Opcao>
        </Pergunta>
      )}

      {passo === 2 && (
        <>
          <Pergunta titulo={T.tituloBancos} subtitulo={T.subtituloBancos} refTitulo={titulo}>
            <Opcao tipo="radio" nome="bancos" marcada={bancos === "PT"} aoMudar={() => setBancos("PT")}>
              {T.bancosPortugal}
            </Opcao>
            <Opcao tipo="radio" nome="bancos" marcada={bancos === "BR"} aoMudar={() => setBancos("BR")}>
              {T.bancosBrasil}
            </Opcao>
            <Opcao tipo="radio" nome="bancos" marcada={bancos === "ambos"} aoMudar={() => setBancos("ambos")}>
              {T.bancosOsDois}
            </Opcao>
          </Pergunta>
          {/* A moeda só se pergunta com contas dos dois países (com um só, é a desse país). */}
          {bancos === "ambos" && (
            <fieldset className="space-y-3 border-t border-borda pt-5">
              <legend className="text-lg font-semibold text-texto">{T.tituloMoeda}</legend>
              <p className="text-sm text-texto-suave">{T.subtituloMoeda}</p>
              <div className="space-y-2">
                <Opcao tipo="radio" nome="moeda" marcada={moeda === "EUR"} aoMudar={() => setMoeda("EUR")}>
                  {T.moedaEuro}
                </Opcao>
                <Opcao tipo="radio" nome="moeda" marcada={moeda === "BRL"} aoMudar={() => setMoeda("BRL")}>
                  {T.moedaReal}
                </Opcao>
              </div>
              <p className="text-sm text-texto-suave">{T.avisoMoeda}</p>
            </fieldset>
          )}
        </>
      )}

      {passo === 3 && (
        <Pergunta titulo={T.tituloMotivo} subtitulo={T.subtituloMotivo} refTitulo={titulo}>
          {MOTIVOS.map((chave) => (
            <Opcao key={chave} tipo="radio" nome="motivo" marcada={motivo === chave} aoMudar={() => setMotivo(chave)}>
              {T.motivos[chave]}
            </Opcao>
          ))}
        </Pergunta>
      )}

      {passo === 4 && (
        <Pergunta titulo={T.tituloObjetivos} subtitulo={T.subtituloObjetivos} refTitulo={titulo}>
          {OBJETIVOS_POR_PAIS[pais ?? "PT"].map((chave) => (
            <Opcao
              key={chave}
              tipo="checkbox"
              nome="objetivos"
              marcada={objetivos.includes(chave)}
              aoMudar={() => alternarObjetivo(chave)}
            >
              {T.objetivos[chave]}
            </Opcao>
          ))}
        </Pergunta>
      )}

      <p className="text-xs text-texto-suave">{passo === 1 ? TEXTOS_PAIS.privacidadePais : T.privacidade}</p>

      {/* No telemóvel a barra de ações fica presa ao fundo do ecrã (o botão principal está sempre à vista, mesmo
          com 7 opções) e o botão principal vem primeiro, à largura toda; Voltar e Saltar ficam por baixo, discretos.
          No computador: Voltar à esquerda, Saltar e o botão principal à direita. */}
      <div className="sticky bottom-0 z-10 -mx-5 -mb-5 rounded-b-xl border-t border-borda bg-cartao px-5 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:static sm:m-0 sm:rounded-none sm:border-0 sm:bg-transparent sm:p-0">
        {/* O erro fica dentro da barra: assim nunca fica escondido por baixo dela. */}
        {erro && (
          <p role="alert" className="mb-3 text-sm font-medium text-red-700 dark:text-red-400">
            {erro}
          </p>
        )}
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
          {passo === 1 && (
            <button type="button" onClick={continuarPais} className={`${BOTAO_PRINCIPAL} sm:order-3`}>
              {T.continuar}
            </button>
          )}
          {passo === 2 && (
            <button type="button" onClick={continuarBancos} className={`${BOTAO_PRINCIPAL} sm:order-3`}>
              {T.continuar}
            </button>
          )}
          {passo === 3 && (
            <button type="button" onClick={() => irPara(4)} className={`${BOTAO_PRINCIPAL} sm:order-3`}>
              {T.continuar}
            </button>
          )}
          {passo === 4 && (
            <button
              type="button"
              onClick={() => terminar(true)}
              disabled={aGuardar}
              aria-busy={aGuardar}
              className={`${BOTAO_PRINCIPAL} sm:order-3`}
            >
              {aGuardar ? T.aGuardar : T.comecar}
            </button>
          )}
          {passo > 1 && (
            <div className="flex items-center justify-between sm:contents">
              <button
                type="button"
                onClick={() => irPara(passo - 1)}
                disabled={aGuardar}
                className={`${BOTAO_TEXTO} -ml-3 sm:order-1 sm:mr-auto sm:ml-0`}
              >
                <span aria-hidden className="mr-1">
                  ←
                </span>
                {T.voltar}
              </button>
              {passo === 3 && (
                <button
                  type="button"
                  onClick={() => {
                    setMotivo(null);
                    irPara(4);
                  }}
                  className={`${BOTAO_TEXTO} -mr-3 sm:order-2 sm:mr-0`}
                >
                  {T.saltar}
                </button>
              )}
              {passo === 4 && (
                <button
                  type="button"
                  onClick={() => terminar(false)}
                  disabled={aGuardar}
                  className={`${BOTAO_TEXTO} -mr-3 sm:order-2 sm:mr-0`}
                >
                  {T.saltar}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </Moldura>
  );
}

// O cartão do questionário, com "Passo x de 4" e a barra de progresso.
function Moldura({ passo, progresso, children }: { passo: number; progresso: string; children: ReactNode }) {
  const texto = preencher(progresso, { atual: passo, total: TOTAL_PASSOS });
  const { TEXTOS_MENU } = useTextos(DICIONARIO_COMUNS);
  const sair = useSair();
  return (
    // O menu está escondido neste ecrã: o logo por cima do cartão mostra onde se está.
    // No computador o cartão fica ao centro do ecrã; no telemóvel começa no topo.
    <main className="flex flex-col items-center gap-6 px-4 pt-6 pb-4 sm:min-h-dvh sm:justify-center sm:p-8">
      <Logo altura={32} />
      <div className="w-full max-w-xl space-y-6 rounded-xl border border-borda bg-cartao p-5 sm:p-8">
        <div className="space-y-2">
          <p id="progresso-boas-vindas" className="text-xs font-semibold uppercase tracking-wide text-destaque-hover">
            {texto}
          </p>
          {/* A trilha usa a cor da borda (a do fundo quase não se vê sobre o cartão no tema claro). */}
          <div
            className="h-1.5 overflow-hidden rounded-full bg-borda"
            role="progressbar"
            aria-valuenow={passo}
            aria-valuemin={1}
            aria-valuemax={TOTAL_PASSOS}
            aria-labelledby="progresso-boas-vindas"
          >
            <div
              className="h-full rounded-full bg-destaque transition-[width] duration-300 motion-reduce:transition-none"
              style={{ width: `${(passo / TOTAL_PASSOS) * 100}%` }}
            />
          </div>
        </div>
        {children}
      </div>
      {/* O menu está escondido: a única saída do questionário é sair da conta (discreta, por baixo do cartão).
          Os links legais: no telemóvel já estão no fundo da página (layout da app); no computador ficam aqui. */}
      <div className="flex flex-col items-center gap-1">
        <button type="button" onClick={sair} className={BOTAO_TEXTO}>
          {TEXTOS_MENU.sair}
        </button>
        <RodapeLegal className="hidden md:flex" />
      </div>
    </main>
  );
}

// Uma pergunta: título (recebe o foco), subtítulo e as opções num fieldset.
function Pergunta({
  titulo,
  subtitulo,
  refTitulo,
  children,
}: {
  titulo: string;
  subtitulo: string;
  refTitulo: React.RefObject<HTMLHeadingElement | null>;
  children: ReactNode;
}) {
  return (
    <fieldset className="space-y-4">
      <legend className="sr-only">{titulo}</legend>
      <div className="space-y-1">
        <h1 ref={refTitulo} tabIndex={-1} className="text-2xl font-semibold text-balance text-texto focus:outline-none">
          {titulo}
        </h1>
        <p className="text-sm text-texto-suave">{subtitulo}</p>
      </div>
      <div className="space-y-2">{children}</div>
    </fieldset>
  );
}
