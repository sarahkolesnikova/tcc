"""Co-ocorrência de pares: linhas cujos pares de valores raramente aparecem juntos."""
import numpy as np

from ..base import Detector, DetectorResult, flag_top
from ._util import pares


class CooccurrenceDetector(Detector):
    id = "cooccurrence"
    name = "Co-ocorrência de Pares"
    kind = "categorical"
    description = "Frequência conjunta de cada par de valores na linha; pares raros indicam combinações incomuns."
    min_columns = 2  # com menos de duas colunas não há pares: score zero, nenhuma anomalia

    def _detect(self, X, contamination):
        n = len(X)
        P = pares(X)
        S = np.empty((n, len(P)))
        for k, (a, b) in enumerate(P):
            chave = X[a].astype(str) + "\x1f" + X[b].astype(str)
            S[:, k] = chave.map(chave.value_counts() / n).to_numpy(float)
        surpresa = -np.log(S)
        scores = surpresa.mean(axis=1)
        flags, thr = flag_top(scores, contamination)
        jmin = S.argmin(axis=1)
        reasons = []
        for i, j in enumerate(jmin):
            if not flags[i]:
                reasons.append(None)
                continue
            a, b = P[j]
            reasons.append(f"par '{a}' = '{X.at[X.index[i], a]}' e '{b}' = '{X.at[X.index[i], b]}' "
                           f"aparece em só {S[i, j]:.2%} das linhas")
        return DetectorResult(self.id, scores, flags, reasons, thr, {"pares": len(P)})
