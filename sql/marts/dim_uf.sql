-- Dimensão UF com região e população (quando o IBGE foi carregado).
CREATE OR REPLACE TABLE dim_uf AS
SELECT r.uf, r.regiao, p.populacao
FROM ref_uf r
LEFT JOIN ref_populacao p USING (uf);
