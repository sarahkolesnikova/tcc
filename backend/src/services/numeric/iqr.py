"""IQR (Tukey) com multiplicador ajustado pela contaminação."""
import numpy as np

from ..base import Detector, DetectorResult, fmt, z_critico


class IQRDetector(Detector):
    id = "iqr"
    name = "IQR (Tukey)"
    kind = "numeric"
    description = "Valores fora de [Q1 − m·IQR, Q3 + m·IQR]; robusto à assimetria."

    def _detect(self, X, contamination):
        A = X.to_numpy(dtype=float)
        q1, q3 = np.percentile(A, [25, 75], axis=0)
        iqr = q3 - q1
        sd = A.std(axis=0)
        escala = np.where(iqr > 0, iqr, np.where(sd > 0, sd * 1.349, np.inf))
        # multiplicador equivalente à normal: Q3 + m·IQR = z*  →  m = (z* − 0,6745) / 1,349
        m = max((z_critico(contamination, A.shape[1]) - 0.6745) / 1.349, 0.5)
        dist = np.maximum((q1 - A) / escala, (A - q3) / escala)  # em unidades de IQR além da caixa
        scores = dist.max(axis=1)
        flags = scores > m
        jmax = dist.argmax(axis=1)
        reasons = []
        for i, j in enumerate(jmax):
            if not flags[i]:
                reasons.append(None)
                continue
            lo, hi = q1[j] - m * escala[j], q3[j] + m * escala[j]
            reasons.append(f"'{X.columns[j]}' = {fmt(X.iat[i, j])} fora do intervalo [{fmt(lo)}; {fmt(hi)}] "
                           f"(m = {m:.2f})")
        return DetectorResult(self.id, scores, flags, reasons, m, {"multiplicador": m})
