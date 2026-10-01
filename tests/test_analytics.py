import numpy as np
import pandas as pd
import pytest

from residuos.analytics.anomalias import detectar, zscore_robusto
from residuos.analytics.clusters import kmeans, matriz_perfil
from residuos.analytics.previsao import prever_linear


def test_previsao_recupera_tendencia_exata():
    anos = [2019, 2020, 2021, 2022, 2023]
    prev = prever_linear(anos, [100, 102, 104, 106, 108], ate=2026)
    fut = prev.tabela[prev.tabela.tipo == "previsto"]
    assert fut.ano.tolist() == [2024, 2025, 2026]
    assert fut.previsto.tolist() == pytest.approx([110, 112, 114])
    assert prev.inclinacao == pytest.approx(2) and prev.r2 == pytest.approx(1)
    assert prev.mape_backtest == pytest.approx(0, abs=1e-9)


def test_intervalo_alarga_no_futuro():
    rng = np.random.default_rng(1)
    anos = np.arange(2010, 2024)
    prev = prever_linear(anos, 80 + 0.5 * (anos - 2010) + rng.normal(0, 1, len(anos)), ate=2030)
    largura = (prev.tabela.ls - prev.tabela.li).to_numpy()
    assert (np.diff(largura[len(anos):]) > 0).all()
    t = prev.tabela
    assert ((t.li <= t.previsto) & (t.previsto <= t.ls)).all()


def test_previsao_exige_3_pontos():
    with pytest.raises(ValueError):
        prever_linear([2022, 2023], [1, 2], ate=2025)


def test_anomalia_detecta_erro_de_unidade():
    rng = np.random.default_rng(0)
    massas = list(rng.lognormal(3, 0.5, 60)) + [45_000]   # 45 mil t num grupo de ~20 t
    df = pd.DataFrame({"cat_id": "vidro", "massa_t": massas})
    out = detectar(df)
    assert out["massa_t"].iloc[0] == 45_000
    assert len(out) <= 3


def test_zscore_serie_constante_nao_quebra():
    assert (zscore_robusto(pd.Series([5.0] * 10)) == 0).all()


def test_anomalia_ignora_grupo_pequeno():
    df = pd.DataFrame({"cat_id": ["x"] * 3, "massa_t": [1, 1, 10_000]})
    assert detectar(df).empty


def test_clusters_separam_perfis_obvios():
    linhas = []
    for uf in ["AA", "AB", "AC"]:   # quase tudo em lixão
        linhas += [(uf, "Lixão", 90), (uf, "Aterro sanitário", 10)]
    for uf in ["BA", "BB", "BC"]:   # quase tudo reciclado/aterro
        linhas += [(uf, "Aterro sanitário", 60), (uf, "Reciclagem", 40)]
    df = pd.DataFrame(linhas, columns=["uf", "destinacao", "massa_t"])
    perfil = matriz_perfil(df)
    assert np.allclose(perfil.sum(axis=1), 1)
    res = kmeans(perfil, k=2)
    assert set(res.rotulos[["AA", "AB", "AC"]]) == {0}       # cluster 0 = mais inadequado
    assert set(res.rotulos[["BA", "BB", "BC"]]) == {1}
    assert res.centroides.loc[0, "Lixão"] == pytest.approx(0.9)


def test_kmeans_reprodutivel():
    rng = np.random.default_rng(3)
    perfil = pd.DataFrame(rng.dirichlet([1, 1, 1], 12), columns=["a", "b", "c"])
    r1, r2 = kmeans(perfil, k=3, seed=5), kmeans(perfil, k=3, seed=5)
    assert r1.rotulos.equals(r2.rotulos) and r1.inercia == r2.inercia
