"""API REST de leitura dos marts (camada ouro). Rode: uvicorn app.api.main:app --reload"""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, Query

from residuos import __version__
from residuos.config import Settings
from residuos.repositorio import Repositorio

app = FastAPI(title="Observatório de Resíduos Brasil", version=__version__)


@lru_cache
def get_repo() -> Repositorio:
    cfg = Settings.from_env()
    return Repositorio(cfg.data_dir, cfg.sql_dir, cfg.db_path)


def _filtros(uf: str | None, ano: int | None) -> tuple[str, list]:
    cond, params = ["1=1"], []
    if uf:
        cond.append("f.uf = ?")
        params.append(uf.upper())
    if ano:
        cond.append("f.ano = ?")
        params.append(ano)
    return " AND ".join(cond), params


def _q(repo: Repositorio, sql: str, params: list):
    if not repo.db_path.exists():
        raise HTTPException(503, "Camada ouro ainda não foi construída. Rode `residuos run`.")
    return repo.consultar(sql, params)


@app.get("/saude")
def saude(repo: Repositorio = Depends(get_repo)):
    return {"status": "ok", "versao": __version__, "ouro_disponivel": repo.db_path.exists()}


@app.get("/kpis")
def kpis(uf: str | None = None, ano: int | None = None, repo: Repositorio = Depends(get_repo)):
    where, p = _filtros(uf, ano)
    df = _q(repo, f"""
        SELECT SUM(massa_t) AS massa_t,
               SUM(CASE WHEN NOT adequada THEN massa_t ELSE 0 END) / NULLIF(SUM(massa_t),0) AS pct_inadequada,
               COUNT(DISTINCT cat_id) FILTER (WHERE cat_id NOT IN ('nc','reee')) AS categorias_sinir,
               SUM(registros) AS registros
        FROM fato_residuo f WHERE {where}""", p)
    r = df.iloc[0]
    return {"massa_t": float(r.massa_t or 0), "pct_inadequada": float(r.pct_inadequada or 0),
            "categorias_sinir": int(r.categorias_sinir or 0), "registros": int(r.registros or 0)}


@app.get("/categorias")
def categorias(uf: str | None = None, ano: int | None = None,
               familia: str | None = Query(None, description="RCC, RSU, RSS, Saneamento, Transporte, REEE"),
               repo: Repositorio = Depends(get_repo)):
    where, p = _filtros(uf, ano)
    if familia:
        where += " AND c.familia = ?"
        p.append(familia)
    df = _q(repo, f"""
        SELECT c.cat_id, c.familia, c.categoria, SUM(f.massa_t) AS massa_t
        FROM fato_residuo f JOIN dim_categoria c USING (cat_id)
        WHERE {where} GROUP BY ALL ORDER BY massa_t DESC""", p)
    return df.to_dict(orient="records")


@app.get("/destinacao")
def destinacao(uf: str | None = None, ano: int | None = None, repo: Repositorio = Depends(get_repo)):
    where, p = _filtros(uf, ano)
    df = _q(repo, f"""SELECT destinacao, adequada, SUM(massa_t) AS massa_t
                      FROM fato_residuo f WHERE {where} GROUP BY ALL ORDER BY massa_t DESC""", p)
    return df.to_dict(orient="records")


@app.get("/uf")
def por_uf(ano: int | None = None, repo: Repositorio = Depends(get_repo)):
    where, p = _filtros(None, ano)
    df = _q(repo, f"""
        SELECT f.uf, u.regiao, SUM(f.massa_t) AS massa_t,
               SUM(CASE WHEN NOT f.adequada THEN f.massa_t ELSE 0 END)/NULLIF(SUM(f.massa_t),0) AS pct_inadequada
        FROM fato_residuo f LEFT JOIN dim_uf u USING (uf)
        WHERE {where} AND f.uf IS NOT NULL GROUP BY ALL ORDER BY massa_t DESC""", p)
    return df.to_dict(orient="records")
