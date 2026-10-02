"""Catálogo dos 14 detectores (8 numéricos + 6 categóricos)."""
from __future__ import annotations

from .base import Detector
from .categorical.binomial import BinomialDetector
from .categorical.chi_square import ChiSquareDetector
from .categorical.cooccurrence import CooccurrenceDetector
from .categorical.entropy import EntropyDetector
from .categorical.frequency import FrequencyDetector
from .categorical.lof_categorical import CategoricalLOFDetector
from .numeric.iqr import IQRDetector
from .numeric.isolation_forest import IsolationForestDetector
from .numeric.knn import KNNDistanceDetector
from .numeric.lof import LOFDetector
from .numeric.mad import MADDetector
from .numeric.mahalanobis import MahalanobisDetector
from .numeric.percentile_fence import PercentileFenceDetector
from .numeric.zscore import ZScoreDetector

DETECTORES: dict[str, Detector] = {d.id: d for d in (
    ZScoreDetector(), IQRDetector(), MADDetector(), MahalanobisDetector(), KNNDistanceDetector(),
    LOFDetector(), IsolationForestDetector(), PercentileFenceDetector(),
    FrequencyDetector(), EntropyDetector(), ChiSquareDetector(), BinomialDetector(),
    CooccurrenceDetector(), CategoricalLOFDetector(),
)}


def listar() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"numeric": [], "categorical": []}
    for d in DETECTORES.values():
        out[d.kind].append(d.info())
    return out


def obter(model_id: str) -> Detector:
    try:
        return DETECTORES[model_id]
    except KeyError:
        raise KeyError(f"detector desconhecido: {model_id}") from None
