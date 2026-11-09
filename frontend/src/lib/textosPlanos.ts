// Textos dos planos, preços e limite diário (aprovados pelo copywriter). Usar sempre "pedidos à IA".
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).

export const TEXTOS_PRECOS = {
  titulo: "Escolhe o teu plano",
  subtitulo:
    "Todos os planos têm as mesmas funcionalidades. Só muda quantos pedidos podes fazer à IA por dia. Começas no Free, sem cartão.",
  precoPorDefinir: "Preço em breve",
  precoFree: "Grátis",
  pedidosPorDia: "{limite} pedidos à IA por dia",
  funcionalidadesTitulo: "Incluído em todos os planos",
  funcionalidades: [
    "Importar extratos em CSV e PDF, com categorias feitas pela IA",
    "Dashboard com gastos por categoria e evolução mensal",
    "Chat que responde com os teus números reais",
    "Resumo do mês com alertas",
    "Planeamento: orçamento por categoria, com sugestão da IA",
    "Minhas compras: a IA lê o talão a partir de uma fotografia",
    "Minha reserva: objetivos de poupança e simulador de juros compostos",
    "Instala no telemóvel como uma app",
  ],
  notaPagamento:
    'Os planos pagos são pagos por MB Way. Carregas em "Pedir acesso", combinamos o pagamento e ativamos o plano assim que o confirmarmos.',
  faqTitulo: "Perguntas frequentes",
  faq: [
    {
      pergunta: "Como pago?",
      resposta:
        'Por MB Way. Carrega em "Pedir acesso" no plano que queres e envia-nos a mensagem que aparece. Respondemos com os dados para o pagamento.',
    },
    {
      pergunta: "Quando fica ativo?",
      resposta:
        'Ativamos o plano assim que confirmarmos o pagamento. Até lá, continuas a usar o Free. Quando o plano estiver ativo, vês a data de fim em "O meu plano".',
    },
    {
      pergunta: "O que conta como pedido à IA?",
      resposta:
        "Cada vez que a IA trabalha para ti: uma pergunta no chat, uma importação de extrato, a leitura de um talão, uma sugestão de orçamento, o resumo do mês, o plano de poupança de um objetivo ou categorizar uma movimentação nova. Ver o dashboard, as listas e o simulador não conta. O contador volta a zero à meia-noite.",
    },
    {
      pergunta: "Posso voltar ao Free?",
      resposta:
        "Sim, pede-nos e passamos a tua conta para o Free. Atenção: se um plano pago chegar ao fim sem renovares, a conta fica bloqueada até renovares ou pedires para passar ao Free. Os teus dados não se perdem.",
    },
    {
      pergunta: "E os meus dados?",
      resposta:
        "Cada conta só vê os seus próprios dados. Para categorizar, ler talões e responder no chat, os dados necessários são enviados ao serviço de IA que usamos. A Control Prices não é um banco nem dá conselhos de investimento: o simulador é só uma simulação.",
    },
  ],
};

// Nome, frase, pontos e botão de cada cartão. O primeiro ponto é sempre o limite (TEXTOS_PRECOS.pedidosPorDia),
// com o número vindo de GET /planos; aqui ficam só os outros.
export const TEXTOS_CARTOES = {
  free: {
    nome: "Free",
    frase: "Para experimentar e organizar o dia a dia.",
    pontos: ["Todas as funcionalidades da app", "Sem data de fim", "Ativo logo que confirmes o email"],
    botao: "Criar conta grátis",
  },
  essencial: {
    nome: "Essencial",
    frase: "Para quem usa a app todas as semanas.",
    pontos: ["Todas as funcionalidades da app", "Pagamento por MB Way"],
    botao: "Pedir acesso",
  },
  completo: {
    nome: "Completo",
    frase: "Para quem importa extratos, lê talões e conversa com a IA todos os dias.",
    pontos: ["Todas as funcionalidades da app", "Pagamento por MB Way"],
    botao: "Pedir acesso",
  },
};

export const TEXTOS_MEU_PLANO = {
  titulo: "O meu plano",
  planoAtual: "Plano atual",
  nomeSemPlano: "Sem plano",
  pedidosHoje: "Pedidos à IA hoje: {usadas} de {limite}",
  reinicia: "O contador volta a zero à meia-noite.",
  ativoAte: "Ativo até {data}",
  semDataFim: "Sem data de fim",
  avisoRenovar: "O teu plano termina a {data}. Para não perderes o acesso, pede a renovação antes dessa data.",
  botaoUpgrade: "Mudar de plano",
  botaoRenovar: "Pedir renovação",
  completo: "Estás no plano Completo, o que tem mais pedidos por dia. Se precisares de mais, fala connosco.",
  todasFuncionalidades: "O teu plano inclui todas as funcionalidades da app.",
};

// Mensagens pré-preenchidas do WhatsApp e do email. Sem sessão, a frase do email da conta sai (FRASE_EMAIL).
export const TEXTOS_MENSAGEM = {
  mensagem:
    "Olá! Quero o plano {plano} da Control Prices. O email da minha conta é {email}. Como faço o pagamento por MB Way?",
  mensagemRenovar: "Olá! Quero renovar o plano {plano} da Control Prices. O email da minha conta é {email}.",
  emailAssunto: "Pedido de plano {plano} – Control Prices",
  emailAssuntoRenovar: "Renovação do plano {plano} – Control Prices",
};
export const FRASE_EMAIL = " O email da minha conta é {email}.";

export const TEXTOS_EXPIRADA = {
  titulo: "O teu plano terminou",
  texto1: "Os teus dados continuam guardados. Assim que renovares, voltas a ver tudo como deixaste.",
  texto2: "Para renovar, escolhe um plano e pede acesso. Ativamos assim que confirmarmos o pagamento.",
  botaoPlanos: "Ver planos",
  botaoSair: "Sair da conta",
};

export const TEXTOS_LIMITE = {
  titulo: "Chegaste ao limite de hoje",
  texto: "Já usaste os {limite} pedidos à IA do teu plano. O contador volta a zero à meia-noite.",
  link: "Ver planos",
};
