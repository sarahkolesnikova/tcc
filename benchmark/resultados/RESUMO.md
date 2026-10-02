# Resumo do benchmark

Sementes: [0, 1, 2, 3, 4]. Contaminação = taxa real de cada dataset.

## Achados

- Linha de base aleatória: F1 = 0,073 (igual à taxa média de anomalias) e AUC = 0,5.
- Maior F1 médio: **Modified Z-Score (MAD)** (0,482; lift 11,2× o acaso), mas sinalizando 23,6% das linhas para uma taxa real de 7,3%: parte do F1 vem de recall comprado com falsos positivos.
- Maior AUC-ROC médio: **Co-ocorrência de Pares** (0,807).
- Maior especificidade: **Percentile Fence** (0,957).
- Maior lift num único dataset: **Distância de Mahalanobis** em synthetic_2 (F1 = 0,774, 38,7× o acaso).
- Modelos com AUC médio abaixo de 0,5 (pior que o acaso): Qui-Quadrado.
- Modelos que sinalizam mais que o dobro da taxa real: Modified Z-Score (MAD), IQR (Tukey), Teste Binomial.
- Datasets em que a mediana do AUC dos detectores numéricos fica abaixo de 0,5: digits (0,295). Nesses casos a classe rotulada como anomalia forma um grupo denso, não pontos isolados, e o protocolo não mede detecção de anomalias.

## Por dataset (F1 / AUC-ROC)

| nome                      |   breast_cancer |   digits |   synthetic_2 |   synthetic_5 |   wine |
|:--------------------------|----------------:|---------:|--------------:|--------------:|-------:|
| Aleatório (linha de base) |           0.101 |    0.099 |         0.02  |         0.05  |  0.097 |
| Co-ocorrência de Pares    |           0.655 |    0.034 |         0.542 |         0.566 |  0.486 |
| Distância de Mahalanobis  |           0.509 |    0.005 |         0.774 |         0.757 |  0.329 |
| Entropia por Linha        |           0.65  |    0.006 |         0.485 |         0.497 |  0.543 |
| Frequência Relativa       |           0.436 |    0.037 |         0.451 |         0.479 |  0.211 |
| IQR (Tukey)               |           0.511 |    0.081 |         0.467 |         0.495 |  0.36  |
| Isolation Forest          |           0.61  |    0.03  |         0.515 |         0.54  |  0.514 |
| KNN Distance              |           0.485 |    0.006 |         0.665 |         0.71  |  0.214 |
| LOF                       |           0.19  |    0.056 |         0.74  |         0.784 |  0.086 |
| LOF Categórico            |           0.395 |    0.011 |         0.021 |         0.024 |  0.557 |
| Modified Z-Score (MAD)    |           0.527 |    0.188 |         0.633 |         0.658 |  0.403 |
| Percentile Fence          |           0.212 |    0     |         0.627 |         0.657 |  0.178 |
| Qui-Quadrado              |           0.028 |    0.089 |         0.085 |         0.167 |  0.026 |
| Teste Binomial            |           0.298 |    0.18  |         0.35  |         0.38  |  0.242 |
| Z-Score                   |           0.489 |    0.007 |         0.537 |         0.599 |  0.243 |


| nome                      |   breast_cancer |   digits |   synthetic_2 |   synthetic_5 |   wine |
|:--------------------------|----------------:|---------:|--------------:|--------------:|-------:|
| Aleatório (linha de base) |           0.5   |    0.5   |         0.5   |         0.5   |  0.5   |
| Co-ocorrência de Pares    |           0.946 |    0.541 |         0.806 |         0.817 |  0.926 |
| Distância de Mahalanobis  |           0.879 |    0.235 |         0.907 |         0.882 |  0.788 |
| Entropia por Linha        |           0.942 |    0.583 |         0.745 |         0.752 |  0.933 |
| Frequência Relativa       |           0.881 |    0.288 |         0.752 |         0.75  |  0.72  |
| IQR (Tukey)               |           0.924 |    0.302 |         0.744 |         0.745 |  0.842 |
| Isolation Forest          |           0.923 |    0.404 |         0.822 |         0.819 |  0.912 |
| KNN Distance              |           0.904 |    0.144 |         0.912 |         0.905 |  0.847 |
| LOF                       |           0.758 |    0.493 |         0.951 |         0.94  |  0.796 |
| LOF Categórico            |           0.883 |    0.28  |         0.798 |         0.683 |  0.944 |
| Modified Z-Score (MAD)    |           0.918 |    0.483 |         0.744 |         0.745 |  0.868 |
| Percentile Fence          |           0.757 |    0.26  |         0.744 |         0.744 |  0.722 |
| Qui-Quadrado              |           0.355 |    0.417 |         0.611 |         0.642 |  0.307 |
| Teste Binomial            |           0.88  |    0.288 |         0.755 |         0.752 |  0.72  |
| Z-Score                   |           0.87  |    0.287 |         0.742 |         0.745 |  0.847 |


## Tempo com 20.000 linhas (mediana de 3 execuções)

| nome                     |   tempo_ms |
|:-------------------------|-----------:|
| Z-Score                  |       16.1 |
| Modified Z-Score (MAD)   |       17.5 |
| Distância de Mahalanobis |       25.4 |
| Percentile Fence         |       27.7 |
| IQR (Tukey)              |       28   |
| Frequência Relativa      |       28   |
| Teste Binomial           |       43.8 |
| Entropia por Linha       |       62.1 |
| Co-ocorrência de Pares   |       92.8 |
| Qui-Quadrado             |      131.3 |
| LOF                      |      627.5 |
| Isolation Forest         |      865.8 |
| LOF Categórico           |     1004.9 |
| KNN Distance             |     1642.5 |

