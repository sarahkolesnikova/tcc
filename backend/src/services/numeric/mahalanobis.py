"""Distância de Mahalanobis com limiar qui-quadrado (p graus de liberdade)."""
import numpy as np
from scipy.stats import chi2

from ..base import Detector, DetectorResult, fmt


class MahalanobisDetector(Detector):
    id = "mahalanobis"
    name = "Distância de Mahalanobis"
    kind = "numeric"
    description = "Distância multivariada que considera a correlação entre colunas; limiar χ²(p)."

    def _detect(self, X, contamination):
        A = X.to_numpy(dtype=float)
        keep = A.std(axis=0) > 0
        A = A[:, keep]
        cols = X.columns[keep]
        if A.shape[1] == 0:
            n = len(X)
            return DetectorResult(self.id, np.zeros(n), np.zeros(n, bool), [None] * n)
        D = A - A.mean(axis=0)
        cov = np.atleast_2d(np.cov(A, rowvar=False))
        inv = np.linalg.pinv(cov)  # pseudo-inversa: funciona com covariância singular
        W = D @ inv
        d2 = np.einsum("ij,ij->i", W, D)
        p = A.shape[1]
        thr = float(chi2.ppf(1 - contamination, p))
        flags = d2 > thr
        contrib = D * W  # decomposição de D² por coluna
        reasons = []
        for i in range(len(A)):
            if not flags[i]:
                reasons.append(None)
                continue
            j = int(np.argmax(contrib[i]))
            share = contrib[i, j] / d2[i] if d2[i] else 0
            reasons.append(f"D² = {d2[i]:.2f} > {thr:.2f}; '{cols[j]}' = {fmt(X.iat[i, list(X.columns).index(cols[j])])} "
                           f"responde por {share:.0%} da distância")
        return DetectorResult(self.id, d2, flags, reasons, thr, {"graus_liberdade": p})
