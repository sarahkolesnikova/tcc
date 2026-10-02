"""Z-Score com limiar pela normal inversa e correção de Šidák entre colunas."""
import numpy as np

from ..base import Detector, DetectorResult, fmt, z_critico


class ZScoreDetector(Detector):
    id = "zscore"
    name = "Z-Score"
    kind = "numeric"
    description = "Desvios-padrão em relação à média de cada coluna; assume distribuição aproximadamente normal."

    def _detect(self, X, contamination):
        A = X.to_numpy(dtype=float)
        sd = A.std(axis=0)
        sd[sd == 0] = np.inf  # coluna constante não gera anomalia
        Z = (A - A.mean(axis=0)) / sd
        absz = np.abs(Z)
        scores = absz.max(axis=1)
        thr = z_critico(contamination, A.shape[1])
        flags = scores > thr
        jmax = absz.argmax(axis=1)
        reasons = [f"'{X.columns[j]}' = {fmt(X.iat[i, j])} está a {Z[i, j]:+.2f} desvios-padrão da média "
                   f"(limiar ±{thr:.2f})" if flags[i] else None for i, j in enumerate(jmax)]
        return DetectorResult(self.id, scores, flags, reasons, thr, {"z_critico": thr})
