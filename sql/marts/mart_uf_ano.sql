-- Visão pronta para o dashboard: indicadores por UF e ano.
CREATE OR REPLACE VIEW mart_uf_ano AS
SELECT
    f.uf,
    u.regiao,
    f.ano,
    SUM(f.massa_t)                                              AS massa_t,
    SUM(CASE WHEN NOT f.adequada THEN f.massa_t ELSE 0 END)
        / NULLIF(SUM(f.massa_t), 0)                             AS pct_inadequada,
    SUM(f.massa_t) * 1000 / NULLIF(MAX(u.populacao), 0)         AS kg_por_hab
FROM fato_residuo f
LEFT JOIN dim_uf u USING (uf)
GROUP BY f.uf, u.regiao, f.ano;
