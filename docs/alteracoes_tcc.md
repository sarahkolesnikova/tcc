# O que muda no texto do TCC

Este documento compara o texto da entrega preliminar com o que o código implementa e mede.
Os números vêm de `benchmark/resultados/` (5 sementes) e podem ser regenerados com
`python benchmark/run_benchmark.py`.

## Implementado como o texto descreve

- Arquitetura em três camadas: SPA React + TypeScript + React Router v7 (`app/routes.ts`,
  API declarativa), backend Python 3.11 + FastAPI, Supabase (PostgreSQL + Object Storage),
  comunicação HTTP/JSON, CORS para `http://localhost:5173`, Dockerfiles.
- Frontend com React 19, Tailwind CSS v4, Recharts v3, Vite 8; sem gerenciador de estado
  global, sessão no LocalStorage; rotas e arquivos da Tabela 1 (`homepage.tsx`,
  `upload_archives.tsx`, `filtercolumns.tsx`, `modelspage.tsx`, `reportpage.tsx`).
- Backend com NumPy 2.x, pandas 3.x, SciPy 1.x, scikit-learn 1.8, ReportLab 4.x, biblioteca
  `supabase`, `python-dotenv`; módulos `main.py`, `models/`, `routes/` (`file_routes.py`,
  `model_routes.py`) e `services/` com subpacotes `numeric/` e `categorical/`, um módulo por
  algoritmo e interface padronizada.
- Os 7 endpoints da Tabela 2, com limpeza de arquivos com mais de 10 minutos.
- Os 14 detectores; NaN → mediana (numéricos) e "missing" (categóricos); MAD com fallback
  para desvio-padrão; Mahalanobis com pseudo-inversa; KNN com k = √n (mín. 5, máx. n − 1);
  co-ocorrência com score zero quando há menos de duas colunas categóricas.
- Upload de CSV, XLSX e XLS até 50 MB; exportação CSV e PDF; critérios por registro.

## Diferenças em relação ao texto (e por quê)

| Ponto | Texto | Implementação | Motivo |
|---|---|---|---|
| Agregação por linha (Z-Score, IQR, Percentile Fence, Binomial) | limiar por coluna = contaminação | correção de Šidák: α por coluna = 1 − (1 − c)^(1/p) | sem ela, 30 colunas a 5% sinalizam ~78% das linhas; é a origem dos 73,8% e 66,8% da Tabela 3 |
| Teste Binomial | proporção vs. valor teórico | H₀: p = min(contaminação, 1/K) | contra a uniforme (1/K), qualquer categoria só desbalanceada vira anomalia |
| LOF Categórico | Ordinal Encoding | One-hot | a codificação ordinal inventa ordem e distância entre categorias |
| Discretização no benchmark | não descrita | 10 faixas de mesma largura | quantis deixam todas as categorias com a mesma frequência e zeram Frequência/Binomial |
| Rastreabilidade | "rastreabilidade das análises" e limpeza em 10 min | arquivo apagado em 10 min; tabela `analyses` guarda nome, SHA-256, parâmetros e contagens para sempre | o texto prometia as duas coisas, que se contradiziam |
| Supabase | obrigatório | obrigatório em produção; fallback local (SQLite) sem credenciais | permite rodar, testar e demonstrar sem conta |

Todas estão documentadas no código (docstrings) e cobertas por testes.

## Correções necessárias no texto

**1. "F1-norm = 17,000".** O F1 vai de 0 a 1. O valor só faz sentido como F1 ÷ taxa de
anomalias (F1 = 0,34 com 2% de anomalias → 17), ou seja, quantas vezes melhor que o acaso.
Sugestão: chamar de **lift do F1** e definir na seção 3.4: "como um classificador aleatório
tem F1 igual à taxa de anomalias, o lift (F1 ÷ taxa) indica quantas vezes o detector supera o
acaso". No benchmark novo, Mahalanobis tem F1 = 0,774 no Synthetic-2% (lift 38,7×).

**2. Linha de base aleatória.** Acrescentar à Tabela 3 a linha "Aleatório": F1 = taxa média de
anomalias (0,073), AUC = 0,5. Sem ela, a frase "F1 de 0,20–0,30 não indica baixa qualidade"
não se sustenta. Com ela, o argumento vira concreto.

**3. Descrever o protocolo dos datasets** (seção 5.1). Breast Cancer, Wine e Digits são do
scikit-learn montados no protocolo do ADBench, não os arquivos do ADBench. Texto sugerido:
"Seguindo o protocolo do ADBench, uma classe foi tomada como normal e outra como anomalia,
subamostrada: Breast Cancer (maligno, 40 de 397), Wine (classe 2, 14 de 144) e Digits (dígito
0, 178 de 1.797). Os dois sintéticos têm 2.000 linhas de uma normal multivariada correlacionada;
metade das anomalias são valores extremos e metade quebram a correlação entre colunas sem valor
extremo isolado. Para os detectores categóricos, cada coluna foi discretizada em 10 faixas de
mesma largura. As métricas são médias de 5 subamostragens."

