// Textos da página Fazer as minhas compras (/fazer-compras): a pessoa dá o orçamento, escolhe 1 a 3 mercados
// e escreve a lista; a IA procura os preços nos sites oficiais dos mercados e a página mostra o plano.
// {chaves} entre chavetas são trocadas pelo valor certo com preencher() (planos.ts).
// Nos componentes: const { TEXTOS_... } = useTextos(DICIONARIO_FAZER_COMPRAS) (lib/textos.ts).
// Todos os textos são novos: o copywriter revê-os depois. Nenhum texto tem preços ou números inventados
// (os números vêm da API ou dos limites do formulário).

import type { Dicionario, Traducao } from "./textos";

const PT = {
  TEXTOS_FAZER_COMPRAS: {
    menu: "Fazer compras", // TEXTO NOVO (rótulo curto do menu; o título da página continua longo)
    etiquetaTopo: "Plano de compras com IA",
    titulo: "Fazer as minhas compras",
    intro:
      "Diz quanto queres gastar, escolhe até 3 mercados e escreve a tua lista. A IA procura os preços nos sites dos mercados e mostra onde cada produto fica mais barato.",
    contador: "{usadas} de {limite} listas este mês",
    aCarregar: "A carregar...",
    erroCarregar: "Não foi possível carregar os mercados. Confirma a ligação e recarrega a página.",
    semMercados: "De momento não há mercados disponíveis. Tenta mais tarde.",
    indisponivel: "Esta função ainda não está disponível na tua conta.",
    soPagos:
      "Fazer as minhas compras está disponível nos planos Essencial e Completo: dás o orçamento e a lista, e a IA procura os preços nos sites dos mercados por ti.",
    limiteTitulo: "Já usaste as listas deste mês",
    limiteTexto: "O teu plano inclui {limite} listas por mês. Podes fazer novas listas a partir do dia 1.",
    limiteTextoSemNumero: "Já usaste as listas incluídas no teu plano este mês.", // 429 sem o número

    // Formulário
    orcamento: "Orçamento em {moeda}", // {moeda}: euros ou reais
    dicaOrcamento: "Podes escrever 100 ou 100,50.",
    mercados: "Mercados",
    dicaMercados: "Escolhe de 1 a 3.",
    mercadosMaximo: "Já escolheste 3 mercados. Para trocar, desmarca um primeiro.",
    lista: "A tua lista",
    marcadorLista: "2 kg de arroz\n1 L de azeite\n4 garrafões de 6 L de água\n12 ovos",
    dicaLista:
      "Um produto por linha, com a quantidade (ex.: \"2 kg de arroz\", \"4 garrafões de 6 L\"). Assim a IA calcula quantas embalagens precisas.",
    contadorLista: "{n} de {maximo} caracteres",
    envioIA: "A lista e os mercados escolhidos são enviados à Anthropic (EUA) para a IA procurar os preços.",
    botao: "Montar o meu plano",
    botaoAProcurar: "A procurar preços...",

    // Validação no browser, antes de enviar
    erroOrcamentoVazio: "Escreve o orçamento.", // TEXTO NOVO
    erroOrcamentoFormato: "Escreve o orçamento só com números, por exemplo 100 ou 100,50.",
    erroOrcamentoValor: "O orçamento tem de ser maior que zero e no máximo {maximo}.",
    erroMercados: "Escolhe pelo menos 1 mercado.",
    erroListaCurta: "Escreve a tua lista de compras (pelo menos {minimo} caracteres).",
    erroListaLonga: "A lista passa dos {maximo} caracteres. Encurta-a um pouco.",

    // Espera (~50 s)
    aProcurarTitulo: "A procurar preços nos sites dos mercados…",
    aProcurarTexto: "Costuma demorar cerca de um minuto. Deixa esta página aberta.",
    segundos: "{s} s",

    // Erros da API
    erroIA: "A IA não está disponível neste momento. Tenta outra vez daqui a uns minutos.",
    erroGenerico: "Não foi possível montar o plano. Tenta outra vez.",
  } as const,

  TEXTOS_RESULTADO_COMPRAS: {
    titulo: "O teu plano",
    pronto: "Plano pronto. Total: {total}.", // anunciado aos leitores de ecrã
    exemplo: "Exemplo da demo: plano já feito, com preços inventados. Não usa a lista nem o orçamento que escreveste.", // TEXTO NOVO
    total: "Total",
    orcamento: "Orçamento",
    sobram: "Sobram {valor}",
    passa: "Ultrapassa o orçamento em {valor}",
    aviso: "Preços tirados dos sites dos mercados na altura da pesquisa. Podem mudar, ser diferentes na loja ou estar mal lidos pela IA. Confirma antes de comprar.",
    totalMercado: "Total neste mercado",
    umProduto: "1 produto",
    nProdutos: "{n} produtos",
    embalagens: "{n} ×",
    paraPedido: "Para: {pedido}",
    verNoSite: "Ver no site",
    verNoSiteRotulo: "Ver {produto} no site de {mercado} (abre num novo separador)",
    mapa: "Procurar no Google Maps",
    mapaRotulo: "Procurar lojas {mercado} no Google Maps (abre num novo separador)",
    planoVazio:
      "A IA não encontrou preços para nenhum produto da lista. Experimenta outros mercados ou escreve os produtos de outra forma.",
    semPrecoTitulo: "Sem preço encontrado",
    semPrecoTexto: "A IA não encontrou estes produtos nos sites escolhidos. Procura-os na loja.",
    comparacao: "Comparação por produto",
    comparacaoDica: "O preço de cada produto em todos os mercados que escolheste.",
    naoEncontrado: "Não encontrado",
    noPlano: "No plano",
    porEmbalagem: "{preco} por embalagem",
  } as const,
};

