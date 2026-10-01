-- Fato agregado: massa por UF × ano × categoria × destinação.
CREATE OR REPLACE TABLE fato_residuo AS
SELECT
    NULLIF(uf, '')            AS uf,
    ano,
    cat_id,
    destinacao,
    adequada,
    SUM(massa_t)              AS massa_t,
    COUNT(*)                  AS registros
FROM silver_residuo
WHERE massa_t IS NOT NULL
GROUP BY ALL;
