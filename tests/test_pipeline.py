from pathlib import Path

import pandas as pd
import pytest
import requests

from residuos.cli import main as cli
from residuos.ingestao.base import ArquivoLocalExtractor
from residuos.ingestao.ibama import IbamaExtractor
from residuos.ingestao.ibge import IbgeExtractor
from residuos.ingestao.sinir import SinirExtractor
from residuos.pipeline import Pipeline
from residuos.qualidade.contratos import ContratoViolado
from residuos.repositorio import Repositorio


def test_pipeline_ponta_a_ponta(ouro, cfg):
    assert ouro.linhas == 601
    assert ouro.relatorio.aprovado
    assert ouro.marts == ["dim_categoria", "dim_uf", "fato_residuo", "mart_uf_ano"]
    for camada in ("bronze", "silver"):
        assert list((cfg.data_dir / camada).glob("*.parquet"))
    repo = Repositorio(cfg.data_dir, cfg.sql_dir, cfg.db_path)
    silver = pd.read_parquet(next((cfg.data_dir / "silver").glob("*.parquet")))
    fato_total = repo.consultar("SELECT SUM(massa_t) AS m FROM fato_residuo")["m"][0]
    assert fato_total == pytest.approx(silver["massa_t"].sum())   # agregação não perde massa
    assert (silver["cat_id"] == "nc").sum() == 0                  # amostra 100% classificada


def test_kg_convertido_no_ouro(ouro, cfg):
    silver = pd.read_parquet(next((cfg.data_dir / "silver").glob("*.parquet")))
    # sem conversão, linhas em kg passariam de 10⁵; após /1000 só a anomalia plantada fica acima
    assert (silver["massa_t"] > 10_000).sum() == 1


def test_mart_uf_ano_usa_populacao(ouro, cfg):
    repo = Repositorio(cfg.data_dir, cfg.sql_dir, cfg.db_path)
    m = repo.consultar("SELECT * FROM mart_uf_ano WHERE uf = 'SP'")
    assert not m.empty and m["kg_por_hab"].notna().all()
    assert m["pct_inadequada"].between(0, 1).all()


def test_pipeline_formato_sinir_municipal(cfg, amostras):
    res = Pipeline(cfg).run(ArquivoLocalExtractor(amostras["sinir"]))
    assert res.linhas == 8
    repo = Repositorio(cfg.data_dir, cfg.sql_dir, cfg.db_path)
    inad = repo.consultar("SELECT SUM(massa_t) m FROM fato_residuo WHERE NOT adequada")["m"][0]
    assert inad == pytest.approx(12.3 + 9)  # metal e vidro em lixão


def test_contrato_violado_nao_publica_ouro(cfg, tmp_path):
    ruim = tmp_path / "ruim.csv"
    ruim.write_text("UF;Descrição do resíduo;Quantidade\nZZ;Vidro;10\nSP;Metal;-3\n", encoding="utf-8")
    with pytest.raises(ContratoViolado):
        Pipeline(cfg).run(ArquivoLocalExtractor(ruim))
    assert not cfg.db_path.exists()


class _Resp:
    def __init__(self, conteudo: bytes = b"", json_=None):
        self.conteudo, self._json = conteudo, json_

    def raise_for_status(self):
        pass

    def iter_content(self, n):
        yield self.conteudo

    def json(self):
        return self._json

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Sessao(requests.Session):
    def __init__(self, respostas: dict):
        super().__init__()
        self.respostas, self.urls = respostas, []

    def get(self, url, **kw):
        self.urls.append(url)
        for trecho, resp in self.respostas.items():
            if trecho in url:
                return resp
        raise AssertionError(f"URL inesperada {url}")


def test_ibama_extractor_baixa_e_usa_cache(tmp_path, amostras):
    s = _Sessao({"residuoSolidosDestinador": _Resp(Path(amostras["rapp"]).read_bytes())})
    ext = IbamaExtractor(tmp_path, "destinador", session=s)
    p1 = ext.extract()
    p2 = ext.extract()
    assert p1 == p2 and p1.read_bytes() == Path(amostras["rapp"]).read_bytes()
    assert len(s.urls) == 1  # segunda chamada veio do cache
    assert not list(tmp_path.glob("*.part"))


def test_ibama_formulario_invalido(tmp_path):
    with pytest.raises(ValueError):
        IbamaExtractor(tmp_path, "todos")


def test_sinir_extractor_escolhe_por_ano(tmp_path):
    pacote = {"result": {"resources": [
        {"name": "Dados 2021", "format": "zip", "url": "https://x/2021.zip"},
        {"name": "Dados 2022", "format": "zip", "url": "https://x/2022.zip"}]}}
    s = _Sessao({"package_show": _Resp(json_=pacote), "2022.zip": _Resp(b"PK")})
    p = SinirExtractor(tmp_path, session=s).extract(ano=2022)
    assert p.name == "sinir_2022.zip" and p.read_bytes() == b"PK"


def test_ibge_para_dataframe(amostras):
    df = IbgeExtractor.para_dataframe(amostras["ibge"])
    assert set(df.columns) == {"uf", "regiao", "populacao"}
    assert df.set_index("uf").loc["SP", "regiao"] == "Sudeste"


def test_cli_run_e_exportar(cfg, amostras, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("RESIDUOS_DATA_DIR", str(cfg.data_dir))
    monkeypatch.setenv("RESIDUOS_SQL_DIR", str(cfg.sql_dir))
    assert cli(["run", "--arquivo", str(amostras["rapp"])]) == 0
    saida = tmp_path / "export.csv"
    assert cli(["exportar", "--saida", str(saida)]) == 0
    exp = pd.read_csv(saida, sep=";", decimal=",")
    assert list(exp.columns) == ["UF", "ano", "Caracterização - Descrição", "Destinação", "Massa (TON)"]
    capsys.readouterr()
    assert cli(["anomalias", "--top", "1"]) == 0
    topo = capsys.readouterr().out.splitlines()[1]     # 1ª linha após o cabeçalho
    assert "Vidro" in topo and "45000" in topo         # anomalia plantada vem primeiro


def test_cli_contrato_violado_retorna_2(cfg, monkeypatch, tmp_path):
    monkeypatch.setenv("RESIDUOS_DATA_DIR", str(cfg.data_dir))
    ruim = tmp_path / "ruim.csv"
    ruim.write_text("UF;Descrição do resíduo;Quantidade\nZZ;Vidro;10\n", encoding="utf-8")
    assert cli(["run", "--arquivo", str(ruim)]) == 2
