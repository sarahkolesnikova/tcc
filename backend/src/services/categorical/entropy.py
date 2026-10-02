"""Entropia por linha: surpresa média dos valores da linha, normalizada pela entropia da coluna."""
import numpy as np

from ..base import Detector, DetectorResult, flag_top
from ._util import frequencias


class EntropyDetector(Detector):
    id = "entropy"
    name = "Entropia por Linha"
    kind = "categorical"
    description = "Informação (−log₂ p) média dos valores da linha relativa à entropia de cada coluna (Shannon)."

    def _detect(self, X, contamination):
        F = frequencias(X)
        surpresa = -np.log2(F)
        H = np.array([-(p * np.log2(p)).sum() for p in (X[c].value_counts(normalize=True).to_numpy() for c in X.columns)])
        validas = H > 0
        if not validas.any():
            n = len(X)
            return DetectorResult(self.id, np.zeros(n), np.zeros(n, bool), [None] * n)
        rel = surpresa[:, validas] / H[validas]
        scores = rel.mean(axis=1)
        flags, thr = flag_top(scores, contamination)
        cols = X.columns[validas]
        jmax = rel.argmax(axis=1)
        reasons = [f"surpresa média {scores[i]:.2f}× a entropia das colunas; maior em '{cols[j]}' = "
                   f"'{X.at[X.index[i], cols[j]]}' ({surpresa[i, list(X.columns).index(cols[j])]:.1f} bits)"
                   if flags[i] else None for i, j in enumerate(jmax)]
        return DetectorResult(self.id, scores, flags, reasons, thr, {})
