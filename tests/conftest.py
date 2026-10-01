from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from residuos.config import Settings

RAIZ = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def amostras():
    """Garante que as amostras sintéticas existem (gera se faltarem)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("gerar", FIX / "gerar_amostras.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {
        "rapp": FIX / "rapp_destinador_amostra.csv" if (FIX / "rapp_destinador_amostra.csv").exists() else mod.rapp_destinador(),
        "sinir": FIX / "sinir_municipal_amostra.csv" if (FIX / "sinir_municipal_amostra.csv").exists() else mod.sinir_municipal(),
        "ibge": FIX / "ibge_populacao_amostra.json" if (FIX / "ibge_populacao_amostra.json").exists() else mod.ibge_populacao(),
    }


@pytest.fixture
def cfg(tmp_path: Path) -> Settings:
    data = tmp_path / "data"
    data.mkdir()
    return Settings(data_dir=data, sql_dir=RAIZ / "sql", chunksize=150)


@pytest.fixture
def ouro(cfg, amostras, monkeypatch):
    """Roda o pipeline completo na amostra RAPP e aponta o ambiente para o ouro gerado."""
    from residuos.ingestao.base import ArquivoLocalExtractor
    from residuos.ingestao.ibge import IbgeExtractor
    from residuos.pipeline import Pipeline

    raw = cfg.raw_dir
    raw.mkdir(parents=True, exist_ok=True)
    csv = shutil.copy(amostras["rapp"], raw / "rapp_destinador.csv")
    pop = IbgeExtractor.para_dataframe(amostras["ibge"])
    res = Pipeline(cfg).run(ArquivoLocalExtractor(Path(csv)), pop)
    monkeypatch.setenv("RESIDUOS_DATA_DIR", str(cfg.data_dir))
    return res
