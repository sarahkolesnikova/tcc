-- Dimensão de categorias: vem da tabela de referência carregada pelo pipeline.
CREATE OR REPLACE TABLE dim_categoria AS
SELECT cat_id, familia, categoria, ordem
FROM ref_categoria;
