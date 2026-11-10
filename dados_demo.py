"""Dados inventados da conta de demonstração (para recrutadores): movimentações, talões, orçamentos e objetivos.

Tudo é inventado: lojas, empresas e valores são fictícios. As datas são relativas ao mês de hoje
(o mês atual e os 5 anteriores), para o dashboard ter sempre meses recentes com dados.
Quem grava estes dados na base de dados é o demo.py (sempre com o DEMO_USER_ID da configuração).
"""

from datetime import date

# Meses com dados: o atual e os 5 anteriores.
MESES_COM_DADOS = 6

# Pequena variação dos gastos de mês para mês (do mês atual para trás), para os gráficos não ficarem iguais.
VARIACAO_POR_MES = [1.0, 0.92, 1.08, 0.97, 1.05, 0.95]

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
]

# Transferências com o nome de uma pessoa, só no mês atual: (dia, descrição, valor, categoria, método).
# Servem para o chat mostrar a procura por pessoa ("quanto mandei à Rita?"). Entram depois de todas as
# outras, para não mudar a impressão digital (hash) das que já existiam.
TRANSFERENCIAS_DO_MES_ATUAL = [
    (3, "MB WAY para Rita", -25.00, "transferências", "mbway"),
    (7, "MB WAY de Rita", 12.50, "transferências", "mbway"),
]

# Talões (Minhas compras): (meses atrás, dia, loja, categoria, método, itens como (descrição, quantidade, preço da linha)).
# O total do talão é a soma das linhas, como no POST /compras.
TALOES = [
    (
        1,
        18,
        "Supermercado Bom Preço",
        "alimentação",
        "cartao_debito",
        [
            ("Leite meio-gordo 1 L", 6, 5.34),
            ("Pão de forma", 1, 1.49),
            ("Maçãs 1 kg", 1, 1.99),
            ("Arroz agulha 1 kg", 2, 2.38),
            ("Iogurtes naturais", 1, 2.15),
        ],
    ),
    (
        2,
        24,
        "Drogaria Central",
        "casa",
        "dinheiro",
        [
            ("Detergente da roupa", 1, 6.99),
            ("Esponjas", 1, 1.20),
            ("Papel de cozinha", 2, 3.10),
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
# semana seguinte. v2 (2026-11-10): transferências da Rita.
VERSAO_DADOS = 2


def hash_da_marca(hoje: date) -> str:
    """A impressão digital da movimentação que marca a reposição da semana: "demo-2026-W46-v2-marca"."""
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


def total_do_talao(itens: list[tuple[str, float, float]]) -> float:
    return round(sum(preco for _, _, preco in itens), 2)


def hash_do_talao(hoje: date, indice: int) -> str:
    return prefixo_hash(hoje) + f"talao-{indice}"


def transacoes_demo(hoje: date) -> list[dict]:
    """As movimentações inventadas dos últimos 6 meses (sem a marca e sem user_id), cada uma com o seu hash."""
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
    """Os talões inventados (sem user_id nem ids): a loja, a data, o total, o hash da transação e os itens."""
    compras = []
    for indice, (atras, dia, loja, _categoria, _metodo, itens) in enumerate(TALOES):
        compras.append(
            {
                "loja": loja,
                "data": mes_de(hoje, atras).replace(day=dia).isoformat(),
                "total": total_do_talao(itens),
                "hash_transacao": hash_do_talao(hoje, indice),
                "itens": [
                    {"descricao": descricao, "quantidade": quantidade, "preco": preco}
                    for descricao, quantidade, preco in itens
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
