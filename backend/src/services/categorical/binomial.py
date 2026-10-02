"""Teste binomial: a categoria é significativamente mais rara do que uma categoria "normal" seria?

Hipótese nula: a proporção da categoria é p₀ = min(contaminação, 1/K). Comparar só com a
uniforme (1/K) sinaliza qualquer categoria apenas desbalanceada (ex.: 20% contra 25%);
limitar p₀ pela contaminação faz o teste perguntar o que interessa: "esta categoria é rara
a ponto de ser anomalia?". Com K grande e categorias equilibradas, p₀ = 1/K e nada é sinalizado.
"""
import numpy as np
from scipy.stats import binom

from ..base import Detector, DetectorResult, alpha_por_coluna


class BinomialDetector(Detector):
    id = "binomial"
    name = "Teste Binomial"
    kind = "categorical"
    description = "P(X ≤ k) com X ~ Binomial(n, p₀), p₀ = min(contaminação, 1/K); categorias raras demais para o acaso."

    def _detect(self, X, contamination):
        n, p = X.shape
        alpha = alpha_por_coluna(contamination, p)
        P = np.ones((n, p))
        for j, c in enumerate(X.columns):
            vc = X[c].value_counts()
            K = len(vc)
            if K < 2:
                continue
            p0 = min(contamination, 1.0 / K)
            pv = binom.cdf(vc.to_numpy(), n, p0)
            P[:, j] = X[c].map(dict(zip(vc.index, pv))).to_numpy(float)
        pmin = P.min(axis=1)
        scores = -np.log10(np.clip(pmin, 1e-300, 1))
        flags = pmin < alpha
        jmin = P.argmin(axis=1)
        reasons = [f"'{X.columns[j]}' = '{X.iat[i, j]}' é rara demais para o acaso (p = {pmin[i]:.2g} < {alpha:.2g})"
                   if flags[i] else None for i, j in enumerate(jmin)]
        return DetectorResult(self.id, scores, flags, reasons, alpha, {"alpha_coluna": alpha})
