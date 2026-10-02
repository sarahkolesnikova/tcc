"""Frequência relativa: linhas com algum valor raro na sua coluna."""
import numpy as np

from ..base import Detector, DetectorResult, flag_top
from ._util import frequencias


class FrequencyDetector(Detector):
    id = "frequency"
    name = "Frequência Relativa"
    kind = "categorical"
    description = "Sinaliza linhas cujo valor mais raro tem frequência relativa abaixo do limiar."

    def _detect(self, X, contamination):
        F = frequencias(X)
        fmin = F.min(axis=1)
        scores = -np.log(fmin)
        flags, thr = flag_top(scores, contamination)
        jmin = F.argmin(axis=1)
        reasons = [f"'{X.columns[j]}' = '{X.iat[i, j]}' aparece em só {F[i, j]:.2%} das linhas"
                   if flags[i] else None for i, j in enumerate(jmin)]
        return DetectorResult(self.id, scores, flags, reasons,
                              float(np.exp(-thr)) if thr is not None else None, {})
