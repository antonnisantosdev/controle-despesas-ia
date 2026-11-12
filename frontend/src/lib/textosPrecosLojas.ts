// Textos do separador "Preços" em Minhas compras (preço de um produto em cada loja, a partir dos talões).
// Revistos pelo copywriter. Não confundir com TEXTOS_PRECOS (textosPlanos.ts), que é a página dos planos.
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).
// Fase 1 Brasil, passo 6: dicionário { PT, BR }. Nos componentes: const { TEXTOS_... } = useTextos(DICIONARIO_PRECOS_LOJAS)
// (lib/textos.ts), que escolhe pelo país da conta. Fora da app (páginas públicas) é sempre o PT.

import type { Dicionario, Traducao } from "./textos";

const PT = {
  TEXTOS_PRECOS_LOJAS: {
    // Separadores da página
    separadorTaloes: "Talões",
    separadorPrecos: "Preços",
    rotuloSeparadores: "Ver talões ou preços",

    // Lista
    explicacao: "Vê quanto pagaste por um produto em cada loja onde o compraste. Os preços vêm dos talões que fotografaste e que a IA leu, por isso pode haver erros de leitura: se um valor parecer estranho, confirma no talão.",
    rotuloPesquisa: "Procurar produto",
    marcadorPesquisa: "Ex.: leite, bananas, café",
    aCarregar: "A carregar...",
    aProcurar: "A procurar...",
    vazio: "Ainda não há produtos para comparar. Fotografa os talões das tuas compras no separador Talões e os produtos aparecem aqui.",
    semResultados: "Nenhum produto encontrado para «{termo}». Experimenta outra palavra.",
    erroLista: "Não foi possível carregar os produtos. Tenta outra vez daqui a pouco.",
    tentarOutraVez: "Tentar outra vez",
    maximo: "Mostramos os 50 produtos comprados há menos tempo. Usa a pesquisa para encontrar outros.",
    lojas1: "1 loja",
    lojasN: "{n} lojas",
    compras1: "1 compra",
    comprasN: "{n} compras",
    ultimaCompra: "Última compra a {data}",

    // Detalhe
    voltar: "Voltar à lista",
    aCarregarProduto: "A carregar os preços...",
    erroProduto: "Não foi possível carregar os preços deste produto. Tenta outra vez daqui a pouco.",
    naoExiste: "Este produto já não aparece nas tuas compras. Se o juntaste a outro, procura pelo nome desse produto.",
    maisBaratoAgora: "Mais barato da última vez",
    maisBaratoEm: "em {loja}",
    pagoA: "compra de {data}",
    soUmaLoja: "Só compraste este produto numa loja. Quando o comprares noutra e fotografares o talão, comparamos os preços aqui.",
    variasUnidades: "Este produto aparece ao quilo, ao litro ou à unidade em talões diferentes. Os preços estão separados por unidade, porque só assim se podem comparar.",
    tituloUnidade: "Preço {unidade}",
    porLoja: "Por loja",
    etiquetaMaisBarata: "Mais barata",
    agora: "Último preço",
    minimo: "Mais baixo",
    medio: "Média",
    nCompras: "Compras",
    historico: "Histórico",
    verMaisHistorico: "Ver o histórico todo ({n})",
    notaLeitura: "Valores lidos dos talões pela IA, que podem ter erros. Cada tamanho de embalagem conta como um produto à parte. Marcas diferentes do mesmo produto e tamanho normalmente contam como o mesmo; se não, junta-os em «É o mesmo produto».",

    // Juntar produtos
    juntarTitulo: "É o mesmo produto?",
    juntarExplicacao: "Se o mesmo produto aparece com nomes diferentes (ex.: «Leite UHT M/G» e «Leite meio gordo»), junta-os para ver todos os preços no mesmo sítio. Podes desfazer depois.",
    juntarAbrir: "Juntar com outro produto",
    juntarFechar: "Cancelar",
    juntarPesquisa: "Procurar o outro produto",
    juntarEscolher: "Escolhe o produto que é igual a «{nome}»",
    juntarSemOutros: "Não encontrámos outros produtos. Experimenta outra palavra.",
    juntarBotao: "Juntar",
    juntarConfirmar: "Juntar «{origem}» a «{destino}»? Os preços de «{origem}» passam a aparecer aqui. Podes desfazer.",
    juntarSim: "Sim, juntar",
    juntarNao: "Não",
    aJuntar: "A juntar...",
    juntado: "Feito: «{origem}» passa a contar como «{destino}».",
    juntadosAqui: "Produtos juntos a este",
    juntadosTitulo: "Produtos juntados ({n})",
    juntadosExplicacao: "Os produtos que juntaste por serem o mesmo. Desfaz uma junção se te enganaste.",
    juntadosErro: "Não foi possível carregar os produtos juntados.",
    juntadoEm: "Juntado a {data}",
    rotuloJuncao: "{origem} passa a contar como {destino}",
    desfazer: "Desfazer",
    desfazerRotulo: "Desfazer a junção de {nome}",
    desfazerConfirmar: "Desfazer a junção? «{origem}» volta a ser um produto à parte de «{destino}».",
    desfazerSim: "Sim, desfazer",
    aDesfazer: "A desfazer...",
    desfeito: "Junção desfeita: «{nome}» volta a ser um produto à parte.",
    erroJuntar: "Não foi possível juntar os produtos. Tenta outra vez.",
    erroDesfazer: "Não foi possível desfazer a junção. Tenta outra vez.",

    // No Free, antes de pedir à API (a API devolve o mesmo texto no 402).
    soPlanosPagos: "Comparar preços entre as lojas onde compraste está disponível nos planos Essencial e Completo.",
  },

  // "1,09 €/kg": o sufixo vai a seguir ao preço já formatado (precoUnitario em compras/formatosPrecos.ts).
  SUFIXO_UNIDADE: { un: "/un", kg: "/kg", l: "/l" } as Record<string, string>,

  // Para o título de cada unidade: "Preço por unidade", "Preço por kg", "Preço por litro".
  NOME_UNIDADE: { un: "por unidade", kg: "por kg", l: "por litro" } as Record<string, string>,
};

