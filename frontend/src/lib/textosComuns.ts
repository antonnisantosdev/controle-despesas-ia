// Textos partilhados por várias páginas: nome da app, menu, cartão do plano e componentes comuns.
// Passo 5 da Fase 1 Brasil: os textos saíram dos componentes .tsx sem mudar uma letra.
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).
// Fase 1 Brasil, passo 6: dicionário { PT, BR }. Nos componentes: const { TEXTOS_... } = useTextos(DICIONARIO_COMUNS)
// (lib/textos.ts), que escolhe pelo país da conta. Fora da app (páginas públicas) é sempre o PT.

import type { Dicionario, Traducao } from "./textos";

// Fora do dicionário (sempre PT): o nome da app vai para a metadata e o manifesto, iguais para todos;
// a palavra-passe só aparece no login e no registo (páginas públicas, em PT-PT).

// Nome e descrição da app (metadata do layout.tsx e manifesto da PWA).
export const TEXTOS_APP = {
  nome: "Control Prices",
  descricao: "Controlo financeiro pessoal com IA",
} as const;

// Botão do olho no campo da palavra-passe (CampoPalavraPasse).
export const TEXTOS_PALAVRA_PASSE = {
  esconder: "Esconder a palavra-passe",
  mostrar: "Mostrar a palavra-passe",
} as const;

const PT = {
  // Faixa no fundo do ecrã enquanto a API acorda (AvisoServidor).
  TEXTOS_SERVIDOR: {
    aAcordar: "A acordar o servidor, pode demorar até um minuto...",
  } as const,

  // Botão "Pedir acesso" / "Pedir renovação" (BotaoPedirAcesso).
  TEXTOS_PEDIR_ACESSO: {
    semContacto: "Contacto ainda não disponível.",
    porEmail: "ou por email",
  } as const,

  // Menu lateral da app (MenuLateral). O "Resumo anual" está em TEXTOS_RELATORIO.menu.
  TEXTOS_MENU: {
    visaoGeral: "Visão geral",
    movimentacoes: "Movimentações",
    planeamento: "Planeamento",
    compras: "Minhas compras",
    reserva: "Minha reserva",
    mudarTema: "Mudar tema",
    sair: "Sair da conta",
  } as const,

  // Cartão do plano no fundo do menu (CartaoPlano). Os textos do contador estão em TEXTOS_MEU_PLANO.
  TEXTOS_CARTAO_PLANO: {
    plano: "Plano {nome}",
    barraMes: "Pedidos à IA usados este mês",
    barraHoje: "Pedidos à IA usados hoje",
  } as const,

  // Caixa dos alertas de orçamento (AlertasOrcamento). As frases estão em TEXTOS_ALERTA_ORCAMENTO.
  TEXTOS_ALERTAS_ORCAMENTO: {
    rotulo: "Alertas de orçamento",
  } as const,

  // Erros e estados repetidos em várias páginas.
  TEXTOS_GERAIS: {
    semLigacao: "Não foi possível ligar ao servidor. Tenta outra vez daqui a um minuto.",
    sessaoExpirou: "A tua sessão expirou. Faz login de novo.",
    email: "Email",
    palavraPasse: "Palavra-passe",
    verPlanos: "Ver planos",
  } as const,
};

export type TextosComuns = Traducao<typeof PT>;

// ===== BR (PT-BR) =====
// Textos PT-BR do copywriter (passo 7). Mesmas chaves e mesmos {placeholders} do PT; o tipo obriga a ter todas
// as chaves (o `npx tsc --noEmit` falha se faltar alguma).
const BR: TextosComuns = {
  // Faixa no fundo do ecrã enquanto a API acorda (AvisoServidor).
  TEXTOS_SERVIDOR: {
    aAcordar: "Acordando o servidor, pode levar até um minuto...",
  },

  // Botão "Pedir acesso" / "Pedir renovação" (BotaoPedirAcesso).
  TEXTOS_PEDIR_ACESSO: {
    semContacto: "Contato ainda não disponível.",
    porEmail: "ou por e-mail",
  },

  // Menu lateral da app (MenuLateral). O "Resumo anual" está em TEXTOS_RELATORIO.menu.
  TEXTOS_MENU: {
    visaoGeral: "Visão geral",
    movimentacoes: "Movimentações",
    planeamento: "Planejamento",
    compras: "Minhas compras",
    reserva: "Minha reserva",
    mudarTema: "Mudar tema",
    sair: "Sair da conta",
  },

  // Cartão do plano no fundo do menu (CartaoPlano). Os textos do contador estão em TEXTOS_MEU_PLANO.
  TEXTOS_CARTAO_PLANO: {
    plano: "Plano {nome}",
    barraMes: "Pedidos à IA usados este mês",
    barraHoje: "Pedidos à IA usados hoje",
  },

  // Caixa dos alertas de orçamento (AlertasOrcamento). As frases estão em TEXTOS_ALERTA_ORCAMENTO.
  TEXTOS_ALERTAS_ORCAMENTO: {
    rotulo: "Alertas de orçamento",
  },

  // Erros e estados repetidos em várias páginas.
  TEXTOS_GERAIS: {
    semLigacao: "Não foi possível conectar ao servidor. Tente de novo daqui a um minuto.",
    sessaoExpirou: "Sua sessão expirou. Faça login de novo.",
    email: "E-mail",
    palavraPasse: "Senha",
    verPlanos: "Ver planos",
  },
};

export const DICIONARIO_COMUNS: Dicionario<TextosComuns> = { PT, BR };
