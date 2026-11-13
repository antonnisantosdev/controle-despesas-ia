"""Dados inventados da conta de demonstração (para recrutadores): movimentações, talões, orçamentos e objetivos.

Tudo é inventado: lojas, empresas e valores são fictícios. As datas são relativas ao mês de hoje
(o mês atual e os 11 anteriores), para o dashboard ter sempre meses recentes com dados.
Quem grava estes dados na base de dados é o demo.py (sempre com o DEMO_USER_ID da configuração).
"""

from datetime import date

# Meses com dados: o atual e os 11 anteriores (um ano, para o resumo anual).
MESES_COM_DADOS = 12

# Pequena variação dos gastos de mês para mês (do mês atual para trás), para os gráficos não ficarem iguais.
# Uma por mês de MESES_COM_DADOS.
VARIACAO_POR_MES = [1.0, 0.92, 1.08, 0.97, 1.05, 0.95, 1.03, 0.9, 1.12, 0.98, 1.06, 0.94]

# Movimentações que se repetem todos os meses: (dia, descrição, valor, categoria, método de pagamento).
# Os valores destas não variam: são assinaturas, renda e contas fixas, que o GET /recorrentes deve encontrar.
FIXAS_DO_MES = [
    (1, "Salario Empresa Ficticia Lda", 1450.00, "rendimento", "transferencia"),
    (1, "Renda Casa Imobiliaria Exemplo", -650.00, "casa", "debito_direto"),
    (2, "Passe Transportes Cidade", -40.00, "transporte", "cartao_debito"),
    (3, "Ginasio Forma Viva", -32.90, "lazer", "debito_direto"),
    (8, "Streaming Ecra Total", -11.99, "lazer", "cartao_credito"),
    (12, "Operadora Rede Lusitana", -24.99, "telecomunicações", "debito_direto"),
]

# Gastos do dia a dia: o valor muda de mês para mês (VARIACAO_POR_MES).
VARIAVEIS_DO_MES = [
    (4, "Supermercado Bom Preco", -62.40, "alimentação", "cartao_debito"),
    (6, "Combustivel Posto da Estrada", -48.00, "transporte", "cartao_debito"),
    (9, "Restaurante O Petisco", -27.50, "restaurantes", "cartao_refeicao"),
    (11, "Mercearia da Esquina", -18.75, "alimentação", "dinheiro"),
    (15, "Eletricidade Energia Verde", -58.30, "casa", "debito_direto"),
    (16, "MB WAY ***000", -15.00, "transferências", "mbway"),  # número mascarado, como nos extratos
    (20, "Pastelaria Doce Lar", -6.40, "restaurantes", "cartao_refeicao"),
    (22, "Levantamento ATM", -40.00, "levantamentos", "cartao_debito"),
    (26, "Supermercado Bom Preco", -71.15, "alimentação", "cartao_debito"),
]

# Gastos que só aparecem em alguns meses: (meses atrás, dia, descrição, valor, categoria, método).
OCASIONAIS = [
    (1, 14, "Farmacia Saude Mais", -14.30, "saúde", "cartao_debito"),
    (2, 19, "Loja Online Casa e Deco", -39.90, "compras", "cartao_credito"),
    (3, 23, "Cinema Sala Estrela", -13.00, "lazer", "cartao_debito"),
    (4, 10, "Livraria Pagina Aberta", -22.50, "compras", "cartao_debito"),
    (5, 21, "Oficina Auto Rapida", -85.00, "transporte", "transferencia"),
    (6, 13, "Clinica Dentaria Sorriso", -60.00, "saúde", "cartao_debito"),
    (7, 5, "Loja de Desporto Ativo", -54.90, "compras", "cartao_credito"),
    (8, 17, "Hotel Praia Serena", -210.00, "lazer", "cartao_credito"),
    (9, 27, "Seguro Auto Exemplo", -180.00, "transporte", "debito_direto"),
    (10, 8, "Loja de Eletrodomesticos Casa Nova", -129.00, "compras", "cartao_debito"),
    (11, 12, "Oculista Visao Clara", -95.00, "saúde", "cartao_debito"),
]

# Transferências com o nome de uma pessoa, só no mês atual: (dia, descrição, valor, categoria, método).
# Servem para o chat mostrar a procura por pessoa ("quanto mandei à Rita?"). Entram depois de todas as
# outras, para não mudar a impressão digital (hash) das que já existiam.
TRANSFERENCIAS_DO_MES_ATUAL = [
    (3, "MB WAY para Rita", -25.00, "transferências", "mbway"),
    (7, "MB WAY de Rita", 12.50, "transferências", "mbway"),
]

