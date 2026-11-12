// Textos da demo para recrutadores (botão no login, faixa no topo da app e avisos). Versão A do copywriter.
// Os textos das respostas da API (bloqueado, indisponivel, limiteEntradas, limiteDemo, limiteResumo, demoCheia) são iguais
// aos do demo.py: o tests/test_demo.py confirma-o. Cada texto numa só linha, entre aspas, para esse teste o ler.
// Fase 1 Brasil, passo 6: dicionário { PT, BR }. Nos componentes: const { TEXTOS_... } = useTextos(DICIONARIO_DEMO)
// (lib/textos.ts), que escolhe pelo país da conta. Fora da app (páginas públicas) é sempre o PT.

import type { Dicionario, Traducao } from "./textos";

const PT = {
  TEXTOS_DEMO: {
    // Botão no login.
    botao: "Ver a demo",
    aEntrar: "A abrir a demo...",
    explicacaoBotao: "Sem registo. Dados inventados: podes ver tudo e fazer perguntas ao chat.",
    erroEntrar: "Não foi possível abrir a demo. Tenta outra vez daqui a um minuto.",
    // 503 do POST /demo: a demo está desligada no servidor.
    indisponivel: "A demo não está disponível de momento. Tenta mais tarde.",
    // 429 do POST /demo: demasiadas entradas do mesmo IP numa hora.
    limiteEntradas: "A demo foi aberta muitas vezes a partir desta rede na última hora. Tenta outra vez mais tarde.",
    // 429 quando a demo tem pedidos de demasiadas redes ao mesmo tempo (MENSAGEM_DEMO_CHEIA no demo.py).
    demoCheia: "A demo está com muitos pedidos neste momento. Tenta outra vez daqui a pouco.",
    // No login, quando o token da demo expirou e não deu para pedir outro.
    sessaoTerminou: "A sessão da demo terminou. Volta à página de entrada e abre a demo outra vez.",

    // Faixa no topo de todas as páginas da app, numa sessão de demo.
    faixa: "Estás na demo: dados inventados, só para ver e conversar com o chat.",
    faixaCriarConta: "Criar conta grátis",

    // 423: a demo tentou mudar alguma coisa (a API recusa tudo o que não seja ver e o chat).
    bloqueado:
      "Isto está desligado na demo. Aqui podes ver os dados e usar o chat. Para usar a app com os teus dados, cria uma conta grátis.",
    // 429 do chat numa sessão de demo: o limite por IP ou os pedidos à IA partilhados da conta de demo.
    limiteDemo:
      "As perguntas ao chat da demo acabaram por hoje. Amanhã há mais, ou cria uma conta grátis para usar o chat com os teus dados.",
    // 429 do resumo do mês numa sessão de demo (limite por hora).
    limiteResumo: "O resumo da demo foi pedido muitas vezes a partir desta rede na última hora. Tenta outra vez mais tarde.",
    // Por cima do chat, numa sessão de demo.
    notaChat: "Na demo podes fazer até 5 perguntas por dia. As respostas usam os dados inventados desta conta.",

    // Junto aos botões de alterar dados, que ficam desligados na demo.
    soLeitura: "Na demo, importar, gravar, apagar, ler talões, juntar produtos e as sugestões da IA estão desligados. Os dados são inventados.",
    botaoDesligado: "Indisponível na demo",
    // No cartão do plano (menu) e na página O meu plano, em vez do contador partilhado e da data.
    planoDemoNome: "Conta de demonstração",
    planoDemoChat: "Até 5 perguntas por dia ao chat",
    // Na página O meu plano, em vez dos botões para pedir acesso ou mudar de plano.
    semMudarPlano: "Esta conta é só para demonstração e é partilhada por todos os visitantes, por isso não muda de plano.",
  },
};

export type TextosDemo = Traducao<typeof PT>;

// ===== BR (PT-BR) =====
// Por agora é uma CÓPIA do PT. COLAR AQUI os textos BR do copywriter, chave a chave: mesmas chaves e
// mesmos {placeholders}. O tipo obriga a ter todas as chaves (o `npx tsc --noEmit` falha se faltar alguma).
// As respostas da API (bloqueado, indisponivel, limiteEntradas, limiteDemo, limiteResumo, demoCheia) apontam para o PT:
// têm de ser iguais ao demo.py (tests/test_demo.py lê este ficheiro) e a demo BR fica para depois.
const BR: TextosDemo = {
  TEXTOS_DEMO: {
    // Botão no login.
    botao: "Ver a demo",
    aEntrar: "A abrir a demo...",
    explicacaoBotao: "Sem registo. Dados inventados: podes ver tudo e fazer perguntas ao chat.",
    erroEntrar: "Não foi possível abrir a demo. Tenta outra vez daqui a um minuto.",
    // 503 do POST /demo: a demo está desligada no servidor.
    indisponivel: PT.TEXTOS_DEMO.indisponivel, // igual à API (demo.py): não traduzir aqui
    // 429 do POST /demo: demasiadas entradas do mesmo IP numa hora.
    limiteEntradas: PT.TEXTOS_DEMO.limiteEntradas, // igual à API (demo.py): não traduzir aqui
    // 429 quando a demo tem pedidos de demasiadas redes ao mesmo tempo (MENSAGEM_DEMO_CHEIA no demo.py).
    demoCheia: PT.TEXTOS_DEMO.demoCheia, // igual à API (demo.py): não traduzir aqui
    // No login, quando o token da demo expirou e não deu para pedir outro.
    sessaoTerminou: "A sessão da demo terminou. Volta à página de entrada e abre a demo outra vez.",

    // Faixa no topo de todas as páginas da app, numa sessão de demo.
    faixa: "Estás na demo: dados inventados, só para ver e conversar com o chat.",
    faixaCriarConta: "Criar conta grátis",

    // 423: a demo tentou mudar alguma coisa (a API recusa tudo o que não seja ver e o chat).
    bloqueado: PT.TEXTOS_DEMO.bloqueado, // igual à API (demo.py): não traduzir aqui
    // 429 do chat numa sessão de demo: o limite por IP ou os pedidos à IA partilhados da conta de demo.
    limiteDemo: PT.TEXTOS_DEMO.limiteDemo, // igual à API (demo.py): não traduzir aqui
    // 429 do resumo do mês numa sessão de demo (limite por hora).
    limiteResumo: PT.TEXTOS_DEMO.limiteResumo, // igual à API (demo.py): não traduzir aqui
    // Por cima do chat, numa sessão de demo.
    notaChat: "Na demo podes fazer até 5 perguntas por dia. As respostas usam os dados inventados desta conta.",

    // Junto aos botões de alterar dados, que ficam desligados na demo.
    soLeitura: "Na demo, importar, gravar, apagar, ler talões, juntar produtos e as sugestões da IA estão desligados. Os dados são inventados.",
    botaoDesligado: "Indisponível na demo",
    // No cartão do plano (menu) e na página O meu plano, em vez do contador partilhado e da data.
    planoDemoNome: "Conta de demonstração",
    planoDemoChat: "Até 5 perguntas por dia ao chat",
    // Na página O meu plano, em vez dos botões para pedir acesso ou mudar de plano.
    semMudarPlano: "Esta conta é só para demonstração e é partilhada por todos os visitantes, por isso não muda de plano.",
  },
};

export const DICIONARIO_DEMO: Dicionario<TextosDemo> = { PT, BR };
