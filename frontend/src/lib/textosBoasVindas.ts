// Textos do questionário de boas-vindas e da página Definições (aprovados pelo CEO, 2026-11-12).
// Os marcados com "TEXTO NOVO" ainda não foram revistos pelo copywriter.
// No BR é sempre "o app" (nunca "a app").
// {chaves} entre chavetas são trocadas com preencher() (planos.ts).
// Nos componentes: const { TEXTOS_... } = useTextos(DICIONARIO_BOAS_VINDAS). O questionário escolhe pelo país
// escolhido no ecrã 1 (DICIONARIO_BOAS_VINDAS[pais]), para os ecrãs seguintes já virem na língua certa.

import type { Pais } from "./formatos";
import type { Dicionario, Traducao } from "./textos";

// As opções (iguais às do backend: models.py e sql/021). A ordem é a dos ecrãs.
export const MOTIVOS = ["nao_sei", "fim_mes", "supermercado", "folhas", "poupar", "experimentar", "outro"] as const;
export const OBJETIVOS = ["importar", "categorias", "orcamento", "chat", "resumo", "reserva", "taloes"] as const;
export type Motivo = (typeof MOTIVOS)[number];
export type Objetivo = (typeof OBJETIVOS)[number];

// No Brasil escondem-se "importar" (ainda sem extratos de bancos do Brasil) e "taloes" (decisão do CEO).
// A API aceita a lista toda: nas definições, um objetivo já escolhido aparece sempre.
export const OBJETIVOS_POR_PAIS: Record<Pais, readonly Objetivo[]> = {
  PT: OBJETIVOS,
  BR: OBJETIVOS.filter((objetivo) => objetivo !== "importar" && objetivo !== "taloes"),
};

// Ecrã 1 (país): texto neutro, igual nos dois países (ainda não se sabe onde a pessoa vive).
export const TEXTOS_PAIS = {
  tituloPais: "País onde vive",
  subtituloPais: "Define a língua, a moeda e o formato das datas.",
  opcaoPortugal: "Portugal",
  opcaoBrasil: "Brasil",
  privacidadePais: "Serve para adaptar a app. Pode mudar mais tarde.",
  erroPais: "Escolha um país.",
};

const PT = {
  TEXTOS_BOAS_VINDAS: {
    progresso: "Passo {atual} de {total}",
    continuar: "Continuar",
    saltar: "Saltar",
    voltar: "Voltar",
    comecar: "Começar",
    privacidade:
      "Usamos estas respostas para adaptar a app a ti e para estatísticas gerais, que não te identificam. Podes mudá-las nas definições.",
    aGuardar: "A guardar…", // TEXTO NOVO
    erroGuardar: "Não foi possível guardar as respostas agora. Tenta mais tarde.", // TEXTO NOVO (igual à API)

    // Ecrã 2: cartões, contas e moeda.
    tituloBancos: "De que países são os teus cartões e contas?",
    subtituloBancos: "Serve para escolher a moeda em que a app mostra os valores.",
    bancosPortugal: "Portugal",
    bancosBrasil: "Brasil",
    bancosOsDois: "Dos dois países",
    erroBancos: "Escolhe uma opção.",
    tituloMoeda: "Em que moeda queres controlar agora?",
    subtituloMoeda:
      "Por agora, cada conta controla uma moeda. Escolhe a das contas que usas mais. Queremos juntar a outra moeda mais tarde, ainda sem data.",
    moedaEuro: "Euro (€)",
    moedaReal: "Real (R$)",
    avisoMoeda:
      "Importa só extratos nesta moeda, para os totais baterem certo. Depois de teres dados na conta, a moeda já não muda.",
    erroMoeda: "Escolhe a moeda com que queres começar.",

    // Ecrã 3: motivo (escolha única, pode saltar).
    tituloMotivo: "Porque instalaste a app?",
    subtituloMotivo: "Escolhe o que mais se parece contigo.",
    motivos: {
      nao_sei: "Não sei para onde vai o meu dinheiro",
      fim_mes: "O dinheiro não chega ao fim do mês",
      supermercado: "As compras do supermercado pesam cada vez mais",
      folhas: "Perco tempo com folhas de cálculo",
      poupar: "Quero começar a pôr dinheiro de parte",
      experimentar: "Só estou a experimentar",
      outro: "Outro motivo",
    },

    // Ecrã 4: objetivos (várias, pode saltar).
    tituloObjetivos: "O que queres conseguir?",
    subtituloObjetivos: "Escolhe as que quiseres.",
    objetivos: {
      importar: "Importar os extratos do banco em vez de escrever tudo à mão",
      categorias: "Ver os gastos organizados por categoria",
      orcamento: "Ter um orçamento por categoria e receber alertas",
      chat: "Perguntar à IA sobre os meus gastos",
      resumo: "Receber um resumo do mês",
      reserva: "Juntar dinheiro para um objetivo",
      taloes: "Guardar os talões e comparar preços entre lojas (planos pagos)",
    },
  },
  TEXTOS_DEFINICOES: {
    titulo: "Definições",
    menu: "Definições", // TEXTO NOVO (ligação no menu)
    // Em "O meu plano", por cima do sítio onde estava o "Apagar conta". TEXTO NOVO
    ligacaoPlano: "Definições da conta e apagar conta",
    tituloPerfil: "O teu perfil",
    descricaoPerfil: "As respostas que deste na primeira entrada. Podes mudá-las quando quiseres.",
    rotuloPais: "Onde vives",
    ajudaPais: "Muda a língua, o fuso horário e o formato das datas e dos valores.",
    rotuloBancos: "Países dos cartões e contas",
    rotuloMoeda: "Moeda da conta",
    ajudaMoeda: "Só muda numa conta sem dados.",
    erroMoedaComDados: "Esta conta já tem dados, por isso a moeda não pode mudar.",
    rotuloMotivo: "Porque instalaste a app",
    rotuloObjetivos: "O que queres conseguir",
    semResposta: "Sem resposta",
    limparRespostas: "Apagar estas duas respostas",
    guardar: "Guardar",
    guardado: "Alterações guardadas.",
    aCarregar: "A carregar o perfil…", // TEXTO NOVO
    erroCarregar: "Não foi possível carregar o perfil. Tenta mais tarde.", // TEXTO NOVO
  },
};

