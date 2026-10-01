"""IBGE — população estimada por UF (API SIDRA, tabela 6579), para indicadores per capita."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .base import Extractor

SIDRA = "https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/9324/p/{ano}"

# código IBGE da UF → sigla
COD_UF = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO", 21: "MA", 22: "PI",
    23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA", 31: "MG", 32: "ES",
    33: "RJ", 35: "SP", 41: "PR", 42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF",
}
REGIAO = {
    "Norte": ["RO", "AC", "AM", "RR", "PA", "AP", "TO"],
    "Nordeste": ["MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA"],
    "Sudeste": ["MG", "ES", "RJ", "SP"],
    "Sul": ["PR", "SC", "RS"],
    "Centro-Oeste": ["MS", "MT", "GO", "DF"],
}
UF_REGIAO = {uf: reg for reg, ufs in REGIAO.items() for uf in ufs}


class IbgeExtractor(Extractor):
    fonte = "ibge_sidra"

    def extract(self, ano: int = 2021, forcar: bool = False, **kwargs) -> Path:
        return self.baixar(SIDRA.format(ano=ano), f"ibge_populacao_{ano}.json", forcar)

    @staticmethod
    def para_dataframe(caminho: Path) -> pd.DataFrame:
        """SIDRA devolve lista de dicts; a 1ª linha é o cabeçalho."""
        linhas = json.loads(Path(caminho).read_text(encoding="utf-8"))[1:]
        df = pd.DataFrame(
            {"cod_uf": [int(r["D1C"]) for r in linhas], "populacao": [int(r["V"]) for r in linhas]}
        )
        df["uf"] = df["cod_uf"].map(COD_UF)
        df["regiao"] = df["uf"].map(UF_REGIAO)
        return df[["uf", "regiao", "populacao"]]
