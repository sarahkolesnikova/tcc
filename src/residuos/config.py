"""Configuração via variáveis de ambiente (prefixo RESIDUOS_)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path = RAIZ / "data"
    sql_dir: Path = RAIZ / "sql"
    max_nao_classificado: float = 0.30
    max_sem_massa: float = 0.05
    chunksize: int = 200_000

    @classmethod
    def from_env(cls) -> "Settings":
        e = os.environ.get
        return cls(
            data_dir=Path(e("RESIDUOS_DATA_DIR", str(cls.data_dir))),
            sql_dir=Path(e("RESIDUOS_SQL_DIR", str(cls.sql_dir))),
            max_nao_classificado=float(e("RESIDUOS_MAX_NC", cls.max_nao_classificado)),
            max_sem_massa=float(e("RESIDUOS_MAX_SEM_MASSA", cls.max_sem_massa)),
            chunksize=int(e("RESIDUOS_CHUNKSIZE", cls.chunksize)),
        )

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "gold" / "residuos.duckdb"