export type TextosBoasVindas = Traducao<typeof PT>;

const BR: TextosBoasVindas = {
  TEXTOS_BOAS_VINDAS: {
    progresso: "Etapa {atual} de {total}",
    continuar: "Continuar",
    saltar: "Pular",
    voltar: "Voltar",
    comecar: "Começar",
    privacidade:
      "Usamos essas respostas para adaptar o app a você e para estatísticas gerais, que não identificam você. Você pode mudar nas configurações.",
    aGuardar: "Salvando…", // TEXTO NOVO
    erroGuardar: "Não foi possível salvar as respostas agora. Tente mais tarde.", // TEXTO NOVO (igual à API)

    tituloBancos: "De quais países são seus cartões e contas?",
    subtituloBancos: "Serve para escolher a moeda em que o app mostra os valores.",
    bancosPortugal: "Portugal",
    bancosBrasil: "Brasil",
    bancosOsDois: "Dos dois países",
    erroBancos: "Escolha uma opção.",
    tituloMoeda: "Em que moeda você quer controlar agora?",
    subtituloMoeda:
      "Por enquanto, cada conta controla uma moeda. Escolha a das contas que você mais usa. Queremos incluir a outra moeda mais tarde, ainda sem data.",
    moedaEuro: "Euro (€)",
    moedaReal: "Real (R$)",
    avisoMoeda:
      "Importe só extratos nessa moeda, para os totais baterem. Depois que a conta tiver dados, a moeda não muda mais.",
    erroMoeda: "Escolha a moeda com que você quer começar.",

    tituloMotivo: "Por que você instalou o app?",
    subtituloMotivo: "Escolha o que mais combina com você.",
    motivos: {
      nao_sei: "Não sei para onde vai meu dinheiro",
      fim_mes: "O dinheiro não chega até o fim do mês",
      supermercado: "O mercado está pesando cada vez mais no bolso",
      folhas: "Perco tempo com planilhas",
      poupar: "Quero começar a guardar dinheiro",
      experimentar: "Só estou conhecendo",
      outro: "Outro motivo",
    },

    tituloObjetivos: "O que você quer conseguir?",
    subtituloObjetivos: "Escolha quantas quiser.",
    objetivos: {
      // Escondidos no BR no questionário (OBJETIVOS_POR_PAIS). Só aparecem nas definições se já estiverem escolhidos
      // (ex.: quem mudou de Portugal para o Brasil). TEXTO NOVO (sem versão BR aprovada).
      importar: "Importar os extratos do banco em vez de digitar tudo à mão",
      categorias: "Ver os gastos organizados por categoria",
      orcamento: "Ter um orçamento por categoria e receber alertas",
      chat: "Perguntar à IA sobre meus gastos",
      resumo: "Receber um resumo do mês",
      reserva: "Guardar dinheiro para uma meta",
      taloes: "Guardar as notas fiscais e comparar preços entre lojas (planos pagos)", // TEXTO NOVO
    },
  },
  TEXTOS_DEFINICOES: {
    titulo: "Configurações",
    menu: "Configurações", // TEXTO NOVO
    ligacaoPlano: "Configurações da conta e apagar conta", // TEXTO NOVO
    tituloPerfil: "Seu perfil",
    descricaoPerfil: "As respostas que você deu no primeiro acesso. Você pode mudar quando quiser.",
    rotuloPais: "Onde você mora",
    ajudaPais: "Muda o idioma, o fuso horário e o formato das datas e dos valores.",
    rotuloBancos: "Países dos cartões e contas",
    rotuloMoeda: "Moeda da conta",
    ajudaMoeda: "Só pode ser alterada em uma conta sem dados.",
    erroMoedaComDados: "Esta conta já tem dados, por isso a moeda não pode ser alterada.",
    rotuloMotivo: "Por que você instalou o app",
    rotuloObjetivos: "O que você quer conseguir",
    semResposta: "Sem resposta",
    limparRespostas: "Apagar essas duas respostas",
    guardar: "Salvar",
    guardado: "Alterações salvas.",
    aCarregar: "Carregando o perfil…", // TEXTO NOVO
    erroCarregar: "Não foi possível carregar o perfil. Tente mais tarde.", // TEXTO NOVO
  },
};

export const DICIONARIO_BOAS_VINDAS: Dicionario<TextosBoasVindas> = { PT, BR };
