"""Pipeline: raw → bronze (staging) → prata (classificado + validado) → ouro (DuckDB)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .config import Settings
from .ingestao.base import Extractor
from .qualidade.contratos import Relatorio, ValidadorPrata
from .repositorio import Repositorio
from .transformacao.classificador import WasteClassifier
from .transformacao.staging import ler_em_blocos, padronizar

log = logging.getLogger(__name__)


@dataclass
class ResultadoPipeline:
    arquivo_raw: Path
    linhas: int
    relatorio: Relatorio
    marts: list[str] = field(default_factory=list)
    resumo_familia: pd.DataFrame | None = None


class Pipeline:
    def __init__(self, config: Settings | None = None, classificador: WasteClassifier | None = None,
                 validador: ValidadorPrata | None = None, repositorio: Repositorio | None = None):
        self.config = config or Settings.from_env()
        self.classificador = classificador or WasteClassifier()
        self.validador = validador or ValidadorPrata(self.config.max_nao_classificado,
                                                     self.config.max_sem_massa)
        self.repo = repositorio or Repositorio(self.config.data_dir, self.config.sql_dir,
                                               self.config.db_path)

    def transformar(self, csv: Path, **colunas) -> pd.DataFrame:
        mapa, blocos = ler_em_blocos(csv, chunksize=self.config.chunksize, **colunas)
        log.info("colunas detectadas: %s", mapa)
        partes = [self.classificador.aplicar(padronizar(b, mapa)) for b in blocos]
        if not partes:
            raise ValueError(f"{csv} não tem linhas de dados")
        return pd.concat(partes, ignore_index=True)

    def run(self, extractor: Extractor, populacao: pd.DataFrame | None = None,
            nome: str | None = None, **colunas) -> ResultadoPipeline:
        raw = extractor.extract()
        nome = nome or f"{extractor.fonte}_{Path(raw).stem}"
        silver = self.transformar(raw, **colunas)
        self.repo.salvar_parquet(silver[["descricao", "massa_t", "destinacao_txt", "uf", "ano"]],
                                 "bronze", nome)
        relatorio = self.validador.exigir(silver)  # lança ContratoViolado e para aqui
        log.info("qualidade:\n%s", relatorio.resumo())
        self.repo.salvar_parquet(silver, "silver", nome)
        marts = self.repo.construir_ouro(silver, populacao)
        resumo = (silver.groupby("familia", as_index=False)["massa_t"].sum()
                  .sort_values("massa_t", ascending=False))
        return ResultadoPipeline(Path(raw), len(silver), relatorio, marts, resumo)
