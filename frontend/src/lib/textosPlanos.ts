// Textos dos planos, preços e limites (aprovados pelo copywriter). Usar sempre "pedidos à IA".
// Os marcados com "TEXTO NOVO" ainda não foram revistos pelo copywriter.
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).

export const TEXTOS_PRECOS = {
  titulo: "Escolhe o teu plano",
  // TEXTO NOVO
  subtitulo:
    "Começas no Free, sem cartão. Os planos pagos dão-te mais pedidos à IA, importação de extratos em PDF e leitura de talões por fotografia.",
  precoPorDefinir: "Preço em breve", // só aparece se um plano pago ficar sem preço em PRECOS (planos.ts)
  precoFree: "Grátis",
  porMes: "/mês",
  precoAnual: "ou {anual}/ano (2 meses grátis)",
  notaLancamento: "Preço de lançamento.",
  pedidosPorDia: "{limite} pedidos à IA por dia",
  pedidosPorMes: "{limite} pedidos à IA por mês", // TEXTO NOVO
  // Nos cartões pagos, no lugar de "Importar extratos em PDF". O número vem de GET /planos (limite_pdf).
  pdfPorMes: "Até {limitePdf} extratos PDF por mês",
  funcionalidadesTitulo: "Incluído em todos os planos",
  funcionalidades: [
    "Categorias feitas pela IA nos extratos importados", // sem repetir o "Importar extratos em CSV" do cartão Free
    "Dashboard com gastos por categoria e evolução mensal",
    "Chat que responde com os teus números reais",
    "Resumo do mês com alertas",
    "Planeamento: orçamento por categoria, com sugestão da IA",
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
        "Cada vez que a IA trabalha para ti: uma pergunta no chat, a categorização de um extrato importado, a leitura de um talão, uma sugestão de orçamento, o resumo do mês, o plano de poupança de um objetivo, categorizar uma movimentação nova ou um clique em \"Categorizar\" (até 300 de cada vez). Ver o dashboard, as listas e o simulador não conta. Se os pedidos acabarem, os extratos em CSV importam-se na mesma, sem categorias. Nos planos pagos, o contador volta a zero à meia-noite. No Free, volta a zero no dia 1 de cada mês. Os extratos em PDF têm também um limite próprio por mês: 15 no Essencial e 30 no Completo, com até 10 páginas cada. Cada PDF conta para esse limite e gasta também 1 pedido à IA. O limite de PDF volta a zero no dia 1.",
    },
    {
      pergunta: "Posso voltar ao Free?",
      resposta:
        "Sim. Pede-nos e passamos a tua conta para o Free. Se um plano pago chegar ao fim sem renovares, a conta passa sozinha para o Free: continuas a entrar e os teus dados ficam guardados. No Free, os pedidos à IA contam-se por mês, importas extratos em CSV e deixas de poder importar PDF e ler talões. As compras e movimentações que já tens ficam lá.",
    },
    {
      pergunta: "E os meus dados?",
      resposta:
        "Cada conta só vê os seus próprios dados. Para categorizar, ler extratos em PDF e talões e responder no chat, os dados necessários são enviados ao serviço de IA que usamos. A Control Prices não é um banco nem dá conselhos de investimento: o simulador é só uma simulação.",
    },
  ],
};

// Nome, frase, pontos e botão de cada cartão. O primeiro ponto é sempre o limite (textoDosPedidos, planos.ts),
// com o número vindo de GET /planos; nos pagos, o segundo é o limite de PDF (pdfPorMes). Aqui ficam só os outros.
export const TEXTOS_CARTOES = {
  free: {
    nome: "Free",
    frase: "Para experimentar e organizar o dia a dia.",
    pontos: ["Importar extratos em CSV", "Sem data de fim", "Ativo logo que confirmes o email"], // TEXTO NOVO (1.º ponto)
    botao: "Criar conta grátis",
  },
  essencial: {
    nome: "Essencial",
    frase: "Para quem usa a app todas as semanas.",
    pontos: ["Leitura de talões por fotografia", "Pagamento por MB Way"],
    botao: "Pedir acesso",
  },
  completo: {
    nome: "Completo",
    frase: "Para quem usa a IA várias vezes por dia.",
    pontos: ["Leitura de talões por fotografia", "Pagamento por MB Way"],
    botao: "Pedir acesso",
  },
};

