import math

import pandas as pd
import pytest

from residuos.qualidade.contratos import ContratoViolado, ValidadorPrata
from residuos.transformacao.classificador import WasteClassifier
from residuos.transformacao.staging import detectar_colunas, ler_em_blocos, norm, padronizar, sniff, to_num


@pytest.mark.parametrize("v,esperado", [
    ("1.200,5", 1200.5), ("1200.5", 1200.5), ("30", 30.0), ("0,8", 0.8), (12, 12.0), (" 7 ", 7.0),
    ("2.000", 2000.0), ("1.250.000", 1_250_000.0), ("0.5", 0.5), ("-3", -3.0),
])
def test_to_num(v, esperado):
    assert to_num(v) == esperado


@pytest.mark.parametrize("v", ["", None, "abc"])
def test_to_num_invalido(v):
    assert math.isnan(to_num(v))


def test_norm():
    assert norm("  Orgânico ÁGUA ") == "organico agua"
    assert norm(float("nan")) == ""


def test_detecta_colunas_do_ibama_e_do_sinir():
    ib = detectar_colunas(["ID Gerador", "UF", "Ano da destinação", "Descrição do resíduo",
                           "Quantidade", "Unidade", "Tipo de destinação"])
    assert (ib.massa, ib.descricao, ib.destinacao, ib.uf, ib.ano, ib.unidade) == (
        "Quantidade", "Descrição do resíduo", "Tipo de destinação", "UF", "Ano da destinação", "Unidade")
    si = detectar_colunas(["Massa (TON)", "Caracterização - Descrição", "Destinação", "UF"])
    assert (si.massa, si.descricao, si.destinacao) == ("Massa (TON)", "Caracterização - Descrição", "Destinação")


def test_detectar_sem_massa_falha():
    with pytest.raises(ValueError):
        detectar_colunas(["UF", "Descrição"])


def test_sniff_latin1_e_ponto_e_virgula(amostras):
    assert sniff(amostras["rapp"]) == ("latin-1", ";")
    assert sniff(amostras["sinir"]) == ("utf-8", ",")


def test_conversao_kg_para_t():
    bruto = pd.DataFrame({"Descrição": ["Vidro", "Vidro"], "Quantidade": ["2.000", "3"],
                          "Unidade": ["kg", "t"]})
    mapa = detectar_colunas(bruto.columns)
    out = padronizar(bruto, mapa)
    assert out["massa_t"].tolist() == [2.0, 3.0]


def test_leitura_em_blocos_preserva_linhas(amostras):
    mapa, blocos = ler_em_blocos(amostras["rapp"], chunksize=100)
    total = sum(len(b) for b in blocos)
    assert total == 601  # 600 sintéticas + 1 anomalia plantada


def _silver(**sobrescrever):
    base = pd.DataFrame({
        "descricao": ["Vidro", "Metal", "Orgânico"], "massa_t": [1.0, 2.0, 3.0],
        "destinacao_txt": ["Reciclagem", "Lixão", "Compostagem"], "uf": ["SP", "MG", ""],
        "ano": pd.array([2023, 2024, None], dtype="Int64")})
    for k, v in sobrescrever.items():
        base[k] = v
    return WasteClassifier().aplicar(base)


def test_contrato_aprova_dado_limpo():
    rel = ValidadorPrata().exigir(_silver())
    assert rel.aprovado


@pytest.mark.parametrize("coluna,valores,checagem", [
    ("massa_t", [1.0, -5.0, 3.0], "massa negativa"),
    ("uf", ["SP", "XX", "MG"], "UF inexistente"),
    ("ano", pd.array([2023, 1850, 2024], dtype="Int64"), "ano fora do intervalo"),
])
def test_contrato_bloqueia(coluna, valores, checagem):
    with pytest.raises(ContratoViolado) as exc:
        ValidadorPrata().exigir(_silver(**{coluna: valores}))
    falhas = [c.nome for c in exc.value.relatorio.checagens if not c.ok]
    assert checagem in falhas


def test_nao_classificado_alto_e_aviso_nao_bloqueio():
    df = _silver(descricao=["xyz", "abc", "Vidro"])
    rel = ValidadorPrata(max_nao_classificado=0.3).validar(df)
    assert rel.aprovado
    assert any(c.nome == "não classificado" and not c.ok for c in rel.checagens)
