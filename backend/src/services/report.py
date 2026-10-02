"""Geração do relatório: executa os detectores, consolida o consenso e as estatísticas."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import registry
from .base import DetectorResult
from .io import preparar_categorico, preparar_numerico

MAX_LINHAS_RELATORIO = 500
MAX_PONTOS_DISPERSAO = 2000


@dataclass(frozen=True)
class Parametros:
    models: tuple[str, ...]
    numeric_columns: tuple[str, ...]
    categorical_columns: tuple[str, ...]
    threshold: float = 0.05  # contaminação esperada

    def chave(self) -> str:
        return hashlib.sha1(json.dumps(self.__dict__, sort_keys=True, default=list).encode()).hexdigest()[:16]


class ParametrosInvalidos(ValueError):
    pass


def validar(params: Parametros, colunas: list[str]) -> None:
    if not params.models:
        raise ParametrosInvalidos("Selecione ao menos um modelo.")
    desconhecidas = set(params.numeric_columns + params.categorical_columns) - set(colunas)
    if desconhecidas:
        raise ParametrosInvalidos(f"Colunas inexistentes: {sorted(desconhecidas)}")
    if not 0 < params.threshold < 0.5:
        raise ParametrosInvalidos("O threshold de contaminação deve estar entre 0 e 0,5.")
    for m in params.models:
        try:
            det = registry.obter(m)
        except KeyError as e:
            raise ParametrosInvalidos(str(e)) from e
        cols = params.numeric_columns if det.kind == "numeric" else params.categorical_columns
        if not cols:
            tipo = "numérica" if det.kind == "numeric" else "categórica"
            raise ParametrosInvalidos(f"O modelo {det.name} precisa de pelo menos uma coluna {tipo}.")


def executar(df: pd.DataFrame, params: Parametros) -> dict[str, DetectorResult]:
    validar(params, list(df.columns))
    Xn = preparar_numerico(df, list(params.numeric_columns)) if params.numeric_columns else None
    Xc = preparar_categorico(df, list(params.categorical_columns)) if params.categorical_columns else None
    out = {}
    for m in params.models:
        det = registry.obter(m)
        X = Xn if det.kind == "numeric" else Xc
        out[m] = det.run(X, params.threshold)
    return out


def _estatisticas(df: pd.DataFrame, params: Parametros) -> dict:
    est = {"numeric": [], "categorical": []}
    if params.numeric_columns:
        Xn = preparar_numerico(df, list(params.numeric_columns))
        for c in Xn.columns:
            bruto = df[c]
            s = Xn[c]
            q1, med, q3 = s.quantile([0.25, 0.5, 0.75])
            est["numeric"].append({"column": c, "count": int(len(s)), "missing": int(bruto.isna().sum()),
                                   "mean": float(s.mean()), "std": float(s.std(ddof=1)) if len(s) > 1 else 0.0,
                                   "min": float(s.min()), "q1": float(q1), "median": float(med),
                                   "q3": float(q3), "max": float(s.max())})
    if params.categorical_columns:
        Xc = preparar_categorico(df, list(params.categorical_columns))
        for c in Xc.columns:
            vc = Xc[c].value_counts()
            est["categorical"].append({"column": c, "count": int(len(Xc)), "unique": int(len(vc)),
                                       "top": str(vc.index[0]), "top_freq": int(vc.iloc[0]),
                                       "missing": int((Xc[c] == "missing").sum())})
    return est


def _valor_json(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    return v if isinstance(v, (int, float, str, bool)) else str(v)


def votos(resultados: dict[str, DetectorResult], n: int) -> np.ndarray:
    return np.sum([r.flags for r in resultados.values()], axis=0) if resultados else np.zeros(n, int)


def score_consenso(resultados: dict[str, DetectorResult]) -> np.ndarray:
    """Média do posto percentual dos scores (0–1): escalas diferentes viram comparáveis."""
    postos = [pd.Series(r.scores).rank(pct=True).to_numpy() for r in resultados.values()]
    return np.mean(postos, axis=0)


def montar_relatorio(df: pd.DataFrame, params: Parametros, resultados: dict[str, DetectorResult],
                     arquivo: dict) -> dict:
    n = len(df)
    v = votos(resultados, n)
    cons = score_consenso(resultados)
    modelos = []
    for m, r in resultados.items():
        det = registry.obter(m)
        idx = np.where(r.flags)[0]
        ordem = idx[np.argsort(-r.scores[idx])][:MAX_LINHAS_RELATORIO]
        modelos.append({
            "id": m, "name": det.name, "type": det.kind, "anomalies": r.n_flagged,
            "rate": r.n_flagged / n if n else 0.0, "threshold": r.threshold, "params": r.params,
            "elapsed_ms": round(r.elapsed_s * 1000, 2),
            "rows": [{"row": int(i) + 1, "score": float(r.scores[i]), "reason": r.reasons[i]} for i in ordem],
        })
    colunas = list(params.numeric_columns + params.categorical_columns)
    sinalizadas = np.where(v > 0)[0]
    ordem = sinalizadas[np.lexsort((-cons[sinalizadas], -v[sinalizadas]))][:MAX_LINHAS_RELATORIO]
    linhas = []
    for i in ordem:
        motivos = [{"model": registry.obter(m).name, "reason": r.reasons[i]}
                   for m, r in resultados.items() if r.flags[i]]
        linhas.append({"row": int(i) + 1, "votes": int(v[i]), "consensus_score": float(cons[i]),
                       "values": {c: _valor_json(df.at[i, c]) for c in colunas}, "reasons": motivos})
    disp = None
    if len(params.numeric_columns) >= 2:
        Xn = preparar_numerico(df, list(params.numeric_columns[:2]))
        if Xn.shape[1] == 2:
            amostra = np.arange(n) if n <= MAX_PONTOS_DISPERSAO else np.unique(np.concatenate([
                np.random.default_rng(0).choice(n, MAX_PONTOS_DISPERSAO, replace=False), sinalizadas[:500]]))
            disp = {"x": Xn.columns[0], "y": Xn.columns[1],
                    "points": [{"row": int(i) + 1, "x": float(Xn.iat[i, 0]), "y": float(Xn.iat[i, 1]),
                                "votes": int(v[i])} for i in amostra]}
    return {
        "file": arquivo,
        "parameters": {"models": list(params.models), "numeric_columns": list(params.numeric_columns),
                       "categorical_columns": list(params.categorical_columns), "threshold": params.threshold},
        "summary": {"rows": n, "flagged_rows": int((v > 0).sum()),
                    "flagged_by_majority": int((v > len(resultados) / 2).sum()), "models_run": len(resultados)},
        "models": modelos,
        "consensus": linhas,
        "votes_histogram": [{"votes": int(k), "rows": int((v == k).sum())} for k in range(len(resultados) + 1)],
        "statistics": _estatisticas(df, params),
        "scatter": disp,
    }


def tabela_marcada(df: pd.DataFrame, resultados: dict[str, DetectorResult], remover: bool = False) -> pd.DataFrame:
    """Dados originais + uma coluna por modelo, votos e score de consenso."""
    out = df.copy()
    for m, r in resultados.items():
        out[f"anomalia_{m}"] = r.flags.astype(int)
    out["votos"] = votos(resultados, len(df))
    out["score_consenso"] = np.round(score_consenso(resultados), 4)
    if remover:
        out = out[out["votos"] == 0].drop(columns=[c for c in out.columns if c.startswith("anomalia_")] +
                                          ["votos", "score_consenso"])
    return out
