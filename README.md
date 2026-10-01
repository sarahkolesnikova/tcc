# Observatório de Resíduos Brasil

Pipeline e dashboard de resíduos sólidos e eletroeletrônicos (REEE) a partir de dados
abertos do **Ibama (RAPP)**, **MMA/SINIR** e **IBGE**.

```
raw (arquivo oficial) → bronze (staging) → prata (classificado + validado) → ouro (DuckDB) → API / dashboard
```

## Rodando

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[app,dev]"

# 1. pipeline (baixa o RAPP Destinador do Ibama)
residuos run --fonte ibama --formulario destinador --ibge-ano 2021 -v
#    ou com um CSV que você já tem (Ibama ou planilha municipal do SINIR):
residuos run --arquivo caminho/para/arquivo.csv

# 2. dashboard e API
streamlit run app/dashboard/Panorama.py
uvicorn app.api.main:app --reload          # docs em http://localhost:8000/docs

# 3. extras
residuos anomalias --top 20                # declarações de massa atípicas
residuos exportar --saida agregado.csv     # CSV para o painel HTML (app/painel_html)
residuos listar                            # conjuntos disponíveis nos CKAN do Ibama/MMA
```

Testes: `pytest --cov=residuos --cov=app`. As amostras em `tests/fixtures/` são
**sintéticas** (formato oficial, valores inventados); regenere com
`python tests/fixtures/gerar_amostras.py`.

## Estrutura

| Pasta | Papel |
|---|---|
| `src/residuos/ingestao/` | `Extractor` (interface) + `IbamaExtractor`, `SinirExtractor`, `IbgeExtractor`, `ArquivoLocalExtractor` |
| `src/residuos/transformacao/` | `staging.py` (números BR, kg→t, detecção de colunas, leitura em blocos) e `classificador.py` (`WasteClassifier`) |
| `src/residuos/dominio.py` | `Familia`, `Destinacao` (com `adequada`), `Categoria`, `RegistroResiduo`, catálogo das 23 categorias |
| `src/residuos/qualidade/` | contratos da camada prata; violação bloqueante impede publicar o ouro |
| `src/residuos/repositorio.py` | Parquet por camada + DuckDB; executa `sql/marts/*.sql` |
| `src/residuos/analytics/` | previsão (tendência + intervalo + backtest), anomalias (z robusto em log), clusters (k-means) |
| `sql/marts/` | `dim_categoria`, `dim_uf`, `fato_residuo`, `mart_uf_ano` |
| `app/api/` | FastAPI: `/saude`, `/kpis`, `/categorias`, `/destinacao`, `/uf` |
| `app/dashboard/` | Streamlit: Panorama, Regiões (perfis), Qualidade e tendência |
| `app/painel_html/` | painel estático publicado (analisador de CSV no navegador) |
| `orquestracao/` | DAG Airflow mensal |
| `docs/` | dicionário de dados e decisões de método |

## Decisões de método

- **Some um formulário só.** Gerador, Destinador e Armazenador do RAPP descrevem o mesmo
  resíduo em elos diferentes da cadeia; somá-los conta a mesma tonelada até três vezes.
- **"2.000" é dois mil.** Em dado público brasileiro, ponto com exatamente três casas é
  separador de milhar. "1200.5" continua decimal.
- **Destinação inadequada** = lixão + aterro controlado. "Não informada" não conta como
  inadequada, mas é monitorada pelo contrato de qualidade.
- **Previsão linear é o baseline.** Com 5 a 15 anos de série, modelos complexos
  superajustam; um modelo novo só entra se bater o MAPE de backtest da tendência linear.

Mais em [`docs/decisoes.md`](docs/decisoes.md) e [`docs/dicionario_dados.md`](docs/dicionario_dados.md).
