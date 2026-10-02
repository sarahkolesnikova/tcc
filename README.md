# Anomaly Detector

Aplicação para identificar inconsistências e erros em planilhas CSV, XLSX e XLS (até 50 MB).
São 14 detectores de anomalias (8 numéricos e 6 categóricos), cada linha sinalizada vem com o
motivo, e os resultados podem ser exportados em CSV e PDF.

TCC — Universidade Virtual do Estado de São Paulo (UNIVESP), Cursos do Eixo de Computação, 2026.

```
frontend/   React 19 + TypeScript + React Router v7 + Tailwind CSS v4 + Recharts v3 (Vite 8)
backend/    Python 3.11 + FastAPI · NumPy, pandas, SciPy, scikit-learn, ReportLab · Supabase
benchmark/  benchmark reproduzível dos 14 detectores (métricas, curvas ROC, tempo de execução)
supabase/   esquema do banco (tabelas files e analyses)
exemplos/   planilhas de exemplo para demonstração (valores fictícios)
docs/       decisões de método  em relação ao texto do TCC
```

## Rodando no Windows (PowerShell)

Pré-requisitos: Python 3.11 ou 3.12 (`winget install Python.Python.3.12`) e Node.js 22
(`winget install OpenJS.NodeJS.LTS`). Abra **dois** terminais.

**Terminal 1 — backend**

```powershell
cd anomaly-detector\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # se bloquear: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements-dev.txt
pytest                                 # 56 testes
uvicorn src.main:app --reload          # API em http://localhost:8000/docs
```

**Terminal 2 — frontend**

```powershell
cd anomaly-detector\frontend
npm install
npm run dev                            # http://localhost:5173
```

Abra http://localhost:5173 e envie `exemplos\vendas_exemplo.csv`. A linha 8 tem um valor
digitado errado (25.000) e a linha 43 tem uma loja escrita errada ("Lojaa Centro").

## Rodando no Linux/macOS

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt && pytest && uvicorn src.main:app --reload
# outro terminal
cd frontend && npm install && npm run dev
```

Ou tudo com Docker: `cp backend/.env.example backend/.env && docker compose up --build`.

## Supabase

Sem credenciais, o backend usa armazenamento local (SQLite + pasta `backend/data/`), suficiente
para desenvolvimento e demonstração. Para usar o Supabase:

1. Crie um projeto em supabase.com e rode `supabase/migrations/001_init.sql` no SQL Editor.
2. Crie um bucket **privado** chamado `uploads` (Storage → New bucket).
3. Copie `backend/.env.example` para `backend/.env` e preencha `SUPABASE_URL` e `SUPABASE_KEY`
   (chave `service_role`, que fica só no backend, nunca no frontend).

`GET /api/health` mostra qual armazenamento está ativo.

## API

| Endpoint | Descrição |
|---|---|
| `POST /api/files/upload` | Recebe o arquivo (multipart). Apaga arquivos com mais de 10 min, grava no storage e no banco, devolve UUID e colunas tipadas. |
| `GET /api/files/{file_id}` | Dados do arquivo (roda a limpeza automática antes). |
| `DELETE /api/files/{file_id}` | Apaga o registro e o arquivo. |
| `GET /api/report/models` | Lista os 14 detectores, separados em numéricos e categóricos. |
| `POST /api/report/generate/{file_id}` | Corpo: `models`, `numeric_columns`, `categorical_columns`, `threshold`. Devolve o relatório completo. |
| `GET /api/report/cleaned/{file_id}` | CSV com uma coluna por modelo, votos e score de consenso; `remover=true` devolve só as linhas não sinalizadas. |
| `GET /api/report/pdf/{file_id}` | Relatório em PDF. |
| `GET /api/report/history` | Histórico de análises (permanece depois que o arquivo expira). |

## Benchmark

```bash
cd backend && source .venv/bin/activate     # Windows: .\.venv\Scripts\Activate.ps1
cd .. && python benchmark/run_benchmark.py  # ~1–2 min; resultados em benchmark/resultados/
```

Gera a tabela de médias com a linha de base aleatória, as curvas ROC por dataset, o gráfico de
tempo por número de linhas e um `RESUMO.md` com os achados. O protocolo está em
`benchmark/datasets.py`.

## Testes

- `backend`: `pytest` — detectores (incluindo a taxa de sinalização com 30 colunas), API,
  formatos CSV/XLSX/XLS, limites, expiração dos arquivos e contrato do Supabase.
- `frontend`: `npm run typecheck`, `npm test` e `npm run e2e -- ../exemplos/vendas_exemplo.csv`
  (fluxo completo no navegador com Playwright; precisa do backend e do `npm run dev` rodando).
