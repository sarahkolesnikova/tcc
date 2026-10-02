"""Estado compartilhado: storage, cache de DataFrames e de relatórios (em memória, como no TCC)."""
from __future__ import annotations

import threading
from collections import OrderedDict
from functools import lru_cache

import pandas as pd

from .config import Settings
from .models.storage import Storage, criar_storage


class LRU:
    def __init__(self, maximo: int):
        self.maximo = maximo
        self._d: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, k):
        with self._lock:
            if k in self._d:
                self._d.move_to_end(k)
                return self._d[k]
        return None

    def set(self, k, v):
        with self._lock:
            self._d[k] = v
            self._d.move_to_end(k)
            while len(self._d) > self.maximo:
                self._d.popitem(last=False)

    def descartar(self, prefixo: str):
        with self._lock:
            for k in [k for k in self._d if str(k).startswith(prefixo)]:
                del self._d[k]


class Contexto:
    def __init__(self, cfg: Settings, storage: Storage):
        self.cfg = cfg
        self.storage = storage
        self.dataframes: LRU = LRU(8)    # file_id → DataFrame
        self.relatorios: LRU = LRU(32)   # f"{file_id}:{chave}" → (resultados, relatório)

    def dataframe(self, file_id: str, rec: dict) -> pd.DataFrame:
        from .services.io import ler_planilha
        df = self.dataframes.get(file_id)
        if df is None:
            df = ler_planilha(self.storage.get_object(rec["storage_key"]), rec["filename"])
            self.dataframes.set(file_id, df)
        return df

    def esquecer(self, file_id: str):
        self.dataframes.descartar(file_id)
        self.relatorios.descartar(f"{file_id}:")


@lru_cache
def get_contexto() -> Contexto:
    cfg = Settings.from_env()
    return Contexto(cfg, criar_storage(cfg))
