// Textos da página Minha reserva: objetivos de poupança, plano da IA e simulador de juros compostos.
// Passo 5 da Fase 1 Brasil: os textos saíram dos componentes .tsx sem mudar uma letra.
// Sem conselhos de investimento: as taxas do simulador são só exemplos.
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).
// Fase 1 Brasil, passo 6: dicionário { PT, BR }. Nos componentes: const { TEXTOS_... } = useTextos(DICIONARIO_RESERVA)
// (lib/textos.ts), que escolhe pelo país da conta. Fora da app (páginas públicas) é sempre o PT.

import type { Dicionario, Traducao } from "./textos";

const PT = {
  TEXTOS_RESERVA: {
    etiquetaTopo: "Objetivos de poupança",
    titulo: "Minha reserva",
    novoObjetivo: "+ Novo objetivo",
    erroCarregar: "Não foi possível carregar os objetivos. Confirma que a API está a correr.",
    aCarregar: "A carregar...",
    vazio: "Ainda não tens objetivos. Cria o primeiro, por exemplo as férias do próximo verão.",
  } as const,

  // Formulário "Novo objetivo" (FormNovoObjetivo, POST /objetivos).
  TEXTOS_NOVO_OBJETIVO: {
    titulo: "Novo objetivo",
    cancelar: "Cancelar",
    nome: "Nome",
    marcadorNome: "Ex.: Férias no verão",
    valor: "Quanto queres juntar ({simbolo})", // {simbolo}: € ou R$, conforme a moeda da conta
    marcadorValor: "0,00",
    data: "Até quando",
    erroValor: "Escreve um valor maior do que zero.",
    erroGuardar: "Não foi possível guardar. Confirma os dados e tenta outra vez.",
    guardar: "Guardar",
    aGuardar: "A guardar...",
  } as const,

  // Cartão de um objetivo (CartaoObjetivo). "de" e "corte" vêm a seguir a um valor ou categoria a negrito.
  TEXTOS_OBJETIVO: {
    ate: "Até {mes}",
    // O prazo já passou e o objetivo não foi atingido.
    prazoPassado: "O prazo terminou em {mes}",
    de: " de {alvo}",
    rotuloProgresso: "Progresso de {nome}",
    percentagem: "{percentagem}% do objetivo",
    juntei: "+ Juntei dinheiro",
    planoPoupanca: "✨ Plano de poupança",
    aPlanear: "A IA está a pensar...",
    apagarPergunta: "Apagar?",
    sim: "Sim",
    nao: "Não",
    apagar: "Apagar",
    rotuloValor: "Valor que juntaste, em {moeda}", // {moeda}: euros ou reais
    marcadorValor: "{zero}", // "0,00 €" (ou "R$ 0,00"), conforme a moeda da conta
    adicionar: "Adicionar",
    erroValor: "Escreve um valor maior do que zero.",
    erroAtualizar: "Não foi possível atualizar o valor poupado.",
    erroPlano: "Não foi possível criar o plano. Tenta outra vez.",
    erroApagar: "Não foi possível apagar o objetivo.",
    viavel: "Consegues chegar lá",
    inviavel: "Assim não chegas lá",
    // A seguir à categoria; o motivo da IA vem depois.
    corte: ": menos {valor} por mês. ",
  } as const,

  // Simulador de poupança (SimuladorPoupanca, GET /simulador).
  TEXTOS_SIMULADOR: {
    titulo: "E se poupares todos os meses?",
    texto: "Vê quanto juntas com juros compostos, por exemplo com o dinheiro que deixas de gastar numa subscrição.",
    mensal: "Poupança por mês ({simbolo})",
    duranteUmAno: "Durante 1 ano",
    duranteAnos: "Durante {anos} anos",
    taxa: "Rendimento anual (exemplo)",
    taxas: [
      { valor: 0, nome: "0% (dinheiro parado)" },
      { valor: 2, nome: "2% ao ano" },
      { valor: 4, nome: "4% ao ano" },
      { valor: 6, nome: "6% ao ano" },
    ],
    erro: "Não foi possível simular. Confirma os valores (máx. {maximo} por mês).", // {maximo}: "10 000 €" na moeda da conta
    depositaste: "Depositaste",
    ganhoJuros: "Ganho com juros",
    terias: "Terias ao fim de {anos} anos",
    eixoAno: "{ano}.º",
    aoFimDeUmAno: "Ao fim de 1 ano",
    aoFimDeAnos: "Ao fim de {anos} anos",
    depositado: "Depositado",
    comJuros: "Com juros",
    aviso:
      "Simulação com uma taxa fixa de exemplo, sem impostos, comissões nem inflação. Não é um conselho de investimento: os rendimentos reais variam e não são garantidos.",
  } as const,
};

