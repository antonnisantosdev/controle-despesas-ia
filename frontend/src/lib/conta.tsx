"use client";

import { usePathname } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { pedirEstadoPlano, type BoasVindasGuardadas, type EstadoPlano } from "./api";
import { CONTA_PADRAO, criarFormatos, FORMATOS_PADRAO, type Conta, type Formatos } from "./formatos";
import { useSessaoDemo } from "./useSessaoDemo";

// País, moeda e países dos bancos da conta (GET /plano), para os formatos de dinheiro e datas.
// Fora do ProvedorConta (páginas públicas) os hooks devolvem PT/EUR.
const ContextoConta = createContext<Conta>(CONTA_PADRAO);
const ContextoFormatos = createContext<Formatos>(FORMATOS_PADRAO);
// O estado do plano (o cartão do menu usa-o). Contexto à parte: muda a cada página (contador de pedidos)
// e assim não volta a desenhar os componentes que só querem a moeda.
const ContextoEstadoPlano = createContext<EstadoPlano | null>(null);
// Depois de gravar o questionário ou as definições: põe já o país, a moeda e os bancos novos (textos e formatos
// mudam logo) e tira o "questionário por fazer", sem esperar pelo próximo GET /plano.
type AplicarPerfil = (perfil: Pick<BoasVindasGuardadas, "pais" | "moeda" | "paises_bancos">) => void;
const ContextoAplicarPerfil = createContext<AplicarPerfil>(() => {});

function chaveDaConta(conta: Conta): string {
  return `${conta.pais}|${conta.moeda}|${conta.paisesBancos.join(",")}`;
}

// No layout da app. Pede o /plano a cada página nova (era o cartão do plano que o fazia, para o contador
// acompanhar os pedidos feitos): assim a conta não custa um pedido a mais. Na demo, só uma vez
// (o contador é partilhado e não aparece). Se o pedido falhar, a conta fica como estava.
export function ProvedorConta({ children }: { children: ReactNode }) {
  const pagina = usePathname();
  const demo = useSessaoDemo();
  const [estado, setEstado] = useState<EstadoPlano | null>(null);
  const [conta, setConta] = useState<Conta>(CONTA_PADRAO);
  const jaPediuNaDemo = useRef(false);
  // O questionário já foi gravado nesta sessão: um GET /plano que saia antes (ou chegue atrasado) não o volta a pedir.
  const respondido = useRef(false);

  useEffect(() => {
    if (demo && jaPediuNaDemo.current) return;
    if (!demo) jaPediuNaDemo.current = false;
    let cancelado = false;
    pedirEstadoPlano()
      .then((novo) => {
        if (cancelado) return;
        // Só marca na demo quando a resposta chegou: um pedido cancelado ou falhado volta a ser feito.
        jaPediuNaDemo.current = demo;
        setEstado(respondido.current ? { ...novo, boas_vindas_pendente: false } : novo);
        // Só troca a conta se o país, a moeda ou os bancos mudaram: quem formata dinheiro não volta a desenhar.
        const nova: Conta = { pais: novo.pais, moeda: novo.moeda, paisesBancos: novo.paises_bancos };
        setConta((atual) => (chaveDaConta(atual) === chaveDaConta(nova) ? atual : nova));
      })
      .catch(() => {
        // O cartão do plano simplesmente não aparece (a página trata da sessão).
        if (!cancelado) setEstado(null);
      });
    return () => {
      cancelado = true;
    };
  }, [pagina, demo]);

  const formatos = useMemo(() => criarFormatos(conta), [conta]);

  const aplicarPerfil = useCallback<AplicarPerfil>((perfil) => {
    respondido.current = true;
    const nova: Conta = { pais: perfil.pais, moeda: perfil.moeda, paisesBancos: perfil.paises_bancos };
    setConta((atual) => (chaveDaConta(atual) === chaveDaConta(nova) ? atual : nova));
    setEstado((atual) =>
      atual
        ? { ...atual, pais: perfil.pais, moeda: perfil.moeda, paises_bancos: perfil.paises_bancos, boas_vindas_pendente: false }
        : atual,
    );
  }, []);

  return (
    <ContextoAplicarPerfil.Provider value={aplicarPerfil}>
      <ContextoConta.Provider value={conta}>
        <ContextoFormatos.Provider value={formatos}>
          <ContextoEstadoPlano.Provider value={estado}>{children}</ContextoEstadoPlano.Provider>
        </ContextoFormatos.Provider>
      </ContextoConta.Provider>
    </ContextoAplicarPerfil.Provider>
  );
}

// aplicarPerfil(resposta do PUT /conta/boas-vindas): a app passa logo ao país e à moeda novos.
export function useAplicarPerfil(): AplicarPerfil {
  return useContext(ContextoAplicarPerfil);
}

// { pais, moeda, paisesBancos } da conta (PT/EUR/[PT] enquanto o /plano não chega ou fora da app).
export function useConta(): Conta {
  return useContext(ContextoConta);
}

// dinheiro(), data(), numero()... já com o país e a moeda da conta (ver lib/formatos.ts).
export function useFormatos(): Formatos {
  return useContext(ContextoFormatos);
}

// O último GET /plano do ProvedorConta (null enquanto não chega, se falhar ou fora da app).
export function useEstadoPlano(): EstadoPlano | null {
  return useContext(ContextoEstadoPlano);
}
