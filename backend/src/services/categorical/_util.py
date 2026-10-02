import numpy as np
import pandas as pd


def frequencias(X: pd.DataFrame) -> np.ndarray:
    """Matriz n×p com a frequência relativa do valor de cada célula na sua coluna."""
    n = len(X)
    return np.column_stack([X[c].map(X[c].value_counts() / n).to_numpy(dtype=float) for c in X.columns])


def pares(X: pd.DataFrame, max_pares: int = 300):
    cols = list(X.columns)
    out = [(a, b) for i, a in enumerate(cols) for b in cols[i + 1:]]
    return out[:max_pares]
