"""Perfis de destinação por UF (ou município): k-means sobre a participação de cada destino.

Implementação em numpy com k-means++ e várias inicializações, para não exigir scikit-learn.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ResultadoCluster:
    rotulos: pd.Series          # índice = entidade, valor = cluster
    centroides: pd.DataFrame    # cluster × destinação (participação média)
    inercia: float


def matriz_perfil(df: pd.DataFrame, entidade: str = "uf", destino: str = "destinacao",
                  massa: str = "massa_t") -> pd.DataFrame:
    """Linhas = entidade; colunas = fração da massa em cada destinação (soma 1)."""
    df = df.assign(**{massa: df[massa].astype(float)})
    piv = df.pivot_table(index=entidade, columns=destino, values=massa, aggfunc="sum", fill_value=0.0)
    piv = piv[piv.sum(axis=1) > 0]
    return piv.div(piv.sum(axis=1), axis=0)


def _kmeans_pp(X: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    c = [X[rng.integers(len(X))]]
    for _ in range(1, k):
        d2 = np.min(((X[:, None, :] - np.array(c)[None]) ** 2).sum(-1), axis=1)
        p = d2 / d2.sum() if d2.sum() else np.full(len(X), 1 / len(X))
        c.append(X[rng.choice(len(X), p=p)])
    return np.array(c)


def kmeans(perfil: pd.DataFrame, k: int = 3, n_init: int = 10, max_iter: int = 100,
           seed: int = 42) -> ResultadoCluster:
    X = perfil.to_numpy(dtype=float)
    k = min(k, len(X))
    rng = np.random.default_rng(seed)
    melhor = None
    for _ in range(n_init):
        C = _kmeans_pp(X, k, rng)
        for _ in range(max_iter):
            lab = (((X[:, None, :] - C[None]) ** 2).sum(-1)).argmin(1)
            novo = np.array([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
            if np.allclose(novo, C):
                break
            C = novo
        inercia = float(((X - C[lab]) ** 2).sum())
        if melhor is None or inercia < melhor[2]:
            melhor = (lab, C, inercia)
    lab, C, inercia = melhor
    # rótulos estáveis: cluster 0 = maior fração inadequada média
    inad = [c for c in perfil.columns if c in ("Lixão", "Aterro controlado")]
    ordem = np.argsort(-C[:, [perfil.columns.get_loc(c) for c in inad]].sum(1)) if inad else np.arange(k)
    remap = {old: new for new, old in enumerate(ordem)}
    return ResultadoCluster(
        pd.Series([remap[x] for x in lab], index=perfil.index, name="cluster"),
        pd.DataFrame(C[ordem], columns=perfil.columns),
        inercia,
    )
