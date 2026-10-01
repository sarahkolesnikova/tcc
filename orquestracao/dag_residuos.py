"""DAG Airflow: ingestão mensal do RAPP + IBGE, validação e publicação do ouro.

A lógica fica toda no pacote `residuos`; o DAG só orquestra. Uma falha de contrato
de dados (`ContratoViolado`) falha a tarefa e o ouro anterior continua publicado.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task


@dag(
    dag_id="residuos_rapp_mensal",
    schedule="0 6 5 * *",          # dia 5 de cada mês, 06:00
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=15)},
    tags=["residuos", "ibama", "sinir"],
)
def residuos_rapp_mensal():
    @task
    def populacao_ibge() -> str:
        from residuos.config import Settings
        from residuos.ingestao.ibge import IbgeExtractor
        return str(IbgeExtractor(Settings.from_env().raw_dir).extract(ano=2021, forcar=True))

    @task
    def pipeline_rapp(caminho_ibge: str) -> dict:
        from pathlib import Path

        from residuos.config import Settings
        from residuos.ingestao.ibama import IbamaExtractor
        from residuos.ingestao.ibge import IbgeExtractor
        from residuos.pipeline import Pipeline

        cfg = Settings.from_env()
        pop = IbgeExtractor.para_dataframe(Path(caminho_ibge))
        ext = IbamaExtractor(cfg.raw_dir, "destinador")
        ext.extract(forcar=True)
        res = Pipeline(cfg).run(ext, pop)
        return {"linhas": res.linhas, "marts": res.marts}

    pipeline_rapp(populacao_ibge())


residuos_rapp_mensal()
