"""Página Qualidade: declarações atípicas e previsão da série anual."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

import streamlit as st  # noqa: E402

from app.dashboard.dados import fato, filtros  # noqa: E402
from residuos.analytics.anomalias import detectar  # noqa: E402
from residuos.analytics.previsao import prever_linear  # noqa: E402

st.title("Qualidade e tendência")
df = fato()
if df.empty:
    st.warning("Rode `residuos run` primeiro.")
    st.stop()
sel = filtros(df)

st.subheader("Registros agregados atípicos")
st.caption("z-score robusto em escala log, por categoria. |z| > 3,5 merece revisão da fonte.")
anom = detectar(sel, min_grupo=5)
if anom.empty:
    st.success("Nenhum valor atípico com os filtros atuais.")
else:
    st.dataframe(anom[["uf", "ano", "categoria", "destinacao", "massa_t", "z_robusto"]],
                 hide_index=True, use_container_width=True)

st.subheader("Tendência da massa declarada")
serie = sel.dropna(subset=["ano"]).groupby("ano")["massa_t"].sum()
if len(serie) >= 3:
    prev = prever_linear(serie.index, serie.values, ate=int(serie.index.max()) + 3)
    graf = prev.tabela.assign(ano=prev.tabela["ano"].astype(str)).set_index("ano")
    st.line_chart(graf[["valor", "previsto", "li", "ls"]])
    mape = f"{prev.mape_backtest:.1%}" if prev.mape_backtest is not None else "n/d"
    st.caption(f"Tendência linear, R² = {prev.r2:.2f}, MAPE de backtest = {mape}. "
               "Intervalo de predição de 95%.")
else:
    st.info("A previsão exige pelo menos 3 anos na seleção.")