# Talões (Minhas compras): (meses atrás, dia, loja, categoria, método, itens).
# Cada item: (descrição como no talão, quantidade, preço da linha, nome genérico, unidade).
# O total do talão é a soma das linhas, como no POST /compras. Os mesmos produtos aparecem em 3 lojas
# (inventadas), para a página de preços por loja ter comparações. Novos talões entram sempre no fim
# (o hash da transação de cada talão é a posição na lista).
TALOES = [
    (
        1,
        18,
        "Supermercado Bom Preço",
        "alimentação",
        "cartao_debito",
        [
            ("Leite meio-gordo 1 L", 6, 5.34, "leite meio gordo 1 l", "un"),
            ("Pão de forma 500 g", 1, 1.49, "pão de forma 500 g", "un"),
            ("Maçãs 1 kg", 1, 1.99, "maçãs 1 kg", "un"),
            ("Arroz agulha 1 kg", 2, 2.38, "arroz agulha 1 kg", "un"),
            ("Iogurtes naturais 4x125 g", 1, 2.15, "iogurtes naturais 4x125 g", "un"),
        ],
    ),
    (
        2,
        24,
        "Drogaria Central",
        "casa",
        "dinheiro",
        [
            ("Detergente da roupa", 1, 6.99, "detergente da roupa", "un"),
            ("Esponjas", 1, 1.20, "esponjas", "un"),
            ("Papel de cozinha", 2, 3.10, "papel de cozinha", "un"),
        ],
    ),
    (
        2,
        9,
        "Mercearia da Esquina",
        "alimentação",
        "dinheiro",
        [
            ("LEITE UHT M/G 1L", 2, 1.98, "leite meio gordo 1 l", "un"),
            ("PAO FORMA 500G", 1, 1.65, "pão de forma 500 g", "un"),
            ("BANANA KG", 1.15, 1.49, "banana", "kg"),
            ("OVOS CLASSE M 12UN", 1, 2.89, "ovos 12 un", "un"),
        ],
    ),
    (
        3,
        14,
        "Hipermercado Cesto Cheio",
        "alimentação",
        "cartao_debito",
        [
            ("LEITE M/GORDO CESTO 1L", 6, 4.98, "leite meio gordo 1 l", "un"),
            ("LEITE M/GORDO CESTO 1,5L", 2, 2.38, "leite meio gordo 1,5 l", "un"),
            ("ARROZ AGULHA 1KG", 2, 2.18, "arroz agulha 1 kg", "un"),
            ("BANANA", 0.98, 1.17, "banana", "kg"),
            ("IOG NAT 4X125G", 1, 1.99, "iogurtes naturais 4x125 g", "un"),
            ("OVOS M 12UN", 1, 2.59, "ovos 12 un", "un"),
            ("AZEITE VIRG EXTRA 0,75L", 1, 6.49, "azeite virgem extra 750 ml", "un"),
        ],
    ),
    (
        1,
        27,
        "Hipermercado Cesto Cheio",
        "alimentação",
        "cartao_debito",
        [
            ("LEITE M/GORDO CESTO 1L", 6, 5.10, "leite meio gordo 1 l", "un"),
            ("PAO DE FORMA 500G", 1, 1.39, "pão de forma 500 g", "un"),
            ("AZEITE VIRG EXTRA 0,75L", 1, 6.79, "azeite virgem extra 750 ml", "un"),
            ("BANANA", 1.21, 1.45, "banana", "kg"),
        ],
    ),
    (
        4,
        6,
        "Supermercado Bom Preço",
        "alimentação",
        "cartao_debito",
        [
            ("Leite meio-gordo 1 L", 6, 5.22, "leite meio gordo 1 l", "un"),
            ("Banana", 1.05, 1.37, "banana", "kg"),
            ("Azeite virgem extra 750 ml", 1, 6.99, "azeite virgem extra 750 ml", "un"),
            ("Ovos classe M 12 un", 1, 2.79, "ovos 12 un", "un"),
        ],
    ),
]

# Orçamentos mensais por categoria (iguais em todos os meses).
ORCAMENTOS = {
    "alimentação": 300.00,
    "restaurantes": 60.00,
    "lazer": 60.00,
    "transporte": 120.00,
    "casa": 750.00,
}

# Objetivos de poupança: (nome, valor alvo, valor poupado, meses até ao prazo).
OBJETIVOS = [
    ("Férias de verão", 1200.00, 450.00, 8),
    ("Fundo de emergência", 3000.00, 900.00, 24),
]

# A movimentação que marca "os dados desta semana já foram repostos" (ver demo.py). É a última a ser gravada.
MARCA = (1, "Juros da conta a ordem", 0.03, "rendimento", "transferencia")


