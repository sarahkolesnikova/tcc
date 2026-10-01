from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def cliente(ouro, cfg):
    from app.api import main
    main.get_repo.cache_clear()
    yield TestClient(main.app)
    main.get_repo.cache_clear()


def test_saude(cliente):
    r = cliente.get("/saude")
    assert r.status_code == 200 and r.json()["ouro_disponivel"] is True


def test_kpis_batem_com_categorias(cliente):
    k = cliente.get("/kpis").json()
    cats = cliente.get("/categorias").json()
    assert k["massa_t"] == pytest.approx(sum(c["massa_t"] for c in cats))
    assert 0 < k["pct_inadequada"] < 1
    assert k["registros"] == 601
    assert k["categorias_sinir"] >= 15


def test_filtros(cliente):
    sp = cliente.get("/kpis", params={"uf": "sp"}).json()
    tudo = cliente.get("/kpis").json()
    assert 0 < sp["massa_t"] < tudo["massa_t"]
    rss = cliente.get("/categorias", params={"familia": "RSS"}).json()
    assert rss and all(c["familia"] == "RSS" for c in rss)
    ufs = cliente.get("/uf", params={"ano": 2023}).json()
    assert {u["uf"] for u in ufs} <= {"SP", "MG", "RJ", "BA", "PR", "PE", "PA", "GO", "AM", "RS"}


def test_sem_ouro_retorna_503(tmp_path, monkeypatch):
    from app.api import main
    monkeypatch.setenv("RESIDUOS_DATA_DIR", str(tmp_path / "vazio"))
    main.get_repo.cache_clear()
    r = TestClient(main.app).get("/kpis")
    main.get_repo.cache_clear()
    assert r.status_code == 503


@pytest.mark.parametrize("pagina", [
    "app/dashboard/Panorama.py",
    "app/dashboard/pages/1_Regioes.py",
    "app/dashboard/pages/2_Qualidade_e_anomalias.py",
])
def test_paginas_do_dashboard_renderizam_sem_erro(ouro, pagina):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(RAIZ / pagina), default_timeout=60).run()
    assert not at.exception, at.exception
    assert not at.warning  # warning = ouro ausente


def test_dashboard_kpis_e_filtro(ouro):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(RAIZ / "app/dashboard/Panorama.py"), default_timeout=60).run()
    rotulos = [m.label for m in at.metric]
    assert rotulos == ["Massa declarada", "Destinação inadequada", "Categorias SINIR presentes",
                       "Eletroeletrônicos (REEE)"]
    antes = at.metric[0].value
    at.multiselect(key="f_uf").select("SP").run()
    assert not at.exception and at.metric[0].value != antes
