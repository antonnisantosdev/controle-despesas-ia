// Textos da página Minha reserva: objetivos de poupança, plano da IA e simulador de juros compostos.
// Passo 5 da Fase 1 Brasil: os textos saíram dos componentes .tsx sem mudar uma letra.
// Sem conselhos de investimento: as taxas do simulador são só exemplos.
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).

export const TEXTOS_RESERVA = {
  etiquetaTopo: "Objetivos de poupança",
  titulo: "Minha reserva",
  novoObjetivo: "+ Novo objetivo",
  erroCarregar: "Não foi possível carregar os objetivos. Confirma que a API está a correr.",
  aCarregar: "A carregar...",
  vazio: "Ainda não tens objetivos. Cria o primeiro, por exemplo as férias do próximo verão.",
} as const;

// Formulário "Novo objetivo" (FormNovoObjetivo, POST /objetivos).
export const TEXTOS_NOVO_OBJETIVO = {
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
} as const;

// Cartão de um objetivo (CartaoObjetivo). "de" e "corte" vêm a seguir a um valor ou categoria a negrito.
export const TEXTOS_OBJETIVO = {
  ate: "Até {mes}",
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
} as const;

// Simulador de poupança (SimuladorPoupanca, GET /simulador).
export const TEXTOS_SIMULADOR = {
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
} as const;
