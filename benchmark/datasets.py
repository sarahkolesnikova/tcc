"""Datasets do benchmark, montados no protocolo do ADBench (Han et al., 2022).

O ADBench transforma datasets de classificação em problemas de detecção de anomalias:
uma classe vira "normal" e outra(s) viram "anomalia", subamostrada(s) para ficarem raras.
Breast Cancer, Wine e Digits vêm do scikit-learn e NÃO são os arquivos do ADBench; são
montados aqui com o mesmo protocolo, que precisa ser descrito no texto do TCC.

| dataset       | normal               | anomalia                    | taxa  |
|---------------|----------------------|-----------------------------|-------|
| breast_cancer | benigno (357)        | maligno, subamostrado → 40  | 10,1% |
| wine          | classes 0 e 1 (130)  | classe 2, subamostrada → 14 | 9,7%  |
| digits        | dígitos 1–9 (1.619)  | dígito 0 (178)              | 9,9%  |
| synthetic_5   | normal correlacionada| 5% (globais + de correlação)| 5,0%  |
| synthetic_2   | normal correlacionada| 2% (globais + de correlação)| 2,0%  |

Os sintéticos têm dois tipos de anomalia de propósito: metade são valores extremos (que
qualquer detector univariado pega) e metade quebram a correlação entre colunas sem ter
nenhum valor extremo isolado (só detectores multivariados pegam).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.datasets import load_breast_cancer, load_digits, load_wine


@dataclass
class Dataset:
    nome: str
    X: pd.DataFrame          # numérico
    y: np.ndarray            # 1 = anomalia
    descricao: str

    @property
    def taxa(self) -> float:
        return float(self.y.mean())

    def categorico(self, bins: int = 10) -> pd.DataFrame:
        """Discretiza cada coluna em `bins` faixas de MESMA LARGURA para os detectores categóricos.

        Faixas de mesma largura preservam a raridade: valores extremos caem em faixas pouco
        povoadas. Quantis fariam o oposto (toda faixa com a mesma frequência), e os detectores
        de frequência ficariam cegos por construção (F1 = 0 na comparação feita no benchmark).
        """
        out = {}
        for c in self.X.columns:
            s = self.X[c]
            if s.nunique() <= bins:
                out[c] = s.astype(str)
            else:
                out[c] = "f" + pd.cut(s, bins, labels=False, duplicates="drop").astype(str)
        return pd.DataFrame(out)


def _subamostrar(X, y_anom, n_anom, rng):
    normais = np.where(~y_anom)[0]
    anom = rng.choice(np.where(y_anom)[0], n_anom, replace=False)
    idx = rng.permutation(np.concatenate([normais, anom]))
    return X.iloc[idx].reset_index(drop=True), y_anom[idx].astype(int)


def breast_cancer(seed: int) -> Dataset:
    d = load_breast_cancer(as_frame=True)
    X, y = _subamostrar(d.data, d.target.to_numpy() == 0, 40, np.random.default_rng(seed))
    return Dataset("breast_cancer", X, y, "Breast Cancer: maligno como anomalia (40 de 397)")


def wine(seed: int) -> Dataset:
    d = load_wine(as_frame=True)
    X, y = _subamostrar(d.data, d.target.to_numpy() == 2, 14, np.random.default_rng(seed))
    return Dataset("wine", X, y, "Wine: classe 2 como anomalia (14 de 144)")


def digits(seed: int) -> Dataset:
    d = load_digits(as_frame=True)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(d.data))
    X = d.data.iloc[idx].reset_index(drop=True)
    return Dataset("digits", X, (d.target.to_numpy()[idx] == 0).astype(int), "Digits: dígito 0 como anomalia (178 de 1.797)")


def sintetico(taxa: float, seed: int, n: int = 2000, p: int = 6) -> Dataset:
    rng = np.random.default_rng(seed)
    n_anom = int(round(taxa * n))
    # covariância com correlação forte entre pares de colunas
    cov = np.full((p, p), 0.0)
    for i in range(p):
        for j in range(p):
            cov[i, j] = 0.8 ** abs(i - j)
    normais = rng.multivariate_normal(np.zeros(p), cov, n - n_anom)
    n_glob = n_anom // 2
    globais = rng.uniform(-6, 6, (n_glob, p))
    globais[np.arange(n_glob), rng.integers(0, p, n_glob)] = rng.choice([-1, 1], n_glob) * rng.uniform(4.5, 7, n_glob)
    # anomalias de correlação: valores marginais comuns (|z| < 2,2) com sinais trocados entre colunas vizinhas
    n_corr = n_anom - n_glob
    corr = rng.multivariate_normal(np.zeros(p), cov, n_corr)
    corr[:, 1::2] *= -1
    corr = np.clip(corr, -2.2, 2.2)
    A = np.vstack([normais, globais, corr])
    y = np.r_[np.zeros(len(normais)), np.ones(n_anom)].astype(int)
    idx = rng.permutation(n)
    X = pd.DataFrame(A[idx], columns=[f"x{i + 1}" for i in range(p)])
    return Dataset(f"synthetic_{int(taxa * 100)}", X, y[idx],
                   f"Sintético {taxa:.0%}: normal correlacionada; metade das anomalias globais, metade de correlação")


def todos(seed: int) -> list[Dataset]:
    return [breast_cancer(seed), wine(seed), digits(seed), sintetico(0.05, seed), sintetico(0.02, seed)]
