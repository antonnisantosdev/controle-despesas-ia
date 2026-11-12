// Textos dos planos, preços e limites (aprovados pelo copywriter). Usar sempre "pedidos à IA".
// Os marcados com "TEXTO NOVO" ainda não foram revistos pelo copywriter.
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).
// Fase 1 Brasil, passo 6: dicionário { PT, BR }. Nos componentes: const { TEXTOS_... } = useTextos(DICIONARIO_PLANOS)
// (lib/textos.ts), que escolhe pelo país da conta. Fora da app (páginas públicas) é sempre o PT.

import type { Dicionario, Traducao } from "./textos";

const PT = {
  TEXTOS_PRECOS: {
    titulo: "Escolhe o teu plano",
    // TEXTO NOVO
    subtitulo:
      "Começas no Free, sem cartão. Os planos pagos dão-te mais pedidos à IA, importação de extratos em PDF e leitura de talões por fotografia.",
    precoPorDefinir: "Preço em breve", // só aparece se um plano pago ficar sem preço em PRECOS (planos.ts)
    precoFree: "Grátis",
    porMes: "/mês",
    precoAnual: "ou {anual}/ano (2 meses grátis)",
    notaLancamento: "Preço de lançamento.",
    // Botão no topo da página: com sessão ativa abre a app, sem sessão vai para o login.
    abrirApp: "Abrir a app",
    entrar: "Entrar",
    pedidosPorDia: "{limite} pedidos à IA por dia",
    pedidosPorMes: "{limite} pedidos à IA por mês", // TEXTO NOVO
    // Nos cartões pagos, no lugar de "Importar extratos em PDF". O número vem de GET /planos (limite_pdf).
    pdfPorMes: "Até {limitePdf} extratos PDF por mês",
    // No cartão do Free, no lugar do limite de PDF (o Free não importa PDF).
    importarCsv: "Importar extratos em CSV", // TEXTO NOVO
    // O que o chat vê e guarda, a seguir à importação. Os números vêm de GET /planos (meses_historico e
    // memoria_mensagens, ConfigIA em limites.py). {anteriores} = meses_historico - 1.
    chatMeses: "O chat vê o mês atual e os {anteriores} anteriores",
    chatTodoHistorico: "O chat vê todo o teu histórico", // meses_historico null
    chatSemMemoria: "O chat responde a cada pergunta à parte", // memoria_mensagens 0
    chatMemoria: "O chat segue a conversa: lembra-se das últimas {n} mensagens",
    // Só no cartão do Completo (effort "medium" em limites.py; GET /planos não o envia).
    analiseCuidada: "Análise mais cuidada da IA no chat, no resumo do mês e nas sugestões",
    funcionalidadesTitulo: "Incluído em todos os planos",
    funcionalidades: [
      "Categorias feitas pela IA nos extratos importados", // sem repetir o "Importar extratos em CSV" do cartão Free
      "Dashboard com gastos por categoria e evolução mensal",
      "Chat que responde com os teus números reais e procura movimentos por loja ou pessoa",
      "Resumo do mês com alertas",
      "Planeamento: orçamento por categoria, com sugestão da IA",
      "Minha reserva: objetivos de poupança e simulador de juros compostos",
      "Pagamentos que se repetem: vê as subscrições e os débitos que te saem todos os meses",
      "Resumo anual: o teu ano numa página, com comparação com o ano anterior, e guardado em PDF",
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
          "Cada vez que a IA trabalha para ti: uma pergunta no chat, a categorização de um extrato importado, a leitura de um talão, uma sugestão de orçamento, o resumo do mês, o resumo do ano (no Completo), o plano de poupança de um objetivo, categorizar uma movimentação nova ou um clique em \"Categorizar\" (até 300 de cada vez). Ver o dashboard, as listas, o resumo anual e o simulador não conta. Se os pedidos acabarem, os extratos em CSV importam-se na mesma, sem categorias. Nos planos pagos, o contador volta a zero à meia-noite. No Free, volta a zero no dia 1 de cada mês. Os extratos em PDF têm também um limite próprio por mês: 15 no Essencial e 30 no Completo, com até 10 páginas cada. Cada PDF conta para esse limite e gasta também 1 pedido à IA. O limite de PDF volta a zero no dia 1.",
      },
      {
        pergunta: "O que é o resumo anual?",
        resposta:
          'É uma página com o teu ano numa só vista: entradas, saídas e saldo, mês a mês, gastos por categoria, comparação com o ano anterior, os maiores gastos e os pagamentos que se repetem. Está em todos os planos e podes guardá-lo em PDF com o "Guardar como PDF" do browser. Descarregar em CSV só existe nos planos Essencial e Completo. O resumo escrito pela IA só existe no Completo e conta como 1 pedido à IA.',
      },
      {
        pergunta: "Como funciona a comparação de preços?",
        resposta:
          "Nos planos Essencial e Completo, a IA lê os produtos e os preços dos talões que fotografas. Em Minhas compras, no separador Preços, vês quanto pagaste por cada produto nas lojas onde o compraste nos últimos 24 meses, à unidade, ao quilo ou ao litro, com cada tamanho de embalagem à parte. Não são preços de mercado nem de lojas onde não compraste, e a leitura pode ter erros: se o mesmo produto aparecer com dois nomes, junta-os em «É o mesmo produto».",
      },
      {
        pergunta: "Posso voltar ao Free?",
        resposta:
          "Sim. Pede-nos e passamos a tua conta para o Free. Se um plano pago chegar ao fim sem renovares, a conta passa sozinha para o Free: continuas a entrar e os teus dados ficam guardados. No Free, os pedidos à IA contam-se por mês, importas extratos em CSV e deixas de poder importar PDF e ler talões. As compras e movimentações que já tens ficam lá.",
      },
      {
        pergunta: "E os meus dados?",
        resposta:
          "Cada conta só vê os seus próprios dados. Para categorizar, ler extratos em PDF e talões e responder no chat, enviamos ao serviço de IA que usamos os dados necessários, incluindo as descrições dos movimentos (por exemplo, o nome de uma loja ou de quem recebeu uma transferência). A Control Prices não é um banco nem dá conselhos de investimento: o simulador é só uma simulação.",
      },
      {
        pergunta: "O que posso perguntar ao chat?",
        resposta:
          'Perguntas sobre os teus gastos, em linguagem simples: quanto gastaste num mês ou numa categoria, a evolução de mês para mês, o orçamento e os objetivos de poupança. Para procurar uma loja ou uma pessoa, usa a palavra que aparece no extrato (por exemplo, "Quanto transferi para a Rita este mês?"). O chat diz-te o total, quantos movimentos encontrou e quais foram os maiores. Só vê os teus dados, dentro dos meses do teu plano, e não faz pagamentos nem dá conselhos de investimento.',
      },
      // Os números destas duas respostas vêm de ConfigIA em limites.py (memoria_mensagens e meses_historico):
      // se lá mudarem, mudar também aqui.
      {
        pergunta: "O chat lembra-se da conversa?",
        resposta:
          'No Free, não: cada pergunta é respondida à parte. No Essencial, o chat tem em conta as últimas 4 mensagens (as tuas e as respostas dele) e no Completo as últimas 10. Assim percebe perguntas como "e no mês anterior?". Esta memória só dura enquanto a página está aberta: se a fechares ou recarregares, a conversa começa do zero. Os números vêm sempre dos teus dados, nunca da conversa.',
      },
      {
        pergunta: "Até que mês o chat consegue ver?",
        resposta:
          "No Free, o chat vê o mês atual e os 2 anteriores. No Essencial, o mês atual e os 11 anteriores. No Completo, todo o histórico que tens na app. Em cada pergunta, o chat procura no máximo 12 meses de cada vez. Este limite é só para o chat: as tuas movimentações ficam todas guardadas, seja qual for o plano.",
      },
    ],
  },

  // Nome, frase, pontos e botão de cada cartão. O primeiro ponto é sempre o limite (textoDosPedidos, planos.ts),
  // com o número vindo de GET /planos; o segundo é a importação (pdfPorMes nos pagos, importarCsv no Free);
  // depois vêm os pontos do chat (chatMeses e os seguintes). Aqui ficam só os outros.
  TEXTOS_CARTOES: {
    free: {
      nome: "Free",
      frase: "Para experimentar e organizar o dia a dia.",
      pontos: ["Sem data de fim", "Ativo logo que confirmes o email"],
      botao: "Criar conta grátis",
    },
    essencial: {
      nome: "Essencial",
      frase: "Para quem usa a app todas as semanas.",
      pontos: ["Leitura de talões por fotografia", "Preços por loja, a partir dos talões", "Resumo anual em CSV", "Pagamento por MB Way"],
      botao: "Pedir acesso",
    },
    completo: {
      nome: "Completo",
      frase: "Para quem usa a IA várias vezes por dia.",
      pontos: ["Leitura de talões por fotografia", "Preços por loja, a partir dos talões", "Resumo anual em CSV", "Resumo do ano escrito pela IA", "Pagamento por MB Way"],
      botao: "Pedir acesso",
    },
  },

  TEXTOS_MEU_PLANO: {
    titulo: "O meu plano",
    aCarregar: "A carregar...",
    erroCarregar: "Não foi possível carregar o teu plano. Confirma que a API está a correr.",
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
  },

  // Mensagens pré-preenchidas do WhatsApp e do email. Sem sessão, a frase do email da conta sai (FRASE_EMAIL).
  TEXTOS_MENSAGEM: {
    mensagem:
      "Olá! Quero o plano {plano} da Control Prices. O email da minha conta é {email}. Como faço o pagamento por MB Way?",
    mensagemRenovar: "Olá! Quero renovar o plano {plano} da Control Prices. O email da minha conta é {email}.",
    emailAssunto: "Pedido de plano {plano} – Control Prices",
    emailAssuntoRenovar: "Renovação do plano {plano} – Control Prices",
  },

  FRASE_EMAIL: " O email da minha conta é {email}.",

  // Página /assinatura-expirada (a API responde 403: a conta não tem linha na tabela assinaturas).
  // Só aparece a uma conta sem linha em assinaturas (o registo cria sempre o Free; um plano pago que
  // termina passa a Free sem vir aqui). Por isso o texto não fala de plano terminado.
  TEXTOS_EXPIRADA: {
    titulo: "A tua conta ainda não tem plano", // TEXTO NOVO
    texto1: "Não encontrámos nenhum plano associado a esta conta. Fala connosco e resolvemos isto.", // TEXTO NOVO
    botaoPlanos: "Ver planos",
    botaoSair: "Sair da conta",
  },

  TEXTOS_LIMITE: {
    titulo: "Chegaste ao limite de hoje",
    texto: "Já usaste os {limite} pedidos à IA do teu plano. O contador volta a zero à meia-noite.",
    // Free (conta por mês). TEXTO NOVO, igual ao 429 da API (limites.py).
    tituloMes: "Chegaste ao limite deste mês",
    textoMes: "Já usaste os {limite} pedidos à IA deste mês. O contador volta a zero no dia 1.",
    link: "Mudar de plano",
  },

  // Limite de extratos PDF do mês (429 da API). textoApi é igual ao detail da API (mensagem_do_limite_pdf em limites.py):
  // é por ele que o frontend distingue este 429 do limite de pedidos à IA.
  TEXTOS_LIMITE_PDF: {
    titulo: "Chegaste ao limite de extratos PDF deste mês",
    texto: "Já importaste os {limite} extratos PDF deste mês. O contador volta a zero no dia 1. Até lá, podes importar o extrato em CSV.",
    textoApi:
      "Chegaste ao limite de {limite} extratos PDF este mês. O contador volta a zero no dia 1. Até lá, podes importar o extrato em CSV.",
  },

  // Aviso discreto quando já se usou 80% (ou mais) dos pedidos à IA do período, antes de chegar ao limite.
  TEXTOS_AVISO_QUOTA: {
    avisoMes: "Já usaste {usadas} de {limite} pedidos à IA deste mês. O contador volta a zero no dia 1.",
    avisoDia: "Já usaste {usadas} de {limite} pedidos à IA de hoje. O contador volta a zero à meia-noite.",
    link: "Mudar de plano", // leva a /plano; não aparece no Completo
    avisoCompleto:
      "Já usaste {usadas} de {limite} pedidos à IA de hoje. O contador volta a zero à meia-noite. Se precisares de mais, fala connosco.",
    avisoCurto: "Faltam {restantes} pedidos à IA", // no cartão do menu lateral, onde há pouco espaço
    avisoCurtoUm: "Falta 1 pedido à IA", // TEXTO NOVO (singular)
  },

  // Alertas de orçamento do mês atual (GET /orcamentos/alertas, sem IA). Os valores vão na moeda da conta (useFormatos).
  TEXTOS_ALERTA_ORCAMENTO: {
    perto: "{categoria}: já gastaste {gasto} de {orcamento}. Estás perto do orçamento do mês.",
    atingido: "{categoria}: chegaste ao orçamento do mês. Gastaste {gasto} de {orcamento}.",
  },

  // Funções só dos planos pagos (402 da API). Iguais ao detail da API (FUNCOES_PAGAS em limites.py).
  TEXTOS_PLANO_PAGO: {
    pdf: "A importação de extratos em PDF está disponível nos planos Essencial e Completo. No Free, podes importar o extrato em CSV.",
    talao: "A leitura de talões está disponível nos planos Essencial e Completo.",
    link: "Mudar de plano",
    // Em Movimentações, no Free, antes de escolher o ficheiro. TEXTO NOVO
    soCsv: "No Free importas extratos em CSV. PDF nos planos Essencial e Completo.",
  },

  // Movimentações: botão que pede à IA as categorias das transações que ficaram vazias
  // (POST /transacoes/categorizar, conta como 1 pedido à IA). TEXTO NOVO (todos)
  TEXTOS_CATEGORIZAR: {
    botao: "Categorizar {n} sem categoria",
    aCategorizar: "A categorizar...",
    sucesso: "{n} movimentação(ões) categorizada(s) pela IA.",
    erro: "Não foi possível categorizar. Tenta outra vez.",
  },

  // Dashboard de uma conta ainda sem movimentações.
  TEXTOS_SEM_DADOS: {
    titulo: "Ainda não tens movimentações", // TEXTO NOVO
    texto: "Importa um extrato do teu banco ou cria a primeira movimentação. Os gráficos e o resumo do mês aparecem logo a seguir.", // TEXTO NOVO
    botao: "Ir para Movimentações", // TEXTO NOVO
  },

  // Aviso antes de enviar ficheiros à IA (Movimentações e Minhas compras). Ligado à Política de Privacidade.
  // pdf e talao: texto aprovado pelo CEO. csv: TEXTO NOVO (no CSV o ficheiro não vai à IA, só a descrição
  // e o valor de cada movimento, para a categorização; ver _categorizar_claude em ia.py).
  TEXTOS_ENVIO_IA: {
    pdf: "O ficheiro é enviado à Anthropic (EUA) para ser lido pela IA e não fica guardado.",
    talao: "A fotografia é enviada à Anthropic (EUA) para ser lida pela IA e não fica guardada.",
    csv: "No CSV, só a descrição e o valor de cada movimentação são enviados à Anthropic (EUA), para a IA escolher a categoria.",
  },

  // Movimentações: apagar uma movimentação (DELETE /transacoes/{id}). TEXTO NOVO (todos)
  TEXTOS_APAGAR_MOVIMENTO: {
    botao: "Apagar",
    rotuloBotao: "Apagar {descricao}, {data}, {valor}",
    titulo: "Apagar esta movimentação?",
    texto: "{descricao}, {valor}, de {data}. Isto não se pode desfazer.",
    // Só para as movimentações criadas a partir de um talão (Minhas compras).
    avisoTalao: "Esta movimentação veio de um talão: a compra e os produtos em Minhas compras também são apagados, e deixam de contar nos preços por loja.",
    confirmar: "Apagar",
    aApagar: "A apagar...",
    cancelar: "Cancelar",
    sucesso: "Movimentação apagada.",
    erro: "Não foi possível apagar a movimentação. Tenta outra vez.",
    naoEncontrada: "Esta movimentação já não existe. A lista foi atualizada.",
  },

  // Definições: zona para apagar a conta (DELETE /conta). TEXTO NOVO (todos)
  // palavra tem de ser igual a CONFIRMACAO_APAGAR_CONTA em main.py.
  TEXTOS_APAGAR_CONTA: {
    titulo: "Apagar conta",
    aviso: "Apaga a tua conta e todos os teus dados: movimentações, orçamentos, talões, objetivos e resumos. Isto é irreversível e não há forma de recuperar os dados.",
    palavra: "APAGAR",
    rotuloCampo: "Para confirmar, escreve APAGAR",
    botao: "Apagar a minha conta",
    aApagar: "A apagar a conta...",
    erro: "Não foi possível apagar a conta. Tenta outra vez daqui a pouco.",
    // Na página inicial, depois de apagar.
    apagada: "A tua conta foi apagada, com todos os teus dados.",
  },
};

