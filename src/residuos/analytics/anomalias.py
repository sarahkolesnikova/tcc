"""Anomalias em declarações de massa: z-score robusto (mediana/MAD) em escala log por categoria.

Massa de resíduo tem cauda longa (uma siderúrgica declara 10⁶ t, uma clínica 0,1 t).
Z-score comum com média/desvio é dominado pelos extremos; em log + MAD a medida é
estável e acha erros típicos de digitação (kg declarado como t, vírgula perdida).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def zscore_robusto(serie: pd.Series) -> pd.Series:
    v = np.log10(serie.clip(lower=1e-6))
    med = v.median()
    mad = (v - med).abs().median()
    if not mad or np.isnan(mad):
        return pd.Series(0.0, index=serie.index)
    return 0.6745 * (v - med) / mad


def detectar(df: pd.DataFrame, grupo: str = "cat_id", coluna: str = "massa_t",
             limiar: float = 3.5, min_grupo: int = 8) -> pd.DataFrame:
    """Devolve as linhas anômalas com o z robusto. Grupos pequenos são ignorados."""
    base = df[df[coluna] > 0].copy()
    tam = base.groupby(grupo)[coluna].transform("size")
    base = base[tam >= min_grupo]
    if base.empty:
        return base.assign(z_robusto=pd.Series(dtype=float))
    base["z_robusto"] = base.groupby(grupo)[coluna].transform(zscore_robusto)
    return base[base["z_robusto"].abs() > limiar].sort_values("z_robusto", key=abs, ascending=False)
