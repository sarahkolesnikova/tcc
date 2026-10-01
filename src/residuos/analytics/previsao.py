"""Previsão de série anual curta: tendência linear com intervalo de predição.

Séries de resíduos no Brasil têm 5 a 15 pontos anuais. Modelos complexos (Prophet,
ARIMA) superajustam com tão pouco dado; a regressão linear com intervalo honesto é
o baseline correto, e qualquer modelo novo precisa bater este no backtest.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# quantil t de Student bicaudal 95% para gl = 1..30 (evita dependência do scipy)
_T95 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179,
        2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064,
        2.060, 2.056, 2.052, 2.048, 2.045, 2.042]


@dataclass
class Previsao:
    tabela: pd.DataFrame  # ano, valor, previsto, li, ls, tipo
    inclinacao: float
    r2: float
    mape_backtest: float | None


def prever_linear(anos, valores, ate: int, nivel_t: float | None = None) -> Previsao:
    x = np.asarray(anos, dtype=float)
    y = np.asarray(valores, dtype=float)
    if len(x) < 3:
        raise ValueError("São necessários pelo menos 3 anos para prever.")
    b, a = np.polyfit(x, y, 1)
    ajuste = a + b * x
    resid = y - ajuste
    n = len(x)
    s = np.sqrt((resid ** 2).sum() / (n - 2))
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - (resid ** 2).sum() / ss_tot if ss_tot else 1.0
    t = nivel_t or _T95[min(n - 2, 30) - 1]

    futuros = np.arange(int(x.max()) + 1, ate + 1, dtype=float)
    xf = np.concatenate([x, futuros])
    yhat = a + b * xf
    se = s * np.sqrt(1 + 1 / n + (xf - x.mean()) ** 2 / ((x - x.mean()) ** 2).sum())
    tab = pd.DataFrame({
        "ano": xf.astype(int),
        "valor": np.concatenate([y, np.full(len(futuros), np.nan)]),
        "previsto": yhat, "li": yhat - t * se, "ls": yhat + t * se,
        "tipo": ["observado"] * n + ["previsto"] * len(futuros),
    })
    return Previsao(tab, float(b), float(r2), backtest_mape(x, y))


def backtest_mape(x: np.ndarray, y: np.ndarray, min_treino: int = 3) -> float | None:
    """Janela expansiva: treina até t-1, prevê t. MAPE médio dos passos."""
    erros = []
    for i in range(min_treino, len(x)):
        b, a = np.polyfit(x[:i], y[:i], 1)
        if y[i]:
            erros.append(abs((a + b * x[i]) - y[i]) / abs(y[i]))
    return float(np.mean(erros)) if erros else None