def mes_de(hoje: date, meses_atras: int) -> date:
    """O dia 1 do mês que fica meses_atras antes do mês de hoje (0 = o mês de hoje)."""
    # Conta em "meses absolutos" (ano x 12 + mês) para atravessar a mudança de ano sem casos especiais.
    absoluto = hoje.year * 12 + (hoje.month - 1) - meses_atras
    return date(absoluto // 12, absoluto % 12 + 1, 1)


def semana_iso(hoje: date) -> str:
    """A semana ISO de hoje, como "2026-W46" (o ano é o da semana ISO: 1 de janeiro pode ser da semana 53)."""
    ano, semana, _ = hoje.isocalendar()
    return f"{ano}-W{semana:02d}"


def prefixo_hash(hoje: date) -> str:
    """O início da impressão digital de todas as movimentações da demo desta semana: "demo-2026-W46-"."""
    return f"demo-{semana_iso(hoje)}-"


# Subir quando os dados inventados mudam: a marca muda e a demo volta a ser reposta logo, sem esperar pela
# semana seguinte. v2 (2026-11-10): transferências da Rita. v3 (2026-11-10): 12 meses de dados (resumo anual).
# v4 (2026-11-10): talões com os mesmos produtos em 3 lojas (preço por loja); precisa da sql/018.
# v5 (2026-11-10): o tamanho da embalagem entra no nome genérico (leite 1 l e 1,5 l são produtos diferentes).
VERSAO_DADOS = 5


def hash_da_marca(hoje: date) -> str:
    """A impressão digital da movimentação que marca a reposição da semana: "demo-2026-W46-v3-marca"."""
    return prefixo_hash(hoje) + f"v{VERSAO_DADOS}-marca"


def _linha(dia: date, descricao: str, valor: float, categoria: str, metodo: str, hash_importacao: str) -> dict:
    return {
        "data": dia.isoformat(),
        "descricao": descricao,
        "valor": round(valor, 2),
        "categoria": categoria,
        "metodo_pagamento": metodo,
        "hash_importacao": hash_importacao,
    }


def _ja_aconteceu(dia: date, hoje: date) -> bool:
    """No mês atual só entram os dias que já passaram (nada de movimentações no futuro)."""
    return dia <= hoje


def total_do_talao(itens: list[tuple]) -> float:
    return round(sum(item[2] for item in itens), 2)


def hash_do_talao(hoje: date, indice: int) -> str:
    return prefixo_hash(hoje) + f"talao-{indice}"


def transacoes_demo(hoje: date) -> list[dict]:
    """As movimentações inventadas dos últimos MESES_COM_DADOS meses (sem a marca e sem user_id), cada uma com o seu hash."""
    prefixo = prefixo_hash(hoje)
    linhas: list[dict] = []
    for meses_atras in range(MESES_COM_DADOS):
        inicio = mes_de(hoje, meses_atras)
        variacao = VARIACAO_POR_MES[meses_atras]
        for dia, descricao, valor, categoria, metodo in FIXAS_DO_MES:
            linhas.append((inicio.replace(day=dia), descricao, valor, categoria, metodo))
        for dia, descricao, valor, categoria, metodo in VARIAVEIS_DO_MES:
            linhas.append((inicio.replace(day=dia), descricao, valor * variacao, categoria, metodo))
        for atras, dia, descricao, valor, categoria, metodo in OCASIONAIS:
            if atras == meses_atras:
                linhas.append((inicio.replace(day=dia), descricao, valor, categoria, metodo))
    for dia, descricao, valor, categoria, metodo in TRANSFERENCIAS_DO_MES_ATUAL:
        linhas.append((mes_de(hoje, 0).replace(day=dia), descricao, valor, categoria, metodo))

    transacoes = [
        _linha(dia, descricao, valor, categoria, metodo, f"{prefixo}{indice:03d}")
        for indice, (dia, descricao, valor, categoria, metodo) in enumerate(linhas)
        if _ja_aconteceu(dia, hoje)
    ]

    # A transação de cada talão (como o gravar_compra do compras.py: "Talão: loja", com o total em negativo).
    for indice, (atras, dia, loja, categoria, metodo, itens) in enumerate(TALOES):
        data = mes_de(hoje, atras).replace(day=dia)
        transacoes.append(
            _linha(data, f"Talão: {loja}", -total_do_talao(itens), categoria, metodo, hash_do_talao(hoje, indice))
        )
    return transacoes


def marca_demo(hoje: date) -> dict:
    """A movimentação que marca a reposição da semana (sem user_id). Fica no dia 1 do mês atual."""
    dia, descricao, valor, categoria, metodo = MARCA
    return _linha(mes_de(hoje, 0).replace(day=dia), descricao, valor, categoria, metodo, hash_da_marca(hoje))


def compras_demo(hoje: date) -> list[dict]:
    """Os talões inventados (sem user_id nem ids): a loja, a data, o total, o hash da transação e os itens.

    Os itens vão como o compras.py os grava: com o nome genérico, a chave normalizada e a unidade.
    """
    # Importa-se aqui: o produtos.py usa o models.py, que usa o auth.py, que usa o demo.py e este ficheiro.
    from produtos import chave_do_produto

    compras = []
    for indice, (atras, dia, loja, _categoria, _metodo, itens) in enumerate(TALOES):
        compras.append(
            {
                "loja": loja,
                "data": mes_de(hoje, atras).replace(day=dia).isoformat(),
                "total": total_do_talao(itens),
                "hash_transacao": hash_do_talao(hoje, indice),
                "itens": [
                    {
                        "descricao": descricao,
                        "quantidade": quantidade,
                        "preco": preco,
                        "nome_generico": nome_generico,
                        "produto_chave": chave_do_produto(nome_generico, com_tamanho=unidade == "un"),
                        "unidade": unidade,
                    }
                    for descricao, quantidade, preco, nome_generico, unidade in itens
                ],
            }
        )
    return compras


def orcamentos_demo() -> list[dict]:
    """Os orçamentos inventados (sem user_id)."""
    return [{"categoria": categoria, "limite": limite} for categoria, limite in ORCAMENTOS.items()]


def objetivos_demo(hoje: date) -> list[dict]:
    """Os objetivos de poupança inventados (sem user_id). O prazo é o dia 1 de um mês futuro."""
    return [
        {
            "nome": nome,
            "valor_alvo": alvo,
            "valor_poupado": poupado,
            "data_alvo": mes_de(hoje, -meses).isoformat(),
        }
        for nome, alvo, poupado, meses in OBJETIVOS
    ]


# --- Fazer as minhas compras: o exemplo fixo da demo (sem IA, sem pesquisas, não conta) ---
# Preços INVENTADOS (plausíveis, não são os dos sites) e sem links: a demo nunca mostra preços reais.
# Os achados vão pelo mesmo caminho dos da IA (lista_compras.limpar_itens e calcular_plano).
ORCAMENTO_COMPRAS_DEMO = 40.0
MERCADOS_COMPRAS_DEMO = ["pingo_doce", "auchan"]
LISTA_COMPRAS_DEMO = (
    "carne picada, peito de frango, 2 kg de arroz, 2 kg de feijão, refrigerante, 4 garrafões de 6 L de água sem gás"
)

# (pedido, mercado, produto, preço da embalagem, embalagens). Produto vazio = sem preço nesse mercado.
ACHADOS_COMPRAS_DEMO = [
    ("carne picada", "Pingo Doce", "Carne picada mista 500 g", 3.49, 1),
    ("carne picada", "Auchan", "Carne picada de vaca 500 g", 3.79, 1),
    ("peito de frango", "Pingo Doce", "Peito de frango 1 kg", 6.49, 1),
    ("peito de frango", "Auchan", "Filetes de peito de frango 1 kg", 5.99, 1),
    ("2 kg de arroz", "Pingo Doce", "Arroz agulha 1 kg", 1.19, 2),
    ("2 kg de arroz", "Auchan", "Arroz carolino 1 kg", 1.09, 2),
    ("2 kg de feijão", "Pingo Doce", "Feijão encarnado seco 500 g", 1.29, 4),
    ("2 kg de feijão", "Auchan", "", 0.0, 0),
    ("refrigerante", "Pingo Doce", "Refrigerante de cola 1,5 L", 0.99, 1),
    ("refrigerante", "Auchan", "Refrigerante de laranja 1,5 L", 0.89, 1),
    ("4 garrafões de 6 L de água sem gás", "Pingo Doce", "Água mineral sem gás 6 L", 0.99, 4),
    ("4 garrafões de 6 L de água sem gás", "Auchan", "Água sem gás 6 L", 1.05, 4),
]


def achados_compras_demo() -> list[dict]:
    """Os achados do exemplo, no formato que a IA devolve (ainda por limpar)."""
    return [
        {
            "pedido": pedido,
            "mercado": mercado,
            "encontrado": bool(produto),
            "produto": produto,
            "preco_embalagem": preco,
            "embalagens": embalagens,
            "preco_total": round(preco * embalagens, 2),
            "link": "",
            "nota": "" if produto else "Sem preço neste exemplo.",
        }
        for pedido, mercado, produto, preco, embalagens in ACHADOS_COMPRAS_DEMO
    ]
