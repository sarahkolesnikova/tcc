"""Percentile Fence: apara as caudas empíricas de cada coluna."""
import numpy as np
from scipy.stats import rankdata

from ..base import Detector, DetectorResult, alpha_por_coluna, fmt


class PercentileFenceDetector(Detector):
    id = "percentile_fence"
    name = "Percentile Fence"
    kind = "numeric"
    description = "Valores abaixo do percentil α/2 ou acima de 1 − α/2 em alguma coluna; sem suposição de forma."

    def _detect(self, X, contamination):
        A = X.to_numpy(dtype=float)
        n, p = A.shape
        a = alpha_por_coluna(contamination, p)
        lo = np.quantile(A, a / 2, axis=0)
        hi = np.quantile(A, 1 - a / 2, axis=0)
        fora = (A < lo) | (A > hi)
        # score contínuo: quão perto da cauda está o posto do valor (0 = mediana, 1 = extremo)
        R = np.column_stack([np.abs(rankdata(A[:, j]) / n - 0.5) * 2 for j in range(p)])
        scores = R.max(axis=1)
        flags = fora.any(axis=1)
        reasons = []
        for i in range(n):
            if not flags[i]:
                reasons.append(None)
                continue
            j = int(np.argmax(np.where(fora[i], R[i], -1)))
            reasons.append(f"'{X.columns[j]}' = {fmt(A[i, j])} fora dos percentis "
                           f"[{a / 2:.2%}; {1 - a / 2:.2%}] = [{fmt(lo[j])}; {fmt(hi[j])}]")
        return DetectorResult(self.id, scores, flags, reasons, a, {"alpha_coluna": a})