export type TextosPrecosLojas = Traducao<typeof PT>;

// ===== BR (PT-BR) =====
// Textos PT-BR do copywriter (passo 7). Mesmas chaves e mesmos {placeholders} do PT; o tipo obriga a ter todas
// as chaves (o `npx tsc --noEmit` falha se faltar alguma).
const BR: TextosPrecosLojas = {
  TEXTOS_PRECOS_LOJAS: {
    // Separadores da página
    separadorTaloes: "Notas fiscais",
    separadorPrecos: "Preços",
    rotuloSeparadores: "Ver notas fiscais ou preços",

    // Lista
    explicacao: "Veja quanto você pagou por um produto em cada loja onde comprou. Os preços vêm das notas fiscais que você fotografou e que a IA leu, por isso pode haver erros de leitura: se um valor parecer estranho, confira na nota.",
    rotuloPesquisa: "Buscar produto",
    marcadorPesquisa: "Ex.: leite, banana, café",
    aCarregar: "Carregando...",
    aProcurar: "Buscando...",
    vazio: "Ainda não há produtos para comparar. Fotografe as notas fiscais das suas compras na aba Notas fiscais e os produtos aparecem aqui.",
    semResultados: "Nenhum produto encontrado para “{termo}”. Tente outra palavra.",
    erroLista: "Não foi possível carregar os produtos. Tente de novo daqui a pouco.",
    tentarOutraVez: "Tentar de novo",
    maximo: "Mostramos os 50 produtos comprados mais recentemente. Use a busca para encontrar outros.",
    lojas1: "1 loja",
    lojasN: "{n} lojas",
    compras1: "1 compra",
    comprasN: "{n} compras",
    ultimaCompra: "Última compra em {data}",

    // Detalhe
    voltar: "Voltar à lista",
    aCarregarProduto: "Carregando os preços...",
    erroProduto: "Não foi possível carregar os preços deste produto. Tente de novo daqui a pouco.",
    naoExiste: "Este produto não aparece mais nas suas compras. Se você juntou com outro, busque pelo nome desse produto.",
    maisBaratoAgora: "Mais barato da última vez",
    maisBaratoEm: "em {loja}",
    pagoA: "compra de {data}",
    soUmaLoja: "Você só comprou este produto em uma loja. Quando comprar em outra e fotografar a nota fiscal, comparamos os preços aqui.",
    variasUnidades: "Este produto aparece por quilo, por litro ou por unidade em notas fiscais diferentes. Os preços estão separados por unidade, porque só assim dá para comparar.",
    tituloUnidade: "Preço {unidade}",
    porLoja: "Por loja",
    etiquetaMaisBarata: "Mais barata",
    agora: "Último preço",
    minimo: "Mais baixo",
    medio: "Média",
    nCompras: "Compras",
    historico: "Histórico",
    verMaisHistorico: "Ver o histórico completo ({n})",
    notaLeitura: "Valores lidos das notas fiscais pela IA, que podem ter erros. Cada tamanho de embalagem conta como um produto separado. Marcas diferentes do mesmo produto e tamanho normalmente contam como o mesmo; se não, junte em “É o mesmo produto”.",

    // Juntar produtos
    juntarTitulo: "É o mesmo produto?",
    juntarExplicacao: "Se o mesmo produto aparece com nomes diferentes (ex.: “Leite UHT Integral” e “Leite integral 1L”), junte para ver todos os preços no mesmo lugar. Você pode desfazer depois.",
    juntarAbrir: "Juntar com outro produto",
    juntarFechar: "Cancelar",
    juntarPesquisa: "Buscar o outro produto",
    juntarEscolher: "Escolha o produto que é igual a “{nome}”",
    juntarSemOutros: "Não encontramos outros produtos. Tente outra palavra.",
    juntarBotao: "Juntar",
    juntarConfirmar: "Juntar “{origem}” a “{destino}”? Os preços de “{origem}” passam a aparecer aqui. Você pode desfazer.",
    juntarSim: "Sim, juntar",
    juntarNao: "Não",
    aJuntar: "Juntando...",
    juntado: "Pronto: “{origem}” passa a contar como “{destino}”.",
    juntadosAqui: "Produtos juntados a este",
    juntadosTitulo: "Produtos juntados ({n})",
    juntadosExplicacao: "Os produtos que você juntou por serem o mesmo. Desfaça uma junção se tiver se enganado.",
    juntadosErro: "Não foi possível carregar os produtos juntados.",
    juntadoEm: "Juntado em {data}",
    rotuloJuncao: "{origem} passa a contar como {destino}",
    desfazer: "Desfazer",
    desfazerRotulo: "Desfazer a junção de {nome}",
    desfazerConfirmar: "Desfazer a junção? “{origem}” volta a ser um produto separado de “{destino}”.",
    desfazerSim: "Sim, desfazer",
    aDesfazer: "Desfazendo...",
    desfeito: "Junção desfeita: “{nome}” volta a ser um produto separado.",
    erroJuntar: "Não foi possível juntar os produtos. Tente de novo.",
    erroDesfazer: "Não foi possível desfazer a junção. Tente de novo.",

    // No Free, antes de pedir à API (a API devolve o mesmo texto no 402).
    soPlanosPagos: "Comparar preços entre as lojas onde você comprou está disponível nos planos Essencial e Completo.",
  },

  // "1,09 €/kg": o sufixo vai a seguir ao preço já formatado (precoUnitario em compras/formatosPrecos.ts).
  SUFIXO_UNIDADE: { un: "/un", kg: "/kg", l: "/l" } as Record<string, string>,

  // Para o título de cada unidade: "Preço por unidade", "Preço por kg", "Preço por litro".
  NOME_UNIDADE: { un: "por unidade", kg: "por kg", l: "por litro" } as Record<string, string>,
};

export const DICIONARIO_PRECOS_LOJAS: Dicionario<TextosPrecosLojas> = { PT, BR };
