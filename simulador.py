"""Simulador de poupança: quanto junta quem poupa um valor fixo todos os meses, com juros compostos.

São só contas (sem IA). É uma simulação com uma taxa assumida, e não um conselho de investimento.
"""

from models import AnoSimulado


def simular_poupanca(mensal: float, anos: int, taxa_anual: float) -> list[AnoSimulado]:
    """O dinheiro no fim de cada ano, se se poupar `mensal` euros por mês durante `anos` anos.

    taxa_anual é em percentagem (3 = 3% ao ano). Os juros contam-se todos os meses:
    em cada mês, o saldo ganha 1/12 da taxa anual e depois entra a poupança desse mês.
    """
    anos_simulados: list[AnoSimulado] = []
    saldo = 0.0  # com juros
    depositado = 0.0  # só o que entrou
    for ano in range(1, anos + 1):
        for mes in range(1, 13):
            saldo *= 1 + taxa_anual / 100 / 12
            saldo += mensal
            depositado += mensal
        anos_simulados.append(AnoSimulado(ano=ano, depositado=round(depositado, 2), valor=round(saldo, 2)))
    return anos_simulados
