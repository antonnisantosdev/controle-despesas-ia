// Textos da demo para recrutadores (botão no login, faixa no topo da app e avisos). Versão A do copywriter.
// Os textos das respostas da API (bloqueado, indisponivel, limiteEntradas, limiteDemo, limiteResumo, demoCheia) são iguais
// aos do demo.py: o tests/test_demo.py confirma-o. Cada texto numa só linha, entre aspas, para esse teste o ler.

export const TEXTOS_DEMO = {
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
  soLeitura: "Na demo, importar, gravar, ler talões e as sugestões da IA estão desligados. Os dados são inventados.",
  botaoDesligado: "Indisponível na demo",
  // No cartão do plano (menu) e na página O meu plano, em vez do contador partilhado e da data.
  planoDemoNome: "Conta de demonstração",
  planoDemoChat: "Até 5 perguntas por dia ao chat",
  // Na página O meu plano, em vez dos botões para pedir acesso ou mudar de plano.
  semMudarPlano: "Esta conta é só para demonstração e é partilhada por todos os visitantes, por isso não muda de plano.",
};
