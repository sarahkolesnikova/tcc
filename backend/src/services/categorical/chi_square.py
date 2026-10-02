"""Qui-Quadrado: combinações de categorias muito menos frequentes que o esperado sob independência."""
import numpy as np
import pandas as pd

from ..base import Detector, DetectorResult, flag_top
from ._util import pares


class ChiSquareDetector(Detector):
    id = "chi_square"
    name = "Qui-Quadrado"
    kind = "categorical"
    description = "Resíduo de Pearson (O − E)/√E da combinação de cada par de colunas; combinações raras dado o esperado."

    def _detect(self, X, contamination):
        n = len(X)
        if X.shape[1] == 1:  # uma coluna: compara com a distribuição uniforme
            c = X.columns[0]
            vc = X[c].value_counts()
            E = n / len(vc)
            res = X[c].map((E - vc) / np.sqrt(E)).to_numpy(float)
            scores, onde = res, [(c, None)] * n
        else:
            P = pares(X)
            S = np.empty((n, len(P)))
            for k, (a, b) in enumerate(P):
                obs = pd.crosstab(X[a], X[b])                       # O: frequências observadas
                esp = np.outer(obs.sum(axis=1), obs.sum(axis=0)) / n  # E: esperadas sob independência
                R = (esp - obs.to_numpy()) / np.sqrt(esp)           # positivo = combinação rara
                ia = X[a].map({v: i for i, v in enumerate(obs.index)}).to_numpy()
                ib = X[b].map({v: i for i, v in enumerate(obs.columns)}).to_numpy()
                S[:, k] = R[ia, ib]
            scores = S.max(axis=1)
            onde = [P[j] for j in S.argmax(axis=1)]
        flags, thr = flag_top(scores, contamination)
        reasons = []
        for i in range(n):
            if not flags[i]:
                reasons.append(None)
            elif onde[i][1] is None:
                reasons.append(f"'{onde[i][0]}' = '{X.iat[i, 0]}' bem abaixo da frequência esperada (resíduo {scores[i]:.2f})")
            else:
                a, b = onde[i]
                reasons.append(f"combinação '{a}' = '{X.at[X.index[i], a]}' com '{b}' = '{X.at[X.index[i], b]}' "
                               f"ocorre muito menos que o esperado (resíduo de Pearson {scores[i]:.2f})")
        return DetectorResult(self.id, scores, flags, reasons, thr, {})