export type TextosFazerCompras = Traducao<typeof PT>;

// ===== BR (PT-BR) =====
const BR: TextosFazerCompras = {
  TEXTOS_FAZER_COMPRAS: {
    menu: "Fazer compras", // TEXTO NOVO (rótulo curto do menu)
    etiquetaTopo: "Plano de compras com IA",
    titulo: "Fazer minhas compras",
    intro:
      "Diga quanto quer gastar, escolha até 3 mercados e escreva sua lista. A IA busca os preços nos sites dos mercados e mostra onde cada produto sai mais barato.",
    contador: "{usadas} de {limite} listas este mês",
    aCarregar: "Carregando...",
    erroCarregar: "Não foi possível carregar os mercados. Confira sua conexão e recarregue a página.",
    semMercados: "No momento não há mercados disponíveis. Tente mais tarde.",
    indisponivel: "Esta função ainda não está disponível no Brasil.",
    soPagos:
      "Fazer minhas compras está disponível nos planos Essencial e Completo: você informa o orçamento e a lista, e a IA busca os preços nos sites dos mercados para você.",
    limiteTitulo: "Você já usou as listas deste mês",
    limiteTexto: "Seu plano inclui {limite} listas por mês. Você pode fazer novas listas a partir do dia 1.",
    limiteTextoSemNumero: "Você já usou as listas incluídas no seu plano este mês.", // 429 sem o número

    orcamento: "Orçamento em {moeda}",
    dicaOrcamento: "Você pode escrever 100 ou 100,50.",
    mercados: "Mercados",
    dicaMercados: "Escolha de 1 a 3.",
    mercadosMaximo: "Você já escolheu 3 mercados. Para trocar, desmarque um primeiro.",
    lista: "Sua lista",
    marcadorLista: "2 kg de arroz\n1 L de azeite\n4 galões de 5 L de água\n12 ovos",
    dicaLista:
      "Um produto por linha, com a quantidade (ex.: \"2 kg de arroz\", \"4 galões de 5 L\"). Assim a IA calcula quantas embalagens você precisa.",
    contadorLista: "{n} de {maximo} caracteres",
    envioIA: "A lista e os mercados escolhidos são enviados à Anthropic (EUA) para a IA buscar os preços.",
    botao: "Montar meu plano",
    botaoAProcurar: "Buscando preços...",

    erroOrcamentoVazio: "Digite o orçamento.", // TEXTO NOVO
    erroOrcamentoFormato: "Escreva o orçamento só com números, por exemplo 100 ou 100,50.",
    erroOrcamentoValor: "O orçamento precisa ser maior que zero e no máximo {maximo}.",
    erroMercados: "Escolha pelo menos 1 mercado.",
    erroListaCurta: "Escreva sua lista de compras (pelo menos {minimo} caracteres).",
    erroListaLonga: "A lista passa de {maximo} caracteres. Encurte um pouco.",

    aProcurarTitulo: "Buscando preços nos sites dos mercados…",
    aProcurarTexto: "Costuma levar cerca de um minuto. Deixe esta página aberta.",
    segundos: "{s} s",

    erroIA: "A IA não está disponível no momento. Tente de novo daqui a alguns minutos.",
    erroGenerico: "Não foi possível montar o plano. Tente de novo.",
  },

  TEXTOS_RESULTADO_COMPRAS: {
    titulo: "Seu plano",
    pronto: "Plano pronto. Total: {total}.",
    exemplo: "Exemplo da demo: plano já pronto, com preços inventados. Não usa a lista nem o orçamento que você escreveu.", // TEXTO NOVO
    total: "Total",
    orcamento: "Orçamento",
    sobram: "Sobram {valor}",
    passa: "Passa do orçamento em {valor}",
    aviso: "Preços tirados dos sites dos mercados na hora da busca. Podem mudar, ser diferentes na loja ou ter sido lidos errado pela IA. Confira antes de comprar.",
    totalMercado: "Total neste mercado",
    umProduto: "1 produto",
    nProdutos: "{n} produtos",
    embalagens: "{n} ×",
    paraPedido: "Para: {pedido}",
    verNoSite: "Ver no site",
    verNoSiteRotulo: "Ver {produto} no site de {mercado} (abre em uma nova aba)",
    mapa: "Buscar no Google Maps",
    mapaRotulo: "Buscar lojas {mercado} no Google Maps (abre em uma nova aba)",
    planoVazio:
      "A IA não encontrou preços para nenhum produto da lista. Tente outros mercados ou escreva os produtos de outro jeito.",
    semPrecoTitulo: "Sem preço encontrado",
    semPrecoTexto: "A IA não encontrou estes produtos nos sites escolhidos. Procure na loja.",
    comparacao: "Comparação por produto",
    comparacaoDica: "O preço de cada produto em todos os mercados que você escolheu.",
    naoEncontrado: "Não encontrado",
    noPlano: "No plano",
    porEmbalagem: "{preco} por embalagem",
  },
};

export const DICIONARIO_FAZER_COMPRAS: Dicionario<TextosFazerCompras> = { PT, BR };
