import numpy as np
import pandas as pd
import pytest

from src.services import registry
from src.services.base import alpha_por_coluna, flag_top
from src.services.io import preparar_categorico, preparar_numerico

NUM = [d for d in registry.DETECTORES.values() if d.kind == "numeric"]
CAT = [d for d in registry.DETECTORES.values() if d.kind == "categorical"]


def test_catalogo_tem_14_detectores_8_numericos_6_categoricos():
    assert len(registry.DETECTORES) == 14 and len(NUM) == 8 and len(CAT) == 6
    lst = registry.listar()
    assert {d["id"] for d in lst["numeric"]} == {
        "zscore", "iqr", "mad", "mahalanobis", "knn", "lof", "isolation_forest", "percentile_fence"}
    assert {d["id"] for d in lst["categorical"]} == {
        "frequency", "entropy", "chi_square", "binomial", "cooccurrence", "lof_categorical"}


@pytest.fixture(scope="module")
def numerico():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(0, 1, (500, 4)), columns=list("abcd"))
    X.loc[[10, 200, 450], "a"] = [9.0, -10.0, 12.0]       # outliers univariados
    X.loc[300, ["b", "c"]] = [6.0, -6.0]                   # outlier em duas colunas
    return X, {10, 200, 300, 450}


@pytest.mark.parametrize("det", NUM, ids=lambda d: d.id)
def test_numericos_acham_outliers_plantados(det, numerico):
    X, plantados = numerico
    r = det.run(X, 0.02)
    assert len(r.scores) == len(r.flags) == len(r.reasons) == len(X)
    achados = set(np.where(r.flags)[0])
    assert len(plantados & achados) >= 3, f"{det.id} achou {sorted(achados)[:10]}"
    if det.id != "percentile_fence":  # score do Percentile Fence é ordinal: ignora magnitude
        top4 = set(np.argsort(-r.scores)[:4])
        assert len(plantados & top4) >= 3                   # e eles têm os maiores scores
    assert all((r.reasons[i] is None) != bool(r.flags[i]) for i in range(len(X)))  # motivo só nas sinalizadas


@pytest.mark.parametrize("det", NUM, ids=lambda d: d.id)
def test_taxa_de_sinalizacao_nao_explode_com_muitas_colunas(det):
    """Correção do item 3: sem Šidák, 30 colunas normais a 5% sinalizariam ~78% das linhas."""
    rng = np.random.default_rng(1)
    X = pd.DataFrame(rng.normal(0, 1, (2000, 30)), columns=[f"c{i}" for i in range(30)])
    taxa = det.run(X, 0.05).flags.mean()
    limite = 0.10 if det.id != "iqr" else 0.15  # IQR é aproximação normal; tolerância maior
    assert taxa <= limite, f"{det.id}: {taxa:.1%}"


def test_sidak():
    assert alpha_por_coluna(0.05, 1) == pytest.approx(0.05)
    a = alpha_por_coluna(0.05, 30)
    assert 1 - (1 - a) ** 30 == pytest.approx(0.05)


def test_flag_top_empates_e_constante():
    f, _ = flag_top(np.array([1, 1, 1, 1.0]), 0.25)
    assert not f.any()
    f, _ = flag_top(np.array([0, 0, 5, 5, 1, 1, 1, 1, 1, 1.0]), 0.1)
    assert f.tolist().count(True) == 2  # empate no corte entra inteiro


@pytest.fixture(scope="module")
def categorico():
    rng = np.random.default_rng(2)
    n = 600
    cidade = rng.choice(["SP", "RJ", "BH"], n, p=[.5, .3, .2])
    # tipo depende da cidade (associação forte); poucos casos quebram a regra
    tipo = np.where(cidade == "SP", "A", np.where(cidade == "RJ", "B", "C")).astype(object)
    canal = rng.choice(["web", "loja"], n)
    df = pd.DataFrame({"cidade": cidade.astype(object), "tipo": tipo, "canal": canal.astype(object)})
    df.loc[5, "cidade"] = "Xique-Xique"     # categoria raríssima
    df.loc[77, "tipo"] = "C"                # combinação incoerente (SP, C)
    df.loc[78, "tipo"] = "A"; df.loc[78, "cidade"] = "BH"  # (BH, A)
    return df, {5, 77, 78}


@pytest.mark.parametrize("det", CAT, ids=lambda d: d.id)
def test_categoricos_acham_raros(det, categorico):
    df, plantados = categorico
    X = preparar_categorico(df, list(df.columns))
    r = det.run(X, 0.02)
    achados = set(np.where(r.flags)[0])
    esperado = {5} if det.id in ("frequency", "binomial", "entropy") else plantados
    assert len(esperado & achados) >= min(2, len(esperado)) or esperado <= achados, f"{det.id}: {sorted(achados)[:15]}"
    assert r.flags.mean() < 0.2


def test_cooccurrence_com_uma_coluna_nao_sinaliza():
    X = pd.DataFrame({"a": ["x"] * 50 + ["y"]})
    r = registry.obter("cooccurrence").run(X, 0.05)
    assert not r.flags.any() and (r.scores == 0).all()


def test_qui_quadrado_com_uma_coluna_usa_uniforme():
    X = pd.DataFrame({"a": ["x"] * 50 + ["y"] * 49 + ["z"]})
    r = registry.obter("chi_square").run(X, 0.02)
    assert r.flags[-1]


@pytest.mark.parametrize("det", NUM, ids=lambda d: d.id)
def test_robustez_numerica(det):
    df = pd.DataFrame({"const": [5] * 40, "x": list(range(39)) + [500], "dup": list(range(39)) + [500]})
    r = det.run(preparar_numerico(df, ["const", "x", "dup"]), 0.05)  # coluna constante + covariância singular
    assert np.isfinite(r.scores).all()


def test_mad_fallback_quando_mad_zero():
    X = pd.DataFrame({"a": [1.0] * 30 + [1.5, 50.0]})  # MAD = 0
    r = registry.obter("mad").run(X, 0.05)
    assert r.flags[-1]


def test_poucas_linhas_nao_quebra():
    X = pd.DataFrame({"a": [1.0, 2.0]})
    for d in NUM:
        assert not d.run(X, 0.1).flags.any()


def test_contaminacao_invalida():
    with pytest.raises(ValueError):
        registry.obter("zscore").run(pd.DataFrame({"a": [1.0, 2, 3]}), 0.7)


def test_mahalanobis_explica_coluna_responsavel(numerico):
    X, _ = numerico
    r = registry.obter("mahalanobis").run(X, 0.02)
    assert "'a'" in r.reasons[200]