**4. Substituir a Tabela 3** por `benchmark/resultados/tabela_medias.md`. Resumo:

| Modelo | F1 | AUC-ROC | Anom. prev. (real 7,3%) |
|---|---|---|---|
| Modified Z-Score (MAD) | 0,482 | 0,751 | 23,6% |
| Distância de Mahalanobis | 0,475 | 0,738 | 10,2% |
| Co-ocorrência de Pares | 0,457 | 0,807 | 7,4% |
| Isolation Forest | 0,442 | 0,776 | 7,3% |
| Entropia por Linha | 0,436 | 0,791 | 7,4% |
| KNN Distance | 0,416 | 0,742 | 7,3% |
| IQR (Tukey) | 0,383 | 0,711 | 21,7% |
| Z-Score | 0,375 | 0,698 | 10,5% |
| LOF | 0,371 | 0,788 | 7,3% |
| Percentile Fence | 0,335 | 0,645 | 5,3% |
| Frequência Relativa | 0,323 | 0,678 | 9,5% |
| Teste Binomial | 0,290 | 0,679 | 43,0% |
| LOF Categórico | 0,202 | 0,718 | 7,3% |
| Qui-Quadrado | 0,079 | 0,466 | 7,9% |
| **Aleatório** | **0,073** | **0,500** | 7,3% |

**5. Reescrever a análise comparativa (5.2) com base nos números novos.** Pontos que os dados
sustentam:
- Todos os 14 superam o acaso em F1; só o Qui-Quadrado fica abaixo de 0,5 em AUC.
- MAD tem o maior F1, mas sinaliza 23,6% das linhas para 7,3% reais: limiar fixo (3,5) não
  respeita a contaminação em colunas assimétricas ou esparsas. Nos sintéticos, que são normais,
  ele fica em 2,6% (taxa real 5%). O mesmo vale para o IQR (21,7%).
- Mahalanobis é o melhor onde há correlação entre colunas: lift 38,7× no Synthetic-2% e
  15,1× no Synthetic-5%, porque é o único tipo de detector que pega as anomalias de correlação.
- LOF e Isolation Forest têm os maiores AUC entre os numéricos (0,788 e 0,776): ranqueiam bem,
  mesmo quando o corte binário não é o ideal.
- Teste Binomial: recall alto (0,739) e precisão baixa (0,200), como o texto já dizia, e agora
  com a causa explicada (testa a raridade de cada categoria em cada coluna).
- **Digits não funciona como teste de anomalias neste protocolo**: a mediana do AUC dos
  detectores numéricos é 0,295 (abaixo do acaso). O dígito 0 forma um grupo denso e homogêneo,
  não pontos isolados. Vale dizer isso como limitação, em vez de esconder na média.

**6. Tempo de execução (5.3).** Usar `benchmark/resultados/tempo_execucao.png` (pedido do
avaliador). Com 5.000 linhas, os estatísticos diretos levam de 4 a 7 ms (não
"sub-milissegundo": o tempo inclui gerar a explicação de cada linha); KNN 170 ms, LOF 97 ms,
Isolation Forest 367 ms; categóricos de 9 a 34 ms, LOF Categórico 86 ms.

**7. Curvas ROC (5.2).** Incluir `roc_numericos.png` e `roc_categoricos.png` (pedido do avaliador).

**8. Figura 2.** A legenda promete upload, seleção de modelos e geração de relatório, mas o
diagrama termina na seleção de colunas. Completar o diagrama ou ajustar a legenda.

**9. Referências.** Tanenbaum, Aggarwal e Emmott aparecem na lista, mas não no texto; citar ou
remover. Padronizar "Qui-Quadrado" (o texto também usa "Chi-Quadrado").

**10. Comentários do avaliador já atendidos pelo código:** página inicial com "Como usar" (o
manual passo a passo pedido para abrir os Resultados pode usar as capturas das 5 telas), gráfico
de tempo por número de linhas e curvas ROC.

## O repositório

O repositório `sarahkolesnikova/tcc` hoje contém o Observatório de Resíduos, um projeto
diferente do descrito no texto. Para a banca, o repositório do TCC deve conter este projeto.
O Observatório pode ir para um repositório próprio. A planilha municipal do SINIR está em
`exemplos/` e pode ser usada num estudo de caso com dados reais.