export type TextosPlanos = Traducao<typeof PT>;

// ===== BR (PT-BR) =====
// Textos PT-BR do copywriter (passo 7). Mesmas chaves e mesmos {placeholders} do PT; o tipo obriga a ter todas
// as chaves (o `npx tsc --noEmit` falha se faltar alguma).
const BR: TextosPlanos = {
  // TEXTOS_PRECOS: só a página pública /precos (sempre PT) usa o resto; no BR mudam só os textos dos cartões
  // (pedidosPorDia ... analiseCuidada), que aparecem em O meu plano. O resto fica igual ao PT.
  TEXTOS_PRECOS: {
    titulo: "Escolhe o teu plano",
    // TEXTO NOVO
    subtitulo:
      "Começas no Free, sem cartão. Os planos pagos dão-te mais pedidos à IA, importação de extratos em PDF e leitura de talões por fotografia.",
    precoPorDefinir: "Preço em breve", // também nos cartões de /plano das contas BR (preços em PRECOS_BR, ainda escondidos)
    precoFree: "Grátis",
    porMes: "/mês",
    precoAnual: "ou {anual}/ano (2 meses grátis)",
    notaLancamento: "Preço de lançamento.",
    // Botão no topo da página: com sessão ativa abre a app, sem sessão vai para o login.
    abrirApp: "Abrir a app",
    entrar: "Entrar",
    pedidosPorDia: "{limite} pedidos à IA por dia",
    pedidosPorMes: "{limite} pedidos à IA por mês", // TEXTO NOVO
    // Nos cartões pagos, no lugar de "Importar extratos em PDF". O número vem de GET /planos (limite_pdf).
    pdfPorMes: "Até {limitePdf} extratos em PDF por mês",
    // No cartão do Free, no lugar do limite de PDF (o Free não importa PDF).
    importarCsv: "Importar extratos em CSV", // TEXTO NOVO
    // O que o chat vê e guarda, a seguir à importação. Os números vêm de GET /planos (meses_historico e
    // memoria_mensagens, ConfigIA em limites.py). {anteriores} = meses_historico - 1.
    chatMeses: "O chat vê o mês atual e os {anteriores} anteriores",
    chatTodoHistorico: "O chat vê todo o seu histórico", // meses_historico null
    chatSemMemoria: "O chat responde a cada pergunta separadamente", // memoria_mensagens 0
    chatMemoria: "O chat acompanha a conversa: lembra das últimas {n} mensagens",
    // Só no cartão do Completo (effort "medium" em limites.py; GET /planos não o envia).
    analiseCuidada: "Análise mais cuidadosa da IA no chat, no resumo do mês e nas sugestões",
    funcionalidadesTitulo: "Incluído em todos os planos",
    funcionalidades: [
      "Categorias feitas pela IA nos extratos importados", // sem repetir o "Importar extratos em CSV" do cartão Free
      "Dashboard com gastos por categoria e evolução mensal",
      "Chat que responde com os teus números reais e procura movimentos por loja ou pessoa",
      "Resumo do mês com alertas",
      "Planeamento: orçamento por categoria, com sugestão da IA",
      "Minha reserva: objetivos de poupança e simulador de juros compostos",
      "Pagamentos que se repetem: vê as subscrições e os débitos que te saem todos os meses",
      "Resumo anual: o teu ano numa página, com comparação com o ano anterior, e guardado em PDF",
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
          "Cada vez que a IA trabalha para ti: uma pergunta no chat, a categorização de um extrato importado, a leitura de um talão, uma sugestão de orçamento, o resumo do mês, o resumo do ano (no Completo), o plano de poupança de um objetivo, categorizar uma movimentação nova ou um clique em \"Categorizar\" (até 300 de cada vez). Ver o dashboard, as listas, o resumo anual e o simulador não conta. Se os pedidos acabarem, os extratos em CSV importam-se na mesma, sem categorias. Nos planos pagos, o contador volta a zero à meia-noite. No Free, volta a zero no dia 1 de cada mês. Os extratos em PDF têm também um limite próprio por mês: 15 no Essencial e 30 no Completo, com até 10 páginas cada. Cada PDF conta para esse limite e gasta também 1 pedido à IA. O limite de PDF volta a zero no dia 1.",
      },
      {
        pergunta: "O que é o resumo anual?",
        resposta:
          'É uma página com o teu ano numa só vista: entradas, saídas e saldo, mês a mês, gastos por categoria, comparação com o ano anterior, os maiores gastos e os pagamentos que se repetem. Está em todos os planos e podes guardá-lo em PDF com o "Guardar como PDF" do browser. Descarregar em CSV só existe nos planos Essencial e Completo. O resumo escrito pela IA só existe no Completo e conta como 1 pedido à IA.',
      },
      {
        pergunta: "Como funciona a comparação de preços?",
        resposta:
          "Nos planos Essencial e Completo, a IA lê os produtos e os preços dos talões que fotografas. Em Minhas compras, no separador Preços, vês quanto pagaste por cada produto nas lojas onde o compraste nos últimos 24 meses, à unidade, ao quilo ou ao litro, com cada tamanho de embalagem à parte. Não são preços de mercado nem de lojas onde não compraste, e a leitura pode ter erros: se o mesmo produto aparecer com dois nomes, junta-os em «É o mesmo produto».",
      },
      {
        pergunta: "Posso voltar ao Free?",
        resposta:
          "Sim. Pede-nos e passamos a tua conta para o Free. Se um plano pago chegar ao fim sem renovares, a conta passa sozinha para o Free: continuas a entrar e os teus dados ficam guardados. No Free, os pedidos à IA contam-se por mês, importas extratos em CSV e deixas de poder importar PDF e ler talões. As compras e movimentações que já tens ficam lá.",
      },
      {
        pergunta: "E os meus dados?",
        resposta:
          "Cada conta só vê os seus próprios dados. Para categorizar, ler extratos em PDF e talões e responder no chat, enviamos ao serviço de IA que usamos os dados necessários, incluindo as descrições dos movimentos (por exemplo, o nome de uma loja ou de quem recebeu uma transferência). A Control Prices não é um banco nem dá conselhos de investimento: o simulador é só uma simulação.",
      },
      {
        pergunta: "O que posso perguntar ao chat?",
        resposta:
          'Perguntas sobre os teus gastos, em linguagem simples: quanto gastaste num mês ou numa categoria, a evolução de mês para mês, o orçamento e os objetivos de poupança. Para procurar uma loja ou uma pessoa, usa a palavra que aparece no extrato (por exemplo, "Quanto transferi para a Rita este mês?"). O chat diz-te o total, quantos movimentos encontrou e quais foram os maiores. Só vê os teus dados, dentro dos meses do teu plano, e não faz pagamentos nem dá conselhos de investimento.',
      },
      // Os números destas duas respostas vêm de ConfigIA em limites.py (memoria_mensagens e meses_historico):
      // se lá mudarem, mudar também aqui.
      {
        pergunta: "O chat lembra-se da conversa?",
        resposta:
          'No Free, não: cada pergunta é respondida à parte. No Essencial, o chat tem em conta as últimas 4 mensagens (as tuas e as respostas dele) e no Completo as últimas 10. Assim percebe perguntas como "e no mês anterior?". Esta memória só dura enquanto a página está aberta: se a fechares ou recarregares, a conversa começa do zero. Os números vêm sempre dos teus dados, nunca da conversa.',
      },
      {
        pergunta: "Até que mês o chat consegue ver?",
        resposta:
          "No Free, o chat vê o mês atual e os 2 anteriores. No Essencial, o mês atual e os 11 anteriores. No Completo, todo o histórico que tens na app. Em cada pergunta, o chat procura no máximo 12 meses de cada vez. Este limite é só para o chat: as tuas movimentações ficam todas guardadas, seja qual for o plano.",
      },
    ],
  },

  // Nome, frase, pontos e botão de cada cartão. O primeiro ponto é sempre o limite (textoDosPedidos, planos.ts),
  // com o número vindo de GET /planos; o segundo é a importação (pdfPorMes nos pagos, importarCsv no Free);
  // depois vêm os pontos do chat (chatMeses e os seguintes). Aqui ficam só os outros.
  TEXTOS_CARTOES: {
    free: {
      nome: "Free",
      frase: "Para experimentar e organizar o dia a dia.",
      pontos: [
        "Sem data de término",
        "Ativo assim que você confirmar o e-mail",
      ],
      botao: "Criar conta grátis",
    },
    essencial: {
      nome: "Essencial",
      frase: "Para quem usa a app toda semana.",
      pontos: [
        "Leitura de notas fiscais por foto",
        "Preços por loja, a partir das notas fiscais",
        "Resumo anual em CSV",
      ],
      botao: "Pedir acesso",
    },
    completo: {
      nome: "Completo",
      frase: "Para quem usa a IA várias vezes por dia.",
      pontos: [
        "Leitura de notas fiscais por foto",
        "Preços por loja, a partir das notas fiscais",
        "Resumo anual em CSV",
        "Resumo do ano escrito pela IA",
      ],
      botao: "Pedir acesso",
    },
  },

  TEXTOS_MEU_PLANO: {
    titulo: "Meu plano",
    aCarregar: "Carregando...",
    erroCarregar: "Não foi possível carregar o seu plano. Confira se a API está rodando.",
    planoAtual: "Plano atual",
    nomeSemPlano: "Sem plano",
    pedidosHoje: "Pedidos à IA hoje: {usadas} de {limite}",
    pedidosMes: "Pedidos à IA este mês: {usadas} de {limite}", // TEXTO NOVO
    reinicia: "O contador zera à meia-noite.",
    reiniciaMes: "O contador zera no dia 1 de cada mês.", // TEXTO NOVO
    // No cartão do menu lateral. TEXTO NOVO (o do dia já existia no CartaoPlano.tsx)
    cartaoHoje: "{usadas} de {limite} pedidos à IA hoje",
    cartaoMes: "{usadas} de {limite} pedidos à IA este mês",
    ativoAte: "Ativo até {data}",
    semDataFim: "Sem data de término",
    avisoRenovar: "Seu plano termina em {data}. Depois, a conta passa para o Free. Para continuar no {plano}, peça a renovação antes dessa data.",
    // Um plano pago chegou ao fim e a conta passou para o Free (GET /plano: plano_terminado e terminou_em).
    avisoTerminou: "Seu plano {plano} terminou em {data}. A conta agora está no Free e os seus dados estão salvos.",
    // Extratos PDF do mês (não aparece no Free).
    pdfMes: "Extratos em PDF este mês: {usados} de {limite}",
    pdfReinicia: "Zera no dia 1 de cada mês.",
    botaoUpgrade: "Mudar de plano",
    botaoRenovar: "Pedir renovação",
    completo: "Você está no plano Completo, o que tem mais pedidos à IA por dia. Se precisar de mais, fale com a gente.",
    todasFuncionalidades: "O seu plano inclui todas as funções da app.",
    // TEXTO NOVO
    semFuncoesPagas: "A importação de extratos em PDF e a leitura de notas fiscais estão disponíveis nos planos Essencial e Completo.",
  },

  // Mensagens pré-preenchidas do WhatsApp e do email. Sem sessão, a frase do email da conta sai (FRASE_EMAIL).
  TEXTOS_MENSAGEM: {
    mensagem: "Olá! Quero o plano {plano} da Control Prices. O e-mail da minha conta é {email}. Como faço o pagamento?",
    mensagemRenovar: "Olá! Quero renovar o plano {plano} da Control Prices. O e-mail da minha conta é {email}.",
    emailAssunto: "Pedido do plano {plano} – Control Prices",
    emailAssuntoRenovar: "Renovação do plano {plano} – Control Prices",
  },

  FRASE_EMAIL: " O e-mail da minha conta é {email}.",

  // Página /assinatura-expirada (a API responde 403: a conta não tem linha na tabela assinaturas).
  // Só aparece a uma conta sem linha em assinaturas (o registo cria sempre o Free; um plano pago que
  // termina passa a Free sem vir aqui). Por isso o texto não fala de plano terminado.
  TEXTOS_EXPIRADA: {
    titulo: "Sua conta ainda não tem plano", // TEXTO NOVO
    texto1: "Não encontramos nenhum plano associado a esta conta. Fale com a gente e vamos resolver isso.", // TEXTO NOVO
    botaoPlanos: "Ver planos",
    botaoSair: "Sair da conta",
  },

  TEXTOS_LIMITE: {
    titulo: "Você chegou ao limite de hoje",
    texto: "Você já usou os {limite} pedidos à IA do seu plano. O contador zera à meia-noite.",
    // Free (conta por mês). TEXTO NOVO, igual ao 429 da API (limites.py).
    tituloMes: "Você chegou ao limite deste mês",
    textoMes: "Você já usou os {limite} pedidos à IA deste mês. O contador zera no dia 1.",
    link: "Mudar de plano",
  },

  // Limite de extratos PDF do mês (429 da API). textoApi é igual ao detail da API (mensagem_do_limite_pdf em limites.py):
  // é por ele que o frontend distingue este 429 do limite de pedidos à IA.
  TEXTOS_LIMITE_PDF: {
    titulo: "Você chegou ao limite de extratos em PDF deste mês",
    texto: "Você já importou os {limite} extratos em PDF deste mês. O contador zera no dia 1. Até lá, você pode importar o extrato em CSV.",
    // Igual à API (mensagens.py, limite_pdf BR).
    textoApi:
      "Você chegou ao limite de {limite} extratos PDF este mês. O contador zera no dia 1. Até lá, você pode importar o extrato em CSV.",
  },

  // Aviso discreto quando já se usou 80% (ou mais) dos pedidos à IA do período, antes de chegar ao limite.
  TEXTOS_AVISO_QUOTA: {
    avisoMes: "Você já usou {usadas} de {limite} pedidos à IA deste mês. O contador zera no dia 1.",
    avisoDia: "Você já usou {usadas} de {limite} pedidos à IA de hoje. O contador zera à meia-noite.",
    link: "Mudar de plano", // leva a /plano; não aparece no Completo
    avisoCompleto: "Você já usou {usadas} de {limite} pedidos à IA de hoje. O contador zera à meia-noite. Se precisar de mais, fale com a gente.",
    avisoCurto: "Faltam {restantes} pedidos à IA", // no cartão do menu lateral, onde há pouco espaço
    avisoCurtoUm: "Falta 1 pedido à IA", // TEXTO NOVO (singular)
  },

  // Alertas de orçamento do mês atual (GET /orcamentos/alertas, sem IA). Os valores vão na moeda da conta (useFormatos).
  TEXTOS_ALERTA_ORCAMENTO: {
    perto: "{categoria}: você já gastou {gasto} de {orcamento}. Está perto do orçamento do mês.",
    atingido: "{categoria}: você chegou ao orçamento do mês. Gastou {gasto} de {orcamento}.",
  },

  // Funções só dos planos pagos (402 da API). Iguais ao detail da API (FUNCOES_PAGAS em limites.py).
  TEXTOS_PLANO_PAGO: {
    pdf: "A importação de extratos em PDF está disponível nos planos Essencial e Completo. No Free, você pode importar o extrato em CSV.",
    talao: "A leitura de notas fiscais está disponível nos planos Essencial e Completo.",
    link: "Mudar de plano",
    // Em Movimentações, no Free, antes de escolher o ficheiro. TEXTO NOVO
    soCsv: "No Free, você importa extratos em CSV. PDF nos planos Essencial e Completo.",
  },

  // Movimentações: botão que pede à IA as categorias das transações que ficaram vazias
  // (POST /transacoes/categorizar, conta como 1 pedido à IA). TEXTO NOVO (todos)
  TEXTOS_CATEGORIZAR: {
    botao: "Categorizar {n} sem categoria",
    aCategorizar: "Categorizando...",
    sucesso: "{n} movimentação(ões) categorizada(s) pela IA.",
    erro: "Não foi possível categorizar. Tente de novo.",
  },

  // Dashboard de uma conta ainda sem movimentações.
  TEXTOS_SEM_DADOS: {
    titulo: "Você ainda não tem movimentações", // TEXTO NOVO
    texto: "Importe um extrato do seu banco ou crie a primeira movimentação. Os gráficos e o resumo do mês aparecem logo em seguida.", // TEXTO NOVO
    botao: "Ir para Movimentações", // TEXTO NOVO
  },

  // Aviso antes de enviar ficheiros à IA (Movimentações e Minhas compras). Ligado à Política de Privacidade.
  // pdf e talao: texto aprovado pelo CEO. csv: TEXTO NOVO (no CSV o ficheiro não vai à IA, só a descrição
  // e o valor de cada movimento, para a categorização; ver _categorizar_claude em ia.py).
  TEXTOS_ENVIO_IA: {
    pdf: "O arquivo é enviado à Anthropic (EUA) para ser lido pela IA e não fica salvo.",
    talao: "A foto é enviada à Anthropic (EUA) para ser lida pela IA e não fica salva.",
    csv: "No CSV, só a descrição e o valor de cada movimentação são enviados à Anthropic (EUA), para a IA escolher a categoria.",
  },

  // Movimentações: apagar uma movimentação (DELETE /transacoes/{id}). TEXTO NOVO (todos)
  TEXTOS_APAGAR_MOVIMENTO: {
    botao: "Apagar",
    rotuloBotao: "Apagar {descricao}, {data}, {valor}",
    titulo: "Apagar esta movimentação?",
    texto: "{descricao}, {valor}, de {data}. Isso não pode ser desfeito.",
    // Só para as movimentações criadas a partir de um talão (Minhas compras).
    avisoTalao: "Esta movimentação veio de uma nota fiscal: a compra e os produtos em Minhas compras também são apagados e deixam de contar nos preços por loja.",
    confirmar: "Apagar",
    aApagar: "Apagando...",
    cancelar: "Cancelar",
    sucesso: "Movimentação apagada.",
    erro: "Não foi possível apagar a movimentação. Tente de novo.",
    naoEncontrada: "Esta movimentação não existe mais. A lista foi atualizada.",
  },

  // Definições: zona para apagar a conta (DELETE /conta). TEXTO NOVO (todos)
  // palavra tem de ser igual a CONFIRMACAO_APAGAR_CONTA em main.py.
  TEXTOS_APAGAR_CONTA: {
    titulo: "Apagar conta",
    aviso: "Apaga a sua conta e todos os seus dados: movimentações, orçamentos, notas fiscais, metas e resumos. Isso é irreversível e não tem como recuperar os dados.",
    // Igual a CONFIRMACAO_APAGAR_CONTA em main.py: não traduzir.
    palavra: "APAGAR",
    rotuloCampo: "Para confirmar, digite APAGAR",
    botao: "Apagar minha conta",
    aApagar: "Apagando a conta...",
    erro: "Não foi possível apagar a conta. Tente de novo daqui a pouco.",
    // Na página inicial, depois de apagar.
    apagada: "Sua conta foi apagada, com todos os seus dados.",
  },
};

export const DICIONARIO_PLANOS: Dicionario<TextosPlanos> = { PT, BR };
