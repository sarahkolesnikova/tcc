"""Local Outlier Factor (Breunig et al., 2000)."""
import warnings

from sklearn.neighbors import LocalOutlierFactor

from ..base import Detector, DetectorResult, motivo_maior_desvio, padronizar


class LOFDetector(Detector):
    id = "lof"
    name = "LOF"
    kind = "numeric"
    description = "Compara a densidade local de cada ponto com a dos vizinhos; bom para clusters de densidades distintas."

    def _detect(self, X, contamination):
        Z = padronizar(X)
        n = len(Z)
        k = min(20, n - 1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            lof = LocalOutlierFactor(n_neighbors=k, contamination=contamination)
            pred = lof.fit_predict(Z)
        scores = -lof.negative_outlier_factor_
        flags = pred == -1
        reasons = [motivo_maior_desvio(X, Z, i, f"LOF = {scores[i]:.2f} (densidade {scores[i]:.1f}× menor que a dos vizinhos); ")
                   if flags[i] else None for i in range(n)]
        return DetectorResult(self.id, scores, flags, reasons, float(-lof.offset_), {"n_neighbors": k})
