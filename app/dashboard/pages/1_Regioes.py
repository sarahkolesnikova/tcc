"""Página Regiões: UF, região e perfis de destinação (clusters)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

import streamlit as st  # noqa: E402

from app.dashboard.dados import fato, filtros  # noqa: E402
from residuos.analytics.clusters import kmeans, matriz_perfil  # noqa: E402

st.title("Regiões e perfis de destinação")
df = fato()
if df.empty:
    st.warning("Rode `residuos run` primeiro.")
    st.stop()
sel = filtros(df).dropna(subset=["uf"])

por_uf = sel.assign(inad=sel["massa_t"].where(~sel["adequada"], 0)).groupby(["regiao", "uf"], as_index=False)[
    ["massa_t", "inad"]].sum()
por_uf["% inadequada"] = por_uf["inad"] / por_uf["massa_t"]
st.subheader("Destinação inadequada por UF")
st.bar_chart(por_uf.set_index("uf")["% inadequada"].sort_values(ascending=False))

perfil = matriz_perfil(sel)
if len(perfil) >= 3:
    k = st.slider("Número de perfis (k)", 2, min(6, len(perfil)), 3, key="k")
    res = kmeans(perfil, k=k)
    st.subheader("Perfis de destinação")
    st.caption("Perfil 0 = maior fração em lixão/aterro controlado.")
    st.dataframe(res.centroides.style.format("{:.0%}"), use_container_width=True)
    st.dataframe(res.rotulos.rename("perfil").reset_index(), hide_index=True)
else:
    st.info("São necessárias pelo menos 3 UFs para agrupar perfis.")
