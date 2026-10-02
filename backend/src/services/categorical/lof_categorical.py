"""LOF categórico: LOF sobre a codificação one-hot das colunas categóricas."""
import warnings

import numpy as np
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import OneHotEncoder

from ..base import Detector, DetectorResult
from ._util import frequencias


class CategoricalLOFDetector(Detector):
    id = "lof_categorical"
    name = "LOF Categórico"
    kind = "categorical"
    description = ("LOF sobre one-hot das categorias. One-hot em vez de Ordinal Encoding: a codificação ordinal "
                   "inventa uma ordem e distâncias entre categorias que não existem.")

    def _detect(self, X, contamination):
        n = len(X)
        enc = OneHotEncoder(max_categories=50, handle_unknown="infrequent_if_exist", sparse_output=False)
        Z = enc.fit_transform(X.astype(str))
        k = min(max(20, int(np.sqrt(n))), n - 1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # muitas linhas idênticas geram aviso de duplicatas
            lof = LocalOutlierFactor(n_neighbors=k, contamination=contamination)
            pred = lof.fit_predict(Z)
        scores = -lof.negative_outlier_factor_
        flags = pred == -1
        F = frequencias(X)
        jmin = F.argmin(axis=1)
        reasons = [f"combinação de categorias isolada (LOF {scores[i]:.2f}); valor mais raro: "
                   f"'{X.columns[j]}' = '{X.iat[i, j]}' ({F[i, j]:.2%})" if flags[i] else None
                   for i, j in enumerate(jmin)]
        return DetectorResult(self.id, scores, flags, reasons, float(-lof.offset_), {"n_neighbors": k})
