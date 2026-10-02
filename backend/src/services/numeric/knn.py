"""Distância média aos k vizinhos mais próximos (k = √n, mínimo 5, máximo n − 1)."""
import numpy as np
from sklearn.neighbors import NearestNeighbors

from ..base import Detector, DetectorResult, flag_top, motivo_maior_desvio, padronizar


class KNNDistanceDetector(Detector):
    id = "knn"
    name = "KNN Distance"
    kind = "numeric"
    description = "Distância média aos k vizinhos mais próximos; pontos em regiões esparsas são anômalos."

    def _detect(self, X, contamination):
        Z = padronizar(X)
        n = len(Z)
        k = min(max(5, int(np.sqrt(n))), n - 1)
        nn = NearestNeighbors(n_neighbors=k + 1).fit(Z)
        dist, _ = nn.kneighbors(Z)
        scores = dist[:, 1:].mean(axis=1)  # descarta a distância a si mesmo
        flags, thr = flag_top(scores, contamination)
        reasons = [motivo_maior_desvio(X, Z, i, f"distância média {scores[i]:.2f} aos {k} vizinhos; ")
                   if flags[i] else None for i in range(n)]
        return DetectorResult(self.id, scores, flags, reasons, thr, {"k": k})
