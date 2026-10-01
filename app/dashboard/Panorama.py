"""Dashboard — página Panorama. Rode: streamlit run app/dashboard/Panorama.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # raiz (pacote app)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import streamlit as st  # noqa: E402

from app.dashboard.dados import fato, filtros, fmt_t  # noqa: E402

st.set_page_config(page_title="Observatório de Resíduos", layout="wide")
st.title("Observatório de Resíduos Brasil")

df = fato()
if df.empty:
    st.warning("A camada ouro ainda não existe. Rode `residuos run` para construí-la.")
    st.stop()

sel = filtros(df)
total = sel["massa_t"].sum()
inad = sel.loc[~sel["adequada"], "massa_t"].sum()
cats = sel.loc[~sel["cat_id"].isin(["nc", "reee"]), "cat_id"].nunique()
reee = sel.loc[sel["familia"] == "REEE", "massa_t"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Massa declarada", fmt_t(total))
c2.metric("Destinação inadequada", f"{(inad / total if total else 0):.1%}".replace(".", ","),
          help="Lixão e aterro controlado sobre a massa total")
c3.metric("Categorias SINIR presentes", f"{cats}/23")
c4.metric("Eletroeletrônicos (REEE)", fmt_t(reee))

esq, dir_ = st.columns(2)
with esq:
    st.subheader("Massa por família")
    st.bar_chart(sel.groupby("familia")["massa_t"].sum().sort_values(), horizontal=True)
with dir_:
    st.subheader("Massa por destinação")
    st.bar_chart(sel.groupby("destinacao")["massa_t"].sum().sort_values(), horizontal=True)

st.subheader("Evolução anual por família (t)")
serie = sel.dropna(subset=["ano"]).pivot_table(index="ano", columns="familia", values="massa_t", aggfunc="sum")
serie.index = serie.index.astype(int).astype(str)   # evita "2,021" no eixo
st.line_chart(serie)

with st.expander("Tabela por categoria"):
    st.dataframe(
        sel.groupby(["familia", "categoria"], as_index=False)["massa_t"].sum()
           .sort_values("massa_t", ascending=False),
        hide_index=True, use_container_width=True)
