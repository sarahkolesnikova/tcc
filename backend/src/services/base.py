"""Interface padronizada dos detectores.

Todo detector recebe um DataFrame já pré-processado (numérico: float sem NaN;
categórico: str com NaN trocado por "missing") e a taxa de contaminação esperada,
e devolve um `DetectorResult` com:

- `scores`: um valor por linha, maior = mais anômalo (usado para ranking e AUC-ROC);
- `flags`: True para as linhas classificadas como anomalia;
- `reasons`: a explicação textual de cada linha sinalizada (None nas demais).
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd
from scipy.stats import norm

Kind = Literal["numeric", "categorical"]


@dataclass
class DetectorResult:
    model_id: str
    scores: np.ndarray
    flags: np.ndarray
    reasons: list[str | None]
    threshold: float | None = None
    params: dict = field(default_factory=dict)
    elapsed_s: float = 0.0

    @property
    def n_flagged(self) -> int:
        return int(self.flags.sum())


class Detector(ABC):
    id: str
    name: str
    kind: Kind
    description: str
    min_columns: int = 1

    def run(self, X: pd.DataFrame, contamination: float) -> DetectorResult:
        if not 0 < contamination < 0.5:
            raise ValueError("contaminação deve estar entre 0 e 0,5")
        n = len(X)
        t0 = time.perf_counter()
        if n < 3 or X.shape[1] < self.min_columns:
            res = DetectorResult(self.id, np.zeros(n), np.zeros(n, dtype=bool), [None] * n,
                                 params={"aviso": f"requer pelo menos 3 linhas e {self.min_columns} coluna(s)"})
        else:
            res = self._detect(X, contamination)
        res.elapsed_s = time.perf_counter() - t0
        res.scores = np.nan_to_num(np.asarray(res.scores, dtype=float), nan=0.0, posinf=1e12)
        res.flags = np.asarray(res.flags, dtype=bool)
        return res

    @abstractmethod
    def _detect(self, X: pd.DataFrame, contamination: float) -> DetectorResult:
        ...

    def info(self) -> dict:
        return {"id": self.id, "name": self.name, "type": self.kind, "description": self.description}


# ----------------------------------------------------------------------------- utilitários

def alpha_por_coluna(contamination: float, p: int) -> float:
    """Correção de Šidák: taxa por coluna para que a taxa por LINHA fique ≈ contaminação.

    Detectores univariados testam cada coluna e marcam a linha se QUALQUER coluna for
    extrema. Sem correção, com p colunas a taxa por linha vira 1-(1-c)^p (ex.: 30 colunas
    a 5% → 78% das linhas). Com α = 1-(1-c)^(1/p) por coluna, a união volta a ≈ c.
    """
    return 1.0 - (1.0 - contamination) ** (1.0 / max(p, 1))


def z_critico(contamination: float, p: int) -> float:
    return float(norm.ppf(1.0 - alpha_por_coluna(contamination, p) / 2.0))


def flag_top(scores: np.ndarray, contamination: float) -> tuple[np.ndarray, float | None]:
    """Marca as ~c·n linhas de maior score, sem separar linhas empatadas.

    Linhas com o mesmo score recebem o mesmo rótulo. Se o grupo empatado no corte
    levaria a mais que o dobro do esperado (comum em dados categóricos, onde centenas
    de linhas são idênticas), ele fica de fora inteiro. Scores todos iguais → nada.
    """
    s = np.asarray(scores, dtype=float)
    n = len(s)
    if n == 0 or np.allclose(s, s[0]):
        return np.zeros(n, dtype=bool), None
    k = max(1, int(round(contamination * n)))
    thr = float(np.sort(s)[n - k])
    flags = s >= thr
    if flags.sum() > 2 * k:
        flags = s > thr
    return flags, thr


def padronizar(X: pd.DataFrame) -> np.ndarray:
    A = X.to_numpy(dtype=float)
    sd = A.std(axis=0)
    sd[sd == 0] = 1.0
    return (A - A.mean(axis=0)) / sd


def fmt(v) -> str:
    """Número legível para auditor, sem notação científica: inteiros como estão, |v| ≥ 1 com até
    2 casas (1020.4 → "1020.4"), |v| < 1 com 4 algarismos significativos (0.000123 → "0.000123")."""
    if isinstance(v, (float, np.floating)):
        v = float(v)
        if v.is_integer():
            return str(int(v))
        if abs(v) >= 1:
            return f"{v:.2f}".rstrip("0").rstrip(".")
        return np.format_float_positional(v, precision=4, unique=False, fractional=False, trim="-")
    return str(v)


def motivo_maior_desvio(X: pd.DataFrame, Z: np.ndarray, i: int, prefixo: str = "") -> str:
    j = int(np.argmax(np.abs(Z[i])))
    col = X.columns[j]
    return f"{prefixo}maior desvio em '{col}' = {fmt(X.iat[i, j])} ({Z[i, j]:+.2f} desvios-padrão)"
