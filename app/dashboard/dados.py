"""Camada de acesso do dashboard: só lê a camada ouro, com cache do Streamlit."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from residuos.config import Settings
from residuos.repositorio import Repositorio


def repo() -> Repositorio:
    cfg = Settings.from_env()
    return Repositorio(cfg.data_dir, cfg.sql_dir, cfg.db_path)


@st.cache_data(ttl=600, show_spinner=False)
def fato() -> pd.DataFrame:
    r = repo()
    if not r.db_path.exists():
        return pd.DataFrame()
    return r.consultar("""
        SELECT f.uf, u.regiao, f.ano, c.familia, c.categoria, f.cat_id,
               f.destinacao, f.adequada, f.massa_t, f.registros
        FROM fato_residuo f
        JOIN dim_categoria c USING (cat_id)
        LEFT JOIN dim_uf u USING (uf)""")


def filtros(df: pd.DataFrame) -> pd.DataFrame:
    """Filtros globais na barra lateral, compartilhados por todas as páginas."""
    with st.sidebar:
        st.header("Filtros")
        ufs = sorted(df["uf"].dropna().unique())
        anos = sorted(int(a) for a in df["ano"].dropna().unique())
        fams = sorted(df["familia"].unique())
        sel_uf = st.multiselect("UF", ufs, key="f_uf")
        sel_ano = st.multiselect("Ano", anos, key="f_ano")
        sel_fam = st.multiselect("Família", fams, key="f_fam")
    out = df
    if sel_uf:
        out = out[out["uf"].isin(sel_uf)]
    if sel_ano:
        out = out[out["ano"].isin(sel_ano)]
    if sel_fam:
        out = out[out["familia"].isin(sel_fam)]
    return out


def fmt_t(v: float) -> str:
    if v >= 1e6:
        return f"{v / 1e6:,.2f} Mt".replace(",", "X").replace(".", ",").replace("X", ".")
    if v >= 1e3:
        return f"{v / 1e3:,.1f} mil t".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{v:,.1f} t".replace(",", "X").replace(".", ",").replace("X", ".")
