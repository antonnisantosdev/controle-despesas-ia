import type { ReactNode } from "react";

// Foco visível igual ao do resto da app (contorno na cor de destaque).
const FOCO = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque";

// Botões do questionário de boas-vindas (estilos partilhados com a página Definições).
// Alvo de toque de 48 px; no telemóvel ocupam a largura toda, no computador só o necessário.
export const BOTAO_PRINCIPAL = `flex min-h-12 w-full items-center justify-center rounded-md bg-destaque px-6 text-base font-semibold text-white transition-colors hover:bg-destaque-hover disabled:cursor-not-allowed disabled:opacity-50 dark:text-fundo ${FOCO} sm:w-auto`;
export const BOTAO_SECUNDARIO = `flex min-h-12 w-full items-center justify-center rounded-md border border-borda bg-cartao px-6 text-base font-medium text-texto transition-colors hover:bg-fundo disabled:cursor-not-allowed disabled:opacity-50 ${FOCO} sm:w-auto`;
// Ação discreta (Voltar, Saltar): só texto, mas com 44 px de altura para o dedo.
export const BOTAO_TEXTO = `inline-flex min-h-11 items-center justify-center rounded-md px-3 text-base font-medium text-texto-suave transition-colors hover:bg-fundo hover:text-texto disabled:cursor-not-allowed disabled:opacity-50 ${FOCO}`;

// Uma opção grande (fácil de tocar no telemóvel): o rótulo inteiro é clicável e o radio/caixa continua visível.
// A opção escolhida fica com a borda reforçada e o fundo da cor de destaque (nos dois temas), sem mudar de tamanho.
// O input é nativo (radio/checkbox): o papel, o estado e o grupo (fieldset) chegam aos leitores de ecrã sem aria extra.
export default function OpcaoGrande({
  tipo,
  nome,
  marcada,
  aoMudar,
  desligada = false,
  children,
}: {
  tipo: "radio" | "checkbox";
  nome: string;
  marcada: boolean;
  aoMudar: () => void;
  desligada?: boolean;
  children: ReactNode;
}) {
  return (
    <label
      className={`flex min-h-12 cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 text-base leading-snug text-texto transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-destaque has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50 ${
        marcada
          ? "border-destaque bg-destaque/10 font-medium ring-1 ring-destaque"
          : "border-borda bg-cartao hover:border-texto-suave hover:bg-fundo"
      }`}
    >
      <input
        type={tipo}
        name={nome}
        checked={marcada}
        onChange={aoMudar}
        disabled={desligada}
        className="h-5 w-5 shrink-0 cursor-[inherit] accent-destaque focus:outline-none"
      />
      <span className="min-w-0 flex-1 break-words">{children}</span>
    </label>
  );
}
