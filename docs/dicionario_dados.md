# Dicionário de dados

## Prata — `data/silver/*.parquet`

| Coluna | Tipo | Descrição |
|---|---|---|
| `descricao` | texto | Caracterização como veio da fonte |
| `massa_t` | float | Massa em toneladas (kg convertido quando a fonte declara a unidade) |
| `destinacao_txt` | texto | Destinação como veio da fonte |
| `uf` | texto(2) | Sigla da UF, maiúscula; vazio quando a fonte não informa |
| `ano` | int | Ano da destinação/declaração |
| `cat_id` | texto | Id da categoria (`rccA`…`fronteira`, `reee`, `nc` = não classificado) |
| `familia` | texto | RCC, RSU, RSS, Saneamento, Transporte, REEE, Não classificado |
| `categoria` | texto | Nome oficial SINIR da categoria |
| `destinacao` | texto | Valor normalizado do enum `Destinacao` |
| `adequada` | bool | Falso para lixão e aterro controlado |

## Ouro — `data/gold/residuos.duckdb`

**`fato_residuo`**: grão UF × ano × categoria × destinação.
`uf, ano, cat_id, destinacao, adequada, massa_t, registros`

**`dim_categoria`**: `cat_id, familia, categoria, ordem` (25 linhas: 23 SINIR + REEE + não classificado)

**`dim_uf`**: `uf, regiao, populacao` (população só quando o IBGE foi carregado)

**`mart_uf_ano`** (view): `uf, regiao, ano, massa_t, pct_inadequada, kg_por_hab`

## Contratos de qualidade (camada prata)

| Checagem | Tipo | Limite |
|---|---|---|
| Arquivo não vazio | bloqueante | — |
| Massa negativa | bloqueante | 0 linhas |
| Massa ausente/não numérica | bloqueante | ≤ 5% |
| UF inexistente | bloqueante | 0 linhas |
| Ano fora de 2000–2100 | bloqueante | 0 linhas |
| Não classificado | aviso | ≤ 30% |
| Destinação não informada | aviso | ≤ 50% |

Limites configuráveis por `RESIDUOS_MAX_NC` e `RESIDUOS_MAX_SEM_MASSA`.
