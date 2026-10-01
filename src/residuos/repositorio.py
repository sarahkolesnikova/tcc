"""Repositório analítico: Parquet por camada + DuckDB para os marts (camada ouro)."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from .dominio import CATEGORIAS, NAO_CLASSIFICADO
from .ingestao.ibge import UF_REGIAO


class Repositorio:
    def __init__(self, data_dir: Path, sql_dir: Path, db_path: Path | None = None):
        self.data_dir = Path(data_dir)
        self.sql_dir = Path(sql_dir)
        self.db_path = Path(db_path or self.data_dir / "gold" / "residuos.duckdb")
        for camada in ("bronze", "silver", "gold"):
            (self.data_dir / camada).mkdir(parents=True, exist_ok=True)

    def conectar(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.db_path), read_only=read_only)

    def salvar_parquet(self, df: pd.DataFrame, camada: str, nome: str) -> Path:
        destino = self.data_dir / camada / f"{nome}.parquet"
        df.to_parquet(destino, index=False)
        return destino

    def construir_ouro(self, silver: pd.DataFrame, populacao: pd.DataFrame | None = None) -> list[str]:
        """Carrega prata e referências no DuckDB e executa os SQL de sql/marts em ordem."""
        ref_cat = pd.DataFrame(
            [(c.id, c.familia.value, c.nome, i) for i, c in enumerate((*CATEGORIAS, NAO_CLASSIFICADO))],
            columns=["cat_id", "familia", "categoria", "ordem"],
        )
        ref_uf = pd.DataFrame(sorted(UF_REGIAO.items()), columns=["uf", "regiao"])
        pop = populacao if populacao is not None else pd.DataFrame(
            {"uf": pd.Series(dtype=str), "populacao": pd.Series(dtype="Int64")})
        cols = ["uf", "ano", "cat_id", "familia", "categoria", "destinacao", "adequada", "massa_t"]
        executados = []
        with self.conectar() as con:
            for nome, df in {"silver_residuo": silver[cols], "ref_categoria": ref_cat,
                             "ref_uf": ref_uf, "ref_populacao": pop[["uf", "populacao"]]}.items():
                con.register("_tmp", df)
                con.execute(f"CREATE OR REPLACE TABLE {nome} AS SELECT * FROM _tmp")
                con.unregister("_tmp")
            ordem = ["dim_categoria", "dim_uf", "fato_residuo"]
            arquivos = sorted(self.sql_dir.glob("marts/*.sql"),
                              key=lambda p: (ordem.index(p.stem) if p.stem in ordem else 99, p.stem))
            for sql in arquivos:
                con.execute(sql.read_text(encoding="utf-8"))
                executados.append(sql.stem)
        return executados

    def consultar(self, sql: str, params: list | None = None) -> pd.DataFrame:
        with self.conectar(read_only=True) as con:
            return con.execute(sql, params or []).df()
