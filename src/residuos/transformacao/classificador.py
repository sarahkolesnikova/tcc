"""WasteClassifier: texto livre de caracterização → Categoria (23 do SINIR + REEE)."""
from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd

from ..dominio import CATEGORIAS, NAO_CLASSIFICADO, Categoria, Destinacao
from .staging import norm


class WasteClassifier:
    def __init__(self, categorias: tuple[Categoria, ...] = CATEGORIAS):
        self.categorias = categorias
        self._exatos = {norm(c.nome): c for c in categorias}
        self._regras = [(c, [re.compile(k) for k in c.palavras_chave]) for c in categorias]
        self.classify = lru_cache(maxsize=50_000)(self._classify)

    def _classify(self, descricao: object) -> Categoria:
        d = norm(descricao)
        if not d:
            return NAO_CLASSIFICADO
        if d in self._exatos:
            return self._exatos[d]
        for cat, pats in self._regras:
            if any(p.search(d) for p in pats):
                return cat
        return NAO_CLASSIFICADO

    def aplicar(self, staging: pd.DataFrame) -> pd.DataFrame:
        """Acrescenta cat_id, familia, categoria, destinacao e adequada ao staging."""
        # listas em vez de Series de objetos: Enum(str) vira string no pandas 3 e perde atributos
        out = staging.copy()
        cats = [self.classify(d) for d in out["descricao"].tolist()]
        out["cat_id"] = [c.id for c in cats]
        out["familia"] = [c.familia.value for c in cats]
        out["categoria"] = [c.nome for c in cats]
        dest = [Destinacao.from_texto(d) for d in out["destinacao_txt"].tolist()]
        out["destinacao"] = [d.value for d in dest]
        out["adequada"] = pd.array([d.adequada for d in dest], dtype=bool)
        return out
