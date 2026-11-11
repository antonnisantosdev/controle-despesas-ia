// Textos partilhados por várias páginas: nome da app, menu, cartão do plano e componentes comuns.
// Passo 5 da Fase 1 Brasil: os textos saíram dos componentes .tsx sem mudar uma letra.
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).

// Nome e descrição da app (metadata do layout.tsx e manifesto da PWA).
export const TEXTOS_APP = {
  nome: "Control Prices",
  descricao: "Controlo financeiro pessoal com IA",
} as const;

// Faixa no fundo do ecrã enquanto a API acorda (AvisoServidor).
export const TEXTOS_SERVIDOR = {
  aAcordar: "A acordar o servidor, pode demorar até um minuto...",
} as const;

// Botão "Pedir acesso" / "Pedir renovação" (BotaoPedirAcesso).
export const TEXTOS_PEDIR_ACESSO = {
  semContacto: "Contacto ainda não disponível.",
  porEmail: "ou por email",
} as const;

// Botão do olho no campo da palavra-passe (CampoPalavraPasse).
export const TEXTOS_PALAVRA_PASSE = {
  esconder: "Esconder a palavra-passe",
  mostrar: "Mostrar a palavra-passe",
} as const;

// Menu lateral da app (MenuLateral). O "Resumo anual" está em TEXTOS_RELATORIO.menu.
export const TEXTOS_MENU = {
  visaoGeral: "Visão geral",
  movimentacoes: "Movimentações",
  planeamento: "Planeamento",
  compras: "Minhas compras",
  reserva: "Minha reserva",
  mudarTema: "Mudar tema",
  sair: "Sair da conta",
} as const;

// Cartão do plano no fundo do menu (CartaoPlano). Os textos do contador estão em TEXTOS_MEU_PLANO.
export const TEXTOS_CARTAO_PLANO = {
  plano: "Plano {nome}",
  barraMes: "Pedidos à IA usados este mês",
  barraHoje: "Pedidos à IA usados hoje",
} as const;

// Caixa dos alertas de orçamento (AlertasOrcamento). As frases estão em TEXTOS_ALERTA_ORCAMENTO.
export const TEXTOS_ALERTAS_ORCAMENTO = {
  rotulo: "Alertas de orçamento",
} as const;

// Erros e estados repetidos em várias páginas.
export const TEXTOS_GERAIS = {
  semLigacao: "Não foi possível ligar ao servidor. Tenta outra vez daqui a um minuto.",
  sessaoExpirou: "A tua sessão expirou. Faz login de novo.",
  email: "Email",
  palavraPasse: "Palavra-passe",
  verPlanos: "Ver planos",
} as const;
