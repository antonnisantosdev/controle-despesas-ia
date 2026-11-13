"use client";

import { usePathname } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";

import { pedirEstadoPlano, SessaoExpirada, type BoasVindasGuardadas, type EstadoPlano } from "./api";
import { contaDoTexto, guardarConta, lerContaGuardada } from "./contaGuardada";
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
// Como correu o último GET /plano, e como pedi-lo outra vez (ex. o chat, depois de cada pergunta, para o aviso
// dos 80%). falhou: o pedido deu erro (sessaoExpirada: foi um 401); quem precisa trata do erro à sua maneira.
type PedidoPlano = { falhou: boolean; sessaoExpirada: boolean; atualizar: () => void };
const ContextoPedidoPlano = createContext<PedidoPlano>({ falhou: false, sessaoExpirada: false, atualizar: () => {} });

// O localStorage não muda sozinho durante a visita: não há nada a que subscrever.
const semSubscricao = () => () => {};

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
  // A conta que o /plano deu (null enquanto não chega). Até lá vale a guardada neste browser (a da última visita),
  // para a app abrir logo na língua e na moeda certas; no servidor e sem nada guardado, PT/EUR.
  const [contaDoPlano, setContaDoPlano] = useState<Conta | null>(null);
  const textoGuardado = useSyncExternalStore(semSubscricao, lerContaGuardada, () => null);
  const contaGuardada = useMemo(() => contaDoTexto(textoGuardado), [textoGuardado]);
  const conta = contaDoPlano ?? contaGuardada ?? CONTA_PADRAO;
  const jaPediuNaDemo = useRef(false);
  // O questionário já foi gravado nesta sessão: um GET /plano que saia antes (ou chegue atrasado) não o volta a pedir.
  const respondido = useRef(false);
  const [versao, setVersao] = useState(0); // sobe com atualizar(): volta a pedir o /plano
  // A falha guarda a página e o pedido em que aconteceu: numa página nova (ou depois de atualizar) só conta
  // quando o pedido novo também falhar, e o erro antigo não aparece enquanto ele não chega.
  const [falha, setFalha] = useState<{ chave: string; sessaoExpirada: boolean } | null>(null);
  const chavePedido = `${pagina}|${versao}`;

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
        setContaDoPlano((atual) => (atual && chaveDaConta(atual) === chaveDaConta(nova) ? atual : nova));
        if (!demo) guardarConta(nova); // a demo é partilhada: não fica como "a conta deste browser"
        setFalha(null);
      })
      .catch((e) => {
        // O cartão do plano simplesmente não aparece (a página trata da sessão).
        if (cancelado) return;
        setEstado(null);
        setFalha({ chave: `${pagina}|${versao}`, sessaoExpirada: e instanceof SessaoExpirada });
      });
    return () => {
      cancelado = true;
    };
  }, [pagina, demo, versao]);

  const atualizar = useCallback(() => setVersao((v) => v + 1), []);
  const falhou = falha?.chave === chavePedido;
  const sessaoExpirada = falhou && falha.sessaoExpirada;
  const pedidoPlano = useMemo(() => ({ falhou, sessaoExpirada, atualizar }), [falhou, sessaoExpirada, atualizar]);

  const formatos = useMemo(() => criarFormatos(conta), [conta]);

  const aplicarPerfil = useCallback<AplicarPerfil>((perfil) => {
    respondido.current = true;
    const nova: Conta = { pais: perfil.pais, moeda: perfil.moeda, paisesBancos: perfil.paises_bancos };
    setContaDoPlano((atual) => (atual && chaveDaConta(atual) === chaveDaConta(nova) ? atual : nova));
    if (!demo) guardarConta(nova); // como no GET /plano: a demo não fica como "a conta deste browser"
    setEstado((atual) =>
      atual
        ? { ...atual, pais: perfil.pais, moeda: perfil.moeda, paises_bancos: perfil.paises_bancos, boas_vindas_pendente: false }
        : atual,
    );
  }, [demo]);

  return (
    <ContextoAplicarPerfil.Provider value={aplicarPerfil}>
      <ContextoConta.Provider value={conta}>
        <ContextoFormatos.Provider value={formatos}>
          <ContextoEstadoPlano.Provider value={estado}>
            <ContextoPedidoPlano.Provider value={pedidoPlano}>{children}</ContextoPedidoPlano.Provider>
          </ContextoEstadoPlano.Provider>
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

// { falhou, sessaoExpirada, atualizar } do GET /plano do ProvedorConta (fora da app: nada falhou, atualizar não faz nada).
export function usePedidoPlano(): PedidoPlano {
  return useContext(ContextoPedidoPlano);
}