export type TextosReserva = Traducao<typeof PT>;

// ===== BR (PT-BR) =====
// Textos PT-BR do copywriter (passo 7). Mesmas chaves e mesmos {placeholders} do PT; o tipo obriga a ter todas
// as chaves (o `npx tsc --noEmit` falha se faltar alguma).
const BR: TextosReserva = {
  TEXTOS_RESERVA: {
    etiquetaTopo: "Metas de economia",
    titulo: "Minha reserva",
    novoObjetivo: "+ Nova meta",
    erroCarregar: "Não foi possível carregar as metas. Confira se a API está rodando.",
    aCarregar: "Carregando...",
    vazio: "Você ainda não tem metas. Crie a primeira, por exemplo uma viagem nas próximas férias.",
  },

  // Formulário "Novo objetivo" (FormNovoObjetivo, POST /objetivos).
  TEXTOS_NOVO_OBJETIVO: {
    titulo: "Nova meta",
    cancelar: "Cancelar",
    nome: "Nome",
    marcadorNome: "Ex.: Viagem de férias",
    valor: "Quanto você quer juntar ({simbolo})", // {simbolo}: € ou R$, conforme a moeda da conta
    marcadorValor: "0,00",
    data: "Até quando",
    erroValor: "Digite um valor maior que zero.",
    erroGuardar: "Não foi possível salvar. Confira os dados e tente de novo.",
    guardar: "Salvar",
    aGuardar: "Salvando...",
  },

  // Cartão de um objetivo (CartaoObjetivo). "de" e "corte" vêm a seguir a um valor ou categoria a negrito.
  TEXTOS_OBJETIVO: {
    ate: "Até {mes}",
    prazoPassado: "O prazo terminou em {mes}",
    de: " de {alvo}",
    rotuloProgresso: "Progresso de {nome}",
    percentagem: "{percentagem}% da meta",
    juntei: "+ Juntei dinheiro",
    planoPoupanca: "✨ Plano para chegar lá",
    aPlanear: "A IA está pensando...",
    apagarPergunta: "Apagar?",
    sim: "Sim",
    nao: "Não",
    apagar: "Apagar",
    rotuloValor: "Valor que você juntou, em {moeda}", // {moeda}: euros ou reais
    marcadorValor: "{zero}", // "0,00 €" (ou "R$ 0,00"), conforme a moeda da conta
    adicionar: "Adicionar",
    erroValor: "Digite um valor maior que zero.",
    erroAtualizar: "Não foi possível atualizar o valor guardado.",
    erroPlano: "Não foi possível criar o plano. Tente de novo.",
    erroApagar: "Não foi possível apagar a meta.",
    viavel: "Você consegue chegar lá",
    inviavel: "Assim você não chega lá",
    // A seguir à categoria; o motivo da IA vem depois.
    corte: ": menos {valor} por mês. ",
  },

  // Simulador de poupança (SimuladorPoupanca, GET /simulador).
  TEXTOS_SIMULADOR: {
    titulo: "E se você guardar dinheiro todo mês?",
    texto: "Veja quanto você junta com juros compostos, por exemplo com o dinheiro que deixa de gastar em uma assinatura.",
    mensal: "Quanto guardar por mês ({simbolo})",
    duranteUmAno: "Durante 1 ano",
    duranteAnos: "Durante {anos} anos",
    taxa: "Rendimento anual (exemplo)",
    taxas: [
      { valor: 0, nome: "0% (dinheiro parado)" },
      { valor: 2, nome: "2% ao ano" },
      { valor: 4, nome: "4% ao ano" },
      { valor: 6, nome: "6% ao ano" },
    ],
    erro: "Não foi possível simular. Confira os valores (máx. {maximo} por mês).", // {maximo}: "10 000 €" na moeda da conta
    depositaste: "Você depositou",
    ganhoJuros: "Ganho com juros",
    terias: "Você teria depois de {anos} anos",
    eixoAno: "{ano}º",
    aoFimDeUmAno: "Depois de 1 ano",
    aoFimDeAnos: "Depois de {anos} anos",
    depositado: "Depositado",
    comJuros: "Com juros",
    aviso: "Simulação com uma taxa fixa de exemplo, sem impostos, taxas nem inflação. Não é uma recomendação de investimento: os rendimentos reais variam e não são garantidos.",
  },
};

export const DICIONARIO_RESERVA: Dicionario<TextosReserva> = { PT, BR };
