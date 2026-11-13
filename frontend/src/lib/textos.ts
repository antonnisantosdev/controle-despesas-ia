"use client";

// Dicionário de textos por país (Fase 1 Brasil, passo 6), sem biblioteca nova.
// Cada ficheiro textos*.ts usado na app exporta DICIONARIO_X = { PT, BR }, com o mesmo tipo (Traducao<typeof PT>):
// se faltar uma chave no BR, o `npx tsc --noEmit` falha.
// Nos componentes: const { TEXTOS_X } = useTextos(DICIONARIO_X). Escolhe pelo país da conta (useConta);
// fora da app (páginas públicas, sem ProvedorConta) é sempre PT.
// Funções puras (fora de componentes) recebem os textos por argumento, como os formatos.

import { useConta } from "./conta";
import type { Pais } from "./formatos";
import { CATEGORIAS_POR_PAIS, METODOS_POR_PAIS, ROTULOS_CATEGORIAS, ROTULOS_METODOS } from "./opcoes";

// O tipo do PT com os textos "abertos" (string em vez do texto exato), para o BR poder ter outras frases
// mas obrigatoriamente as mesmas chaves (e as mesmas listas e números).
export type Traducao<T> = T extends string
  ? string
  : T extends number | boolean
    ? T
    : T extends readonly (infer U)[]
      ? readonly Traducao<U>[]
      : { readonly [K in keyof T]: Traducao<T[K]> };

export type Dicionario<T> = Record<Pais, T>;

// Os textos do país da conta.
export function useTextos<T>(dicionario: Dicionario<T>): T {
  const { pais } = useConta();
  return dicionario[pais] ?? dicionario.PT;
}

// Categorias e métodos de pagamento do país da conta. As chaves (o que vai para a base de dados e para a IA)
// são iguais em todos os países; só muda o rótulo mostrado e quais aparecem nas listas de escolha.
export type Opcoes = {
  categorias: readonly string[]; // para os <select>
  rotuloCategoria: (chave: string) => string; // chave desconhecida (ex. "sem categoria"): mostra a chave
  // O mesmo rótulo com maiúscula só na 1.ª letra ("Telefone e internet"), para títulos e listas.
  // Substitui o CSS capitalize, que punha maiúscula em todas as palavras ("Telefone E Internet").
  nomeCategoria: (chave: string) => string;
  metodos: readonly string[]; // códigos para os <select>
  rotuloMetodo: (codigo: string) => string; // código desconhecido: mostra o código
};

export function opcoesDe(pais: Pais): Opcoes {
  const rotulosCategorias: Record<string, string> = ROTULOS_CATEGORIAS[pais];
  const rotulosMetodos: Record<string, string> = ROTULOS_METODOS[pais];
  // Object.hasOwn: "constructor" ou "__proto__" não apanham propriedades herdadas.
  const rotuloCategoria = (chave: string) => (Object.hasOwn(rotulosCategorias, chave) ? rotulosCategorias[chave] : chave);
  return {
    categorias: CATEGORIAS_POR_PAIS[pais],
    rotuloCategoria,
    nomeCategoria: (chave) => {
      const rotulo = rotuloCategoria(chave);
      return rotulo.charAt(0).toLocaleUpperCase(pais === "BR" ? "pt-BR" : "pt-PT") + rotulo.slice(1);
    },
    metodos: METODOS_POR_PAIS[pais],
    rotuloMetodo: (codigo) => (Object.hasOwn(rotulosMetodos, codigo) ? rotulosMetodos[codigo] : codigo),
  };
}

// A lista de escolha com o valor atual, se não estiver lá (ex. uma movimentação antiga com uma categoria ou
// um método escondido neste país): assim o <select> mostra o valor certo em vez do primeiro da lista.
export function comValorAtual(lista: readonly string[], atual: string | null | undefined): readonly string[] {
  return atual && !lista.includes(atual) ? [...lista, atual] : lista;
}

const OPCOES: Dicionario<Opcoes> = { PT: opcoesDe("PT"), BR: opcoesDe("BR") };

export function useOpcoes(): Opcoes {
  return useTextos(OPCOES);
}
