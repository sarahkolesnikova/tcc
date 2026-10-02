import io
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src import deps
from src.config import Settings
from src.models.storage import LocalStorage, SupabaseStorage, agora

FIX = __import__("pathlib").Path(__file__).parent / "fixtures"


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path / "dados"))
    deps.get_contexto.cache_clear()
    from src.main import app
    yield TestClient(app)
    deps.get_contexto.cache_clear()


def planilha_vendas(n=300, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "valor": rng.normal(1000, 100, n).round(2),
        "quantidade": rng.integers(1, 20, n),
        "loja": rng.choice(["Centro", "Norte", "Sul"], n),
        "pagamento": rng.choice(["pix", "cartão"], n),
    })
    df.loc[7, "valor"] = 25000.0        # erro de digitação
    df.loc[42, "loja"] = "Lojaa Centro"  # categoria escrita errada
    return df


def csv_br(df: pd.DataFrame) -> bytes:
    """Formato brasileiro: ';', vírgula decimal, Latin-1."""
    return df.to_csv(index=False, sep=";", decimal=",").encode("latin-1")


def enviar(cli, conteudo: bytes, nome="vendas.csv"):
    return cli.post("/api/files/upload", files={"file": (nome, conteudo)})


def test_health(cliente):
    assert cliente.get("/api/health").json() == {"status": "ok", "storage": "local"}


def test_upload_csv_brasileiro_infere_tipos(cliente):
    r = enviar(cliente, csv_br(planilha_vendas()))
    assert r.status_code == 201, r.text
    j = r.json()
    tipos = {c["name"]: c["type"] for c in j["columns"]}
    assert tipos == {"valor": "numeric", "quantidade": "numeric", "loja": "categorical", "pagamento": "categorical"}
    assert j["rows"] == 300 and len(j["sha256"]) == 64
    assert cliente.get(f"/api/files/{j['file_id']}").json()["filename"] == "vendas.csv"


def test_upload_xlsx(cliente):
    buf = io.BytesIO()
    planilha_vendas().to_excel(buf, index=False)
    r = enviar(cliente, buf.getvalue(), "vendas.xlsx")
    assert r.status_code == 201 and r.json()["rows"] == 300


def test_upload_xls(cliente, tmp_path):
    xlwt = pytest.importorskip("xlwt")
    wb = xlwt.Workbook()
    sh = wb.add_sheet("dados")
    df = planilha_vendas(50)
    for j, c in enumerate(df.columns):
        sh.write(0, j, c)
        for i, v in enumerate(df[c]):
            sh.write(i + 1, j, v.item() if hasattr(v, "item") else v)
    p = tmp_path / "v.xls"
    wb.save(str(p))
    r = enviar(cliente, p.read_bytes(), "vendas.xls")
    assert r.status_code == 201 and r.json()["rows"] == 50


@pytest.mark.parametrize("nome,conteudo,status", [
    ("dados.txt", b"a;b\n1;2\n", 422),
    ("vazio.csv", b"a;b\n", 422),
    ("grande.csv", b"a\n" + b"1\n" * (26 * 1024 * 1024), 413),
])
def test_upload_rejeita(cliente, nome, conteudo, status):
    assert enviar(cliente, conteudo, nome).status_code == status


def corpo_relatorio(**kw):
    base = {"models": ["zscore", "mad", "isolation_forest", "frequency", "chi_square"],
            "numeric_columns": ["valor", "quantidade"], "categorical_columns": ["loja", "pagamento"],
            "threshold": 0.02}
    return {**base, **kw}


def test_fluxo_completo(cliente):
    fid = enviar(cliente, csv_br(planilha_vendas())).json()["file_id"]
    modelos = cliente.get("/api/report/models").json()
    assert len(modelos["numeric"]) == 8 and len(modelos["categorical"]) == 6

    r = cliente.post(f"/api/report/generate/{fid}", json=corpo_relatorio())
    assert r.status_code == 200, r.text
    rel = r.json()
    assert rel["summary"]["rows"] == 300 and rel["summary"]["models_run"] == 5
    # linhas 7 e 42 (base 0) = 8 e 43 na planilha
    assert rel["consensus"][0]["row"] == 8 and rel["consensus"][0]["votes"] >= 3
    linha43 = next(c for c in rel["consensus"] if c["row"] == 43)
    assert any(m["model"] == "Frequência Relativa" and "Lojaa Centro" in m["reason"] for m in linha43["reasons"])
    linha8 = next(c for c in rel["consensus"] if c["row"] == 8)
    assert any("valor" in m["reason"] for m in linha8["reasons"])
    assert sum(h["rows"] for h in rel["votes_histogram"]) == 300
    assert rel["scatter"]["x"] == "valor" and rel["statistics"]["numeric"][0]["column"] == "valor"

    q = {"models": "zscore,mad,isolation_forest,frequency,chi_square", "numeric_columns": "valor,quantidade",
         "categorical_columns": "loja,pagamento", "threshold": 0.02}
    c = cliente.get(f"/api/report/cleaned/{fid}", params=q)
    assert c.status_code == 200 and "vendas_anomalias.csv" in c.headers["content-disposition"]
    tab = pd.read_csv(io.BytesIO(c.content), sep=";", decimal=",", encoding="utf-8-sig")
    assert {"anomalia_zscore", "votos", "score_consenso"} <= set(tab.columns) and len(tab) == 300
    assert tab.loc[7, "votos"] >= 2
    limpo = pd.read_csv(io.BytesIO(cliente.get(f"/api/report/cleaned/{fid}", params={**q, "remover": True}).content),
                        sep=";", decimal=",", encoding="utf-8-sig")
    assert len(limpo) < 300 and 25000.0 not in limpo["valor"].tolist() and "votos" not in limpo.columns

    p = cliente.get(f"/api/report/pdf/{fid}", params=q)
    assert p.status_code == 200 and p.content[:4] == b"%PDF" and len(p.content) > 3000

    hist = cliente.get("/api/report/history", params={"file_id": fid}).json()
    assert len(hist) == 1  # generate, cleaned e pdf com os mesmos parâmetros = 1 análise (cache)
    assert hist[0]["summary"]["por_modelo"]["zscore"] >= 1

    assert cliente.delete(f"/api/files/{fid}").status_code == 204
    assert cliente.get(f"/api/files/{fid}").status_code == 404


