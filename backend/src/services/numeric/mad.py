"""Modified Z-Score (mediana e MAD), limiar 3,5 de Iglewicz & Hoaglin."""
import numpy as np

from ..base import Detector, DetectorResult, fmt


class MADDetector(Detector):
    id = "mad"
    name = "Modified Z-Score (MAD)"
    kind = "numeric"
    description = "0,6745·|x − mediana|/MAD; limiar 3,5. Robusto a outliers extremos."
    LIMIAR = 3.5

    def _detect(self, X, contamination):
        A = X.to_numpy(dtype=float)
        med = np.median(A, axis=0)
        mad = np.median(np.abs(A - med), axis=0)
        sd = A.std(axis=0)
        # fallback: coluna (quase) constante tem MAD = 0 → usa o desvio-padrão
        M = np.where(mad > 0, 0.6745 * (A - med) / np.where(mad > 0, mad, 1),
                     (A - med) / np.where(sd > 0, sd, np.inf))
        absm = np.abs(M)
        scores = absm.max(axis=1)
        flags = scores > self.LIMIAR
        jmax = absm.argmax(axis=1)
        reasons = [f"'{X.columns[j]}' = {fmt(X.iat[i, j])} tem Z modificado {M[i, j]:+.2f} "
                   f"(mediana {fmt(med[j])}, limiar ±{self.LIMIAR})" if flags[i] else None
                   for i, j in enumerate(jmax)]
        return DetectorResult(self.id, scores, flags, reasons, self.LIMIAR, {"limiar": self.LIMIAR})
