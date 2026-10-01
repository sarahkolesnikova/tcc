"""Staging: normalização de texto, números BR, detecção de colunas e leitura em streaming."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pandas as pd

UFS = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)


def norm(s: object) -> str:
    """Minúsculas, sem acento, sem espaços nas pontas. None/NaN viram ''."""
    if s is None or (isinstance(s, float) and s != s):
        return ""
    txt = unicodedata.normalize("NFD", str(s))
    return "".join(ch for ch in txt if unicodedata.category(ch) != "Mn").lower().strip()


def to_num(v: object) -> float:
    """Converte '1.200,5', '1200.5', '30' e números para float. Inválido vira NaN."""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v if v is not None else "").strip().replace(" ", "")
    if not s:
        return float("nan")
    if re.search(r",\d{1,6}$", s) or ("." in s and "," in s):
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        # "2.000" / "1.250.000": separador de milhar BR (dados públicos brasileiros não usam
        # ponto decimal com exatamente 3 casas; "1200.5" continua decimal)
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return float("nan")


@dataclass
class MapaColunas:
    massa: str
    descricao: str
    destinacao: str | None = None
    uf: str | None = None
    ano: str | None = None
    unidade: str | None = None

    def usadas(self) -> list[str]:
        return [c for c in dict.fromkeys(
            [self.massa, self.descricao, self.destinacao, self.uf, self.ano, self.unidade]
        ) if c]


PADROES = {
    "massa": [r"quantidade", r"massa", r"^qtd", r"peso", r"tonelada"],
    "descricao": [r"caracteriza", r"descri.*resid", r"tipo.*resid", r"residuo", r"descri"],
    "destinacao": [r"tipo.*destina", r"destina", r"tratamento", r"disposi"],
    "uf": [r"^uf$", r"^estado$", r"\buf\b", r"sigla.*uf"],
    "ano": [r"^ano$", r"ano.*destina", r"^ano", r"ano"],
    "unidade": [r"unidade"],
}


def achar_coluna(cols, padroes, forcada: str | None = None, excluir=()) -> str | None:
    if forcada:
        return forcada
    ncols = {c: norm(c) for c in cols if c not in excluir}
    for p in padroes:
        for c, n in ncols.items():
            if re.search(p, n):
                return c
    return None


def detectar_colunas(cols, **forcadas) -> MapaColunas:
    achadas: dict[str, str | None] = {}
    for campo in ("massa", "descricao", "unidade", "destinacao", "uf", "ano"):
        achadas[campo] = achar_coluna(
            cols, PADROES[campo], forcadas.get(campo), excluir=[v for v in achadas.values() if v]
        )
    if not (achadas["massa"] and achadas["descricao"]):
        raise ValueError(f"Colunas de massa/descrição não encontradas. Disponíveis: {list(cols)}")
    return MapaColunas(**achadas)


def sniff(csv: Path) -> tuple[str, str]:
    """Detecta encoding (utf-8 ou latin-1) e separador (; ou ,)."""
    head = csv.read_bytes()[:20000]
    try:
        head.decode("utf-8")
        enc = "utf-8"
    except UnicodeDecodeError:
        enc = "latin-1"
    sep = ";" if head.count(b";") > head.count(b",") else ","
    return enc, sep


def ler_em_blocos(csv: Path, mapa: MapaColunas | None = None, chunksize: int = 200_000,
                  **forcadas) -> tuple[MapaColunas, Iterator[pd.DataFrame]]:
    enc, sep = sniff(csv)
    if mapa is None:
        cols = pd.read_csv(csv, sep=sep, encoding=enc, nrows=0).columns
        mapa = detectar_colunas(cols, **forcadas)
    it = pd.read_csv(csv, sep=sep, encoding=enc, usecols=mapa.usadas(), chunksize=chunksize,
                     dtype=str, on_bad_lines="skip")
    return mapa, it


def padronizar(bloco: pd.DataFrame, mapa: MapaColunas) -> pd.DataFrame:
    """Leva um bloco bruto ao esquema de staging (colunas canônicas, massa em t)."""
    out = pd.DataFrame(index=bloco.index)
    out["descricao"] = bloco[mapa.descricao].astype("object")
    massa = bloco[mapa.massa].map(to_num).astype(float)
    if mapa.unidade:
        kg = bloco[mapa.unidade].map(norm).str.contains(r"\bkg\b|quilo", regex=True, na=False)
        massa = massa.where(~kg, massa / 1000)
    out["massa_t"] = massa
    out["destinacao_txt"] = bloco[mapa.destinacao].astype("object") if mapa.destinacao else None
    out["uf"] = bloco[mapa.uf].map(lambda x: norm(x).upper()) if mapa.uf else ""
    if mapa.ano:
        out["ano"] = pd.to_numeric(bloco[mapa.ano].astype(str).str.extract(r"(\d{4})")[0], errors="coerce").astype("Int64")
    else:
        out["ano"] = pd.array([pd.NA] * len(bloco), dtype="Int64")
    return out