@pytest.mark.parametrize("ajuste,trecho", [
    ({"models": ["inexistente"]}, "desconhecido"),
    ({"numeric_columns": ["nao_existe"]}, "inexistentes"),
    ({"models": ["zscore"], "numeric_columns": []}, "numérica"),
])
def test_parametros_invalidos(cliente, ajuste, trecho):
    fid = enviar(cliente, csv_br(planilha_vendas())).json()["file_id"]
    r = cliente.post(f"/api/report/generate/{fid}", json=corpo_relatorio(**ajuste))
    assert r.status_code == 422 and trecho in r.text


def test_threshold_fora_do_intervalo(cliente):
    fid = enviar(cliente, csv_br(planilha_vendas())).json()["file_id"]
    assert cliente.post(f"/api/report/generate/{fid}", json=corpo_relatorio(threshold=0.8)).status_code == 422


def test_todos_os_14_modelos_rodam_na_planilha_sinir(cliente):
    fid = enviar(cliente, (FIX / "sinir_municipal_amostra.csv").read_bytes(), "sinir.csv").json()["file_id"]
    todos = [m["id"] for v in cliente.get("/api/report/models").json().values() for m in v]
    r = cliente.post(f"/api/report/generate/{fid}", json={
        "models": todos, "numeric_columns": ["Massa (TON)"],
        "categorical_columns": ["Caracterização - Descrição", "Destinação"], "threshold": 0.1})
    assert r.status_code == 200, r.text
    assert len(r.json()["models"]) == 14


def test_expiracao_apaga_arquivo_e_mantem_historico(cliente):
    ctx = deps.get_contexto()
    fid = enviar(cliente, csv_br(planilha_vendas())).json()["file_id"]
    cliente.post(f"/api/report/generate/{fid}", json=corpo_relatorio())
    rec = ctx.storage.get_file(fid)
    ctx.storage.delete_file(fid)
    rec["created_at"] = (agora() - timedelta(minutes=11)).isoformat()   # envelhece o registro
    ctx.storage.insert_file(rec)
    assert cliente.get(f"/api/files/{fid}").status_code == 404           # limpeza roda na consulta
    assert not (ctx.cfg.local_data_dir / "objects" / rec["storage_key"]).exists()
    assert len(cliente.get("/api/report/history", params={"file_id": fid}).json()) == 1


def test_storage_local_bloqueia_path_traversal(tmp_path):
    st = LocalStorage(tmp_path)
    with pytest.raises(ValueError):
        st.put_object("../fora.txt", b"x", "text/plain")


class _FakeSupabase:
    """Imita a cadeia de chamadas da biblioteca supabase-py usada pelo SupabaseStorage."""

    def __init__(self):
        self.objetos, self.tabelas = {}, {"files": [], "analyses": []}
        fake = self

        class Bucket:
            def upload(self, key, data, opts): fake.objetos[key] = data
            def download(self, key): return fake.objetos[key]
            def remove(self, keys): [fake.objetos.pop(k, None) for k in keys]

        class Storage_:
            def from_(self, nome): return Bucket()

        self.storage = Storage_()

    def table(self, nome):
        fake = self

        class Q:
            def __init__(self): self.filtros, self.op, self.dados = [], "select", None
            def select(self, *_): return self
            def insert(self, rec): self.op, self.dados = "insert", rec; return self
            def delete(self): self.op = "delete"; return self
            def eq(self, c, v): self.filtros.append(lambda r: r[c] == v); return self
            def lt(self, c, v): self.filtros.append(lambda r: r[c] < v); return self
            def limit(self, _): return self
            def order(self, c): return self
            def execute(self):
                linhas = fake.tabelas[nome]
                if self.op == "insert":
                    linhas.append(self.dados)
                    return type("R", (), {"data": [self.dados]})
                sel = [r for r in linhas if all(f(r) for f in self.filtros)]
                if self.op == "delete":
                    fake.tabelas[nome] = [r for r in linhas if r not in sel]
                return type("R", (), {"data": sel})

        return Q()


def test_supabase_storage_contrato():
    st = SupabaseStorage("u", "k", "uploads", client=_FakeSupabase())
    st.put_object("a.csv", b"1", "text/csv")
    assert st.get_object("a.csv") == b"1"
    velho = {"id": "1", "filename": "a.csv", "storage_key": "a.csv", "size_bytes": 1, "sha256": "x", "rows": 1,
             "columns": [], "created_at": (agora() - timedelta(minutes=30)).isoformat()}
    st.insert_file(velho)
    st.insert_analysis({"id": "a", "file_id": "1", "filename": "a.csv", "sha256": "x", "parameters": {},
                        "summary": {}, "created_at": agora().isoformat()})
    assert st.get_file("1")["filename"] == "a.csv"
    assert st.limpar_expirados(10) == ["1"]
    assert st.get_file("1") is None and "a.csv" not in st.client.objetos
    assert len(st.list_analyses("1")) == 1


def test_criar_storage_escolhe_supabase_com_credenciais(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "chave")
    assert Settings.from_env().usa_supabase
