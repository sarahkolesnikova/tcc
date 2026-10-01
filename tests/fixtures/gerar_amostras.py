"""Gera as amostras SINTÉTICAS usadas nos testes (determinísticas, seed fixa).

Imitam o formato dos arquivos oficiais — Latin-1, separador ';', vírgula decimal,
unidades mistas t/kg — mas os valores são inventados. Rode de novo com:
    python tests/fixtures/gerar_amostras.py
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

AQUI = Path(__file__).parent

DESCRICOES = [
    ("Resíduos de concreto, argamassa e tijolos - Classe A", 40, 900),
    ("Madeira, gesso e plásticos de obra - Classe B", 5, 300),
    ("Resíduos para os quais não há reciclagem ou recuperação - Classe C", 1, 60),
    ("Tintas e solventes de obra - Classe D", 0.2, 8),
    ("Sucata de aço e alumínio", 5, 400),
    ("Papel e papelão ondulado", 3, 150),
    ("Resíduos orgânicos de alimentos", 10, 500),
    ("Cacos de vidro", 1, 60),
    ("Embalagens PET e plástico filme", 2, 120),
    ("Rejeitos diversos (outros)", 5, 200),
    ("Resíduos infectantes - Grupo A", 0.1, 12),
    ("Medicamentos vencidos - produtos químicos - Grupo B", 0.05, 3),
    ("Perfurocortantes - Grupo E", 0.02, 1.5),
    ("Lodo de ETE - tratamento de esgoto", 20, 800),
    ("Lodo de ETA - tratamento de água", 10, 300),
    ("Resíduos de portos", 3, 90),
    ("Resíduos de aeroportos", 2, 70),
    ("Equipamentos eletroeletrônicos descartados", 0.5, 40),
    ("Pilhas e baterias", 0.05, 4),
]
DESTINOS = ["Aterro sanitário", "Disposição Final em Lixão", "Reciclagem", "Compostagem",
            "Coprocessamento", "Incineração", "Aterro controlado",
            "Tratamento com aproveitamento energético"]
UFS = ["SP", "MG", "RJ", "BA", "PR", "PE", "PA", "GO", "AM", "RS"]


def rapp_destinador(n: int = 600, seed: int = 7) -> Path:
    rnd = random.Random(seed)
    caminho = AQUI / "rapp_destinador_amostra.csv"
    with open(caminho, "w", encoding="latin-1", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ID Gerador", "UF", "Município", "Ano da destinação", "Descrição do resíduo",
                    "Quantidade", "Unidade", "Tipo de destinação"])
        for i in range(n):
            desc, lo, hi = rnd.choice(DESCRICOES)
            massa = rnd.uniform(lo, hi)
            unidade = "t"
            if rnd.random() < 0.15:          # parte declarada em kg
                massa, unidade = massa * 1000, "kg"
            destino = rnd.choice(DESTINOS)
            if "orgânicos" in desc and rnd.random() < 0.5:
                destino = "Compostagem"
            w.writerow([f"G{i % 120:04d}", rnd.choice(UFS), "Município exemplo",
                        rnd.choice([2021, 2022, 2023, 2024]), desc,
                        f"{massa:.3f}".replace(".", ","), unidade, destino])
        # anomalia plantada: kg declarado como tonelada (1000× acima do normal)
        w.writerow(["G9999", "SP", "Município exemplo", 2024, "Cacos de vidro",
                    "45000,000", "t", "Reciclagem"])
    return caminho


def sinir_municipal() -> Path:
    """Formato da planilha 'Municipal - Diagnóstico' do SINIR (UTF-8, vírgula)."""
    caminho = AQUI / "sinir_municipal_amostra.csv"
    linhas = [
        ("120,5", "Resíduos reutilizáveis ou recicláveis como agregados - Classe A", "Reciclagem"),
        ("80", "Resíduos reutilizáveis ou recicláveis como agregados - Classe A", "Disposição Final em Aterro Sanitário"),
        ("12,3", "Metal", "Disposição Final em Lixão"),
        ("30", "Papel/papelão", "Reciclagem"),
        ("0,8", "Resíduos perfurocortantes ou escarificantes - Grupo E", "Tratamento com aproveitamento energético"),
        ("210", "Orgânico", "Disposição Final em Aterro Sanitário"),
        ("9", "Vidro", "Disposição Final em Lixão"),
        ("44", "Outros", "Tratamento com aproveitamento energético"),
    ]
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=",")
        w.writerow(["Massa (TON)", "Caracterização - Descrição", "Destinação", "UF"])
        for m, c, d in linhas:
            w.writerow([m, c, d, "MG"])
    return caminho


def ibge_populacao() -> Path:
    """Resposta no formato da API SIDRA (valores aproximados, só para teste)."""
    pop = {35: 46_000_000, 31: 21_300_000, 33: 17_400_000, 29: 14_900_000, 41: 11_500_000,
           26: 9_600_000, 15: 8_700_000, 52: 7_200_000, 13: 4_300_000, 43: 11_400_000}
    dados = [{"D1C": "Unidade da Federação (Código)", "V": "Valor"}]
    dados += [{"D1C": str(k), "V": str(v)} for k, v in pop.items()]
    caminho = AQUI / "ibge_populacao_amostra.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return caminho


if __name__ == "__main__":
    for p in (rapp_destinador(), sinir_municipal(), ibge_populacao()):
        print("gerado", p)
