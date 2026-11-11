"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { API_URL, fetchComTentativas } from "@/lib/api";
import { lerOrigem } from "@/lib/origem";
import { TEXTOS_BRASIL } from "@/lib/textosBrasil";

type Pais = "BR" | "PT" | "outro";

// As opções das caixas dos cartões e contas, pela ordem em que aparecem (a API aceita 1 a 3, sem repetidos).
const OPCOES_CARTOES: { valor: Pais; texto: string }[] = [
  { valor: "BR", texto: TEXTOS_BRASIL.paisBrasil },
  { valor: "PT", texto: TEXTOS_BRASIL.paisPortugal },
  { valor: "outro", texto: TEXTOS_BRASIL.cartoesOutro },
];

const ESTILO_CAMPO = "mt-1 min-h-11 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-texto";
const ESTILO_CAIXA = "mt-0.5 h-5 w-5 shrink-0 accent-destaque";
const ESTILO_LINK =
  "font-medium text-destaque-hover underline hover:no-underline focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque";

// O texto do erro para cada resposta da API (a página usa os seus textos em português do Brasil).
function erroDaResposta(estado: number): string {
  if (estado === 422) return TEXTOS_BRASIL.erroDados;
  if (estado === 429) return TEXTOS_BRASIL.erroMuitosPedidos;
  return TEXTOS_BRASIL.erroServidor;
}

// Verifica o formulário antes de o enviar: devolve a mensagem de erro, ou "" se estiver tudo bem.
// As regras a sério estão na API (InscricaoListaEspera); aqui é só para ajudar.
function erroDoFormulario(cartoes: Pais[], consentimento: boolean): string {
  if (cartoes.length === 0) return TEXTOS_BRASIL.erroCartoes;
  if (!consentimento) return TEXTOS_BRASIL.erroConsentimento;
  return "";
}

// Formulário da lista de espera: país onde vive, países dos cartões e contas, email e consentimento
// (caixa NÃO pré-marcada, LGPD). POST /lista-espera responde igual esteja ou não o email já inscrito.
export default function FormularioBrasil() {
  const [pais, setPais] = useState<Pais>("BR");
  const [cartoes, setCartoes] = useState<Pais[]>([]);
  const [email, setEmail] = useState("");
  const [consentimento, setConsentimento] = useState(false);
  const [erro, setErro] = useState("");
  const [aEnviar, setAEnviar] = useState(false);
  const [inscrito, setInscrito] = useState(false);

  // Acorda a API enquanto a pessoa preenche (como no login e no registo).
  useEffect(() => {
    fetch(`${API_URL}/`).catch(() => {});
  }, []);

  // Marca ou desmarca um país dos cartões, mantendo a ordem das opções.
  function mudarCartao(valor: Pais, marcado: boolean) {
    setCartoes((atuais) => OPCOES_CARTOES.map((opcao) => opcao.valor).filter((v) => (v === valor ? marcado : atuais.includes(v))));
  }

  async function inscrever(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const problema = erroDoFormulario(cartoes, consentimento);
    setErro(problema);
    if (problema) return;

    setAEnviar(true);
    try {
      const resposta = await fetchComTentativas(`${API_URL}/lista-espera`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, pais, paises_cartoes: cartoes, consentimento, origem: lerOrigem() }),
      });
      if (resposta.ok) setInscrito(true);
      else setErro(erroDaResposta(resposta.status));
    } catch {
      setErro(TEXTOS_BRASIL.erroServidor);
    } finally {
      setAEnviar(false);
    }
  }

  if (inscrito) {
    return (
      <div role="status" className="space-y-2 text-center">
        <p className="font-medium text-texto">{TEXTOS_BRASIL.sucessoTitulo}</p>
        <p className="text-sm text-texto-suave">{TEXTOS_BRASIL.sucesso}</p>
      </div>
    );
  }

  return (
    <form onSubmit={inscrever} className="space-y-4">
      <label className="block">
        <span className="text-sm text-texto-suave">{TEXTOS_BRASIL.rotuloPais}</span>
        <select value={pais} onChange={(e) => setPais(e.target.value as Pais)} className={ESTILO_CAMPO}>
          <option value="BR">{TEXTOS_BRASIL.paisBrasil}</option>
          <option value="PT">{TEXTOS_BRASIL.paisPortugal}</option>
          <option value="outro">{TEXTOS_BRASIL.paisOutro}</option>
        </select>
      </label>

      <fieldset className="space-y-2">
        <legend className="text-sm text-texto-suave">{TEXTOS_BRASIL.rotuloCartoes}</legend>
        <p className="text-xs text-texto-suave">{TEXTOS_BRASIL.dicaCartoes}</p>
        <div className="flex flex-wrap gap-x-5 gap-y-1">
          {OPCOES_CARTOES.map((opcao) => (
            <label key={opcao.valor} className="flex min-h-11 items-center gap-2 text-sm text-texto">
              <input
                type="checkbox"
                checked={cartoes.includes(opcao.valor)}
                onChange={(e) => mudarCartao(opcao.valor, e.target.checked)}
                className={ESTILO_CAIXA}
              />
              {opcao.texto}
            </label>
          ))}
        </div>
      </fieldset>

      <label className="block">
        <span className="text-sm text-texto-suave">{TEXTOS_BRASIL.rotuloEmail}</span>
        <input
          type="email"
          required
          maxLength={254}
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={ESTILO_CAMPO}
        />
      </label>

      <label className="flex items-start gap-3 text-sm text-texto">
        <input
          type="checkbox"
          checked={consentimento}
          onChange={(e) => setConsentimento(e.target.checked)}
          className={ESTILO_CAIXA}
        />
        <span>{TEXTOS_BRASIL.consentimento}</span>
      </label>

      <p className="text-xs text-texto-suave">
        {TEXTOS_BRASIL.privacidadeAntes}
        <Link href="/privacidade" className={ESTILO_LINK}>
          {TEXTOS_BRASIL.privacidadeLink}
        </Link>
        {TEXTOS_BRASIL.privacidadeDepois}
      </p>

      {erro && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {erro}
        </p>
      )}

      <button
        type="submit"
        disabled={aEnviar}
        className="flex min-h-11 w-full items-center justify-center rounded-md bg-destaque px-4 text-sm font-semibold text-white transition-colors hover:bg-destaque-hover disabled:opacity-50 dark:text-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
      >
        {aEnviar ? TEXTOS_BRASIL.aEnviar : TEXTOS_BRASIL.botao}
      </button>
    </form>
  );
}