export const TEXTOS_MEU_PLANO = {
  titulo: "O meu plano",
  planoAtual: "Plano atual",
  nomeSemPlano: "Sem plano",
  pedidosHoje: "Pedidos à IA hoje: {usadas} de {limite}",
  pedidosMes: "Pedidos à IA este mês: {usadas} de {limite}", // TEXTO NOVO
  reinicia: "O contador volta a zero à meia-noite.",
  reiniciaMes: "O contador volta a zero no dia 1 de cada mês.", // TEXTO NOVO
  // No cartão do menu lateral. TEXTO NOVO (o do dia já existia no CartaoPlano.tsx)
  cartaoHoje: "{usadas} de {limite} pedidos à IA hoje",
  cartaoMes: "{usadas} de {limite} pedidos à IA este mês",
  ativoAte: "Ativo até {data}",
  semDataFim: "Sem data de fim",
  avisoRenovar:
    "O teu plano termina a {data}. Depois, a conta passa para o Free. Para continuares no {plano}, pede a renovação antes dessa data.",
  // Um plano pago chegou ao fim e a conta passou para o Free (GET /plano: plano_terminado e terminou_em).
  avisoTerminou: "O teu plano {plano} terminou a {data}. A conta está agora no Free e os teus dados estão guardados.",
  // Extratos PDF do mês (não aparece no Free).
  pdfMes: "Extratos PDF este mês: {usados} de {limite}",
  pdfReinicia: "Volta a zero no dia 1 de cada mês.",
  botaoUpgrade: "Mudar de plano",
  botaoRenovar: "Pedir renovação",
  completo: "Estás no plano Completo, o que tem mais pedidos à IA por dia. Se precisares de mais, fala connosco.",
  todasFuncionalidades: "O teu plano inclui todas as funcionalidades da app.",
  // TEXTO NOVO
  semFuncoesPagas: "A importação de extratos em PDF e a leitura de talões estão disponíveis nos planos Essencial e Completo.",
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

// Página /assinatura-expirada (a API responde 403: a conta não tem linha na tabela assinaturas).
// Só aparece a uma conta sem linha em assinaturas (o registo cria sempre o Free; um plano pago que
// termina passa a Free sem vir aqui). Por isso o texto não fala de plano terminado.
export const TEXTOS_EXPIRADA = {
  titulo: "A tua conta ainda não tem plano", // TEXTO NOVO
  texto1: "Não encontrámos nenhum plano associado a esta conta. Fala connosco e resolvemos isto.", // TEXTO NOVO
  botaoPlanos: "Ver planos",
  botaoSair: "Sair da conta",
};

export const TEXTOS_LIMITE = {
  titulo: "Chegaste ao limite de hoje",
  texto: "Já usaste os {limite} pedidos à IA do teu plano. O contador volta a zero à meia-noite.",
  // Free (conta por mês). TEXTO NOVO, igual ao 429 da API (limites.py).
  tituloMes: "Chegaste ao limite deste mês",
  textoMes: "Já usaste os {limite} pedidos à IA deste mês. O contador volta a zero no dia 1.",
  link: "Mudar de plano",
};

// Limite de extratos PDF do mês (429 da API). textoApi é igual ao detail da API (mensagem_do_limite_pdf em limites.py):
// é por ele que o frontend distingue este 429 do limite de pedidos à IA.
export const TEXTOS_LIMITE_PDF = {
  titulo: "Chegaste ao limite de extratos PDF deste mês",
  texto: "Já importaste os {limite} extratos PDF deste mês. O contador volta a zero no dia 1. Até lá, podes importar o extrato em CSV.",
  textoApi:
    "Chegaste ao limite de {limite} extratos PDF este mês. O contador volta a zero no dia 1. Até lá, podes importar o extrato em CSV.",
};

// Aviso discreto quando já se usou 80% (ou mais) dos pedidos à IA do período, antes de chegar ao limite.
export const TEXTOS_AVISO_QUOTA = {
  avisoMes: "Já usaste {usadas} de {limite} pedidos à IA deste mês. O contador volta a zero no dia 1.",
  avisoDia: "Já usaste {usadas} de {limite} pedidos à IA de hoje. O contador volta a zero à meia-noite.",
  link: "Mudar de plano", // leva a /plano; não aparece no Completo
  avisoCompleto:
    "Já usaste {usadas} de {limite} pedidos à IA de hoje. O contador volta a zero à meia-noite. Se precisares de mais, fala connosco.",
  avisoCurto: "Faltam {restantes} pedidos à IA", // no cartão do menu lateral, onde há pouco espaço
  avisoCurtoUm: "Falta 1 pedido à IA", // TEXTO NOVO (singular)
};

// Alertas de orçamento do mês atual (GET /orcamentos/alertas, sem IA). Os valores vão em € (pt-PT).
export const TEXTOS_ALERTA_ORCAMENTO = {
  perto: "{categoria}: já gastaste {gasto} de {orcamento}. Estás perto do orçamento do mês.",
  atingido: "{categoria}: chegaste ao orçamento do mês. Gastaste {gasto} de {orcamento}.",
};

// Funções só dos planos pagos (402 da API). Iguais ao detail da API (FUNCOES_PAGAS em limites.py).
export const TEXTOS_PLANO_PAGO = {
  pdf: "A importação de extratos em PDF está disponível nos planos Essencial e Completo. No Free, podes importar o extrato em CSV.",
  talao: "A leitura de talões está disponível nos planos Essencial e Completo.",
  link: "Mudar de plano",
  // Em Movimentações, no Free, antes de escolher o ficheiro. TEXTO NOVO
  soCsv: "No Free importas extratos em CSV. PDF nos planos Essencial e Completo.",
};

// Movimentações: botão que pede à IA as categorias das transações que ficaram vazias
// (POST /transacoes/categorizar, conta como 1 pedido à IA). TEXTO NOVO (todos)
export const TEXTOS_CATEGORIZAR = {
  botao: "Categorizar {n} sem categoria",
  aCategorizar: "A categorizar...",
  sucesso: "{n} movimentação(ões) categorizada(s) pela IA.",
  erro: "Não foi possível categorizar. Tenta outra vez.",
};

// Dashboard de uma conta ainda sem movimentações.
export const TEXTOS_SEM_DADOS = {
  titulo: "Ainda não tens movimentações", // TEXTO NOVO
  texto: "Importa um extrato do teu banco ou cria a primeira movimentação. Os gráficos e o resumo do mês aparecem logo a seguir.", // TEXTO NOVO
  botao: "Ir para Movimentações", // TEXTO NOVO
};
