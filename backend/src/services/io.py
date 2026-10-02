"""Leitura de planilhas (CSV, XLSX, XLS) e inferência de tipos das colunas.

`norm`, `to_num` e a detecção de encoding/separador vêm do pipeline do Observatório de
Resíduos, onde foram testados com arquivos públicos brasileiros: Latin-1, separador ';',
vírgula decimal e ponto de milhar ("2.000" = dois mil).
"""
from __future__ import annotations

import io
import re
import unicodedata

import numpy as np
import pandas as pd

EXTENSOES = {".csv", ".xlsx", ".xls"}
MAX_BYTES = 50 * 1024 * 1024


class ArquivoInvalido(ValueError):
    pass


def norm(s: object) -> str:
    if s is None or (isinstance(s, float) and s != s):
        return ""
    txt = unicodedata.normalize("NFD", str(s))
    return "".join(ch for ch in txt if unicodedata.category(ch) != "Mn").lower().strip()


def to_num(v: object) -> float:
    """'1.200,5' → 1200.5; '2.000' → 2000; '1200.5' → 1200.5; inválido → NaN."""
    if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
        return float(v)
    s = str(v if v is not None else "").strip().replace(" ", "").replace(" ", "")
    s = re.sub(r"^R\$", "", s).rstrip("%")
    if not s:
        return float("nan")
    if re.search(r",\d{1,6}$", s) or ("." in s and "," in s):
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _sniff(raw: bytes) -> tuple[str, str]:
    head = raw[:50000]
    try:
        head.decode("utf-8")
        enc = "utf-8-sig"
    except UnicodeDecodeError:
        enc = "latin-1"
    txt = head.decode(enc, errors="ignore")
    linhas = txt.splitlines()[:20]
    contagem = {sep: sum(linha.count(sep) for linha in linhas) for sep in (";", ",", "\t", "|")}
    return enc, max(contagem, key=contagem.get)


def ler_planilha(raw: bytes, nome: str) -> pd.DataFrame:
    if len(raw) > MAX_BYTES:
        raise ArquivoInvalido("Arquivo maior que 50 MB.")
    ext = ("." + nome.rsplit(".", 1)[-1].lower()) if "." in nome else ""
    if ext not in EXTENSOES:
        raise ArquivoInvalido(f"Formato não suportado ({ext or 'sem extensão'}). Use CSV, XLSX ou XLS.")
    try:
        if ext == ".csv":
            enc, sep = _sniff(raw)
            df = pd.read_csv(io.BytesIO(raw), sep=sep, encoding=enc, dtype=str, on_bad_lines="skip")
        else:
            df = pd.read_excel(io.BytesIO(raw), engine="openpyxl" if ext == ".xlsx" else "xlrd", dtype=object)
    except Exception as e:  # noqa: BLE001 - mensagem amigável para qualquer falha de parsing
        raise ArquivoInvalido(f"Não foi possível ler o arquivo: {e}") from e
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all").reset_index(drop=True)
    df.columns = [str(c).strip() or f"coluna_{i + 1}" for i, c in enumerate(df.columns)]
    if df.empty:
        raise ArquivoInvalido("A planilha não tem linhas de dados.")
    return df


def inferir_tipos(df: pd.DataFrame, limiar_numerico: float = 0.9) -> list[dict]:
    """Numérica se ≥ 90% dos valores não vazios viram número; senão categórica."""
    out = []
    for c in df.columns:
        s = df[c]
        nao_vazio = s.dropna()
        nao_vazio = nao_vazio[nao_vazio.astype(str).str.strip() != ""]
        nums = nao_vazio.map(to_num)
        frac = float(nums.notna().mean()) if len(nao_vazio) else 0.0
        tipo = "numeric" if frac >= limiar_numerico and nums.nunique() > 2 else "categorical"
        out.append({"name": c, "type": tipo, "missing": int(len(s) - len(nao_vazio)),
                    "unique": int(nao_vazio.nunique())})
    return out


def preparar_numerico(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Converte para float e imputa a mediana (NaN quebraria os algoritmos do scikit-learn)."""
    X = pd.DataFrame({c: df[c].map(to_num).astype(float) for c in colunas}, index=df.index)
    X = X.loc[:, X.notna().any()]
    return X.fillna(X.median())


def preparar_categorico(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Texto aparado; vazio/NaN vira a categoria especial "missing"."""
    X = pd.DataFrame(index=df.index)
    for c in colunas:
        s = df[c].astype(object).where(df[c].notna(), None)
        X[c] = [("missing" if v is None or str(v).strip() == "" else str(v).strip()) for v in s]
    return X
