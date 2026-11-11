// Textos da página /brasil (lista de espera), em PORTUGUÊS DO BRASIL.
// Revistos pelo copywriter (2026-11-11). Os marcados com "TEXTO NOVO" vieram depois e ainda não foram revistos.
// Se o texto do consentimento mudar, mudar também lista_espera.VERSAO_CONSENTIMENTO no backend.
// O texto do consentimento foi aprovado pelo CEO (pedido com a funcionalidade) e não muda sem ele.
// Regra do CEO: não dizer de que país é a app; só o que ela faz e que a versão para o Brasil está em preparação.

export const METADATA_BRASIL = {
  title: "Control Prices no Brasil | Lista de espera",
  description:
    "Controle financeiro pessoal com IA: importa extratos, organiza seus gastos por categoria e responde a perguntas sobre eles. A versão para o Brasil está em preparação.", // TEXTO NOVO
};

export const TEXTOS_BRASIL = {
  titulo: "Control Prices no Brasil",
  // 2-3 linhas: o que a app faz e que a versão para o Brasil está em preparação. Sem datas nem funções prometidas.
  explicacao: [
    "A Control Prices é um app de controle financeiro pessoal com IA: importa seus extratos, organiza os gastos por categoria e responde a perguntas sobre eles.", // TEXTO NOVO
    "A versão para o Brasil está em preparação.", // TEXTO NOVO
    "Deixe seu email e avisamos você quando ela estiver disponível.",
  ],
  rotuloPais: "De que país você é?", // TEXTO NOVO
  rotuloCartoes: "De quais países são os cartões e contas que você vai usar?", // TEXTO NOVO
  dicaCartoes: "Marque um ou mais.", // TEXTO NOVO
  paisBrasil: "Brasil",
  paisPortugal: "Portugal", // TEXTO NOVO
  paisOutro: "Outro país",
  cartoesOutro: "Outro", // TEXTO NOVO
  rotuloEmail: "Seu email",
  // Caixa NÃO pré-marcada (LGPD). Texto aprovado pelo CEO.
  consentimento:
    "Aceito receber um email quando a Control Prices estiver disponível no Brasil. Posso pedir para sair a qualquer momento.",
  privacidadeAntes: "Saiba como tratamos seus dados na ",
  privacidadeLink: "Política de Privacidade",
  privacidadeDepois: ".",
  botao: "Quero receber o aviso",
  aEnviar: "Enviando...",
  sucessoTitulo: "Pronto!",
  sucesso: "Avisaremos você por email quando a Control Prices estiver disponível no Brasil.",
  // Erros: a página mostra estes, conforme o estado da resposta da API.
  erroCartoes: "Marque pelo menos um país dos cartões e contas.", // TEXTO NOVO
  erroConsentimento: "Para entrar na lista, marque a caixa de consentimento.",
  erroDados: "Confira se o email está correto e se você marcou a caixa de consentimento.",
  erroMuitosPedidos: "Muitas tentativas a partir desta rede. Tente novamente mais tarde.",
  erroServidor: "Não foi possível salvar seu email agora. Tente novamente em alguns minutos.",
};
