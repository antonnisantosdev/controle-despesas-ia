"use client";

import { useState } from "react";

import { TEXTOS_PALAVRA_PASSE } from "@/lib/textosComuns";

// Campo de palavra-passe com um botão (olho) para mostrar ou esconder o que se escreveu.
// Fica dentro do <label> da página: o input é o primeiro controlo, por isso é ele que o rótulo nomeia.
type Props = {
  value: string;
  onChange: (valor: string) => void;
  autoComplete?: string;
  className?: string;
};

export default function CampoPalavraPasse({ value, onChange, autoComplete = "current-password", className = "" }: Props) {
  const [visivel, setVisivel] = useState(false);

  return (
    <div className="relative">
      <input
        type={visivel ? "text" : "password"}
        required
        autoComplete={autoComplete}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        // pr-12: espaço para o botão do olho não tapar o texto.
        className={`${className} pr-12`}
      />
      <button
        type="button"
        onClick={() => setVisivel((v) => !v)}
        aria-label={visivel ? TEXTOS_PALAVRA_PASSE.esconder : TEXTOS_PALAVRA_PASSE.mostrar}
        aria-pressed={visivel}
        className="absolute inset-y-0 right-0 mt-1 flex w-11 items-center justify-center rounded-r-md text-texto-suave hover:text-texto focus-visible:outline focus-visible:outline-2 focus-visible:outline-destaque"
      >
        {visivel ? (
          <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3l18 18" />
            <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
            <path d="M9.9 4.2A10.4 10.4 0 0 1 12 4c6 0 10 8 10 8a17.6 17.6 0 0 1-3.2 4.1M6.6 6.6C3.8 8.4 2 12 2 12s4 8 10 8a9.7 9.7 0 0 0 5.4-1.6" />
          </svg>
        ) : (
          <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2 12s4-8 10-8 10 8 10 8-4 8-10 8S2 12 2 12z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )}
      </button>
    </div>
  );
}
