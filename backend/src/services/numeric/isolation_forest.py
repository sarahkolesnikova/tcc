"""Isolation Forest (Liu, Ting e Zhou, 2008)."""
from sklearn.ensemble import IsolationForest

from ..base import Detector, DetectorResult, motivo_maior_desvio, padronizar


class IsolationForestDetector(Detector):
    id = "isolation_forest"
    name = "Isolation Forest"
    kind = "numeric"
    description = "Árvores aleatórias isolam pontos raros em poucas divisões; não assume distribuição."

    def __init__(self, random_state: int = 42, n_estimators: int = 200):
        self.random_state = random_state
        self.n_estimators = n_estimators

    def _detect(self, X, contamination):
        Z = padronizar(X)
        model = IsolationForest(n_estimators=self.n_estimators, contamination=contamination,
                                random_state=self.random_state)
        pred = model.fit_predict(Z)
        scores = -model.score_samples(Z)
        flags = pred == -1
        reasons = [motivo_maior_desvio(X, Z, i, f"isolado com profundidade média baixa (score {scores[i]:.3f}); ")
                   if flags[i] else None for i in range(len(Z))]
        return DetectorResult(self.id, scores, flags, reasons, float(-model.offset_),
                              {"n_estimators": self.n_estimators, "random_state": self.random_state})
