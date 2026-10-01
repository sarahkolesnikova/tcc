# Decisões de método

1. **Camadas bronze/prata/ouro.** O dashboard e a API só leem o ouro. Mudança de layout
   na fonte afeta apenas o `Extractor` e o staging.
2. **Classificação por regras, não por modelo.** As 23 categorias têm nomes oficiais
   estáveis; regras explícitas (match exato → palavras-chave em ordem de especificidade)
   são auditáveis e testadas uma a uma. Ordem importa: "Classe B" vence "plástico",
   "aeroporto" não é confundido com "porto".
3. **Números brasileiros.** Vírgula decimal; ponto com exatamente 3 casas é milhar.
   Essa regra corrigiu um erro do script original, que lia "2.000" como 2.
4. **Contrato bloqueante.** Se a prata viola um contrato bloqueante, o pipeline para
   antes de reconstruir o ouro, e o painel continua mostrando a última versão válida.
5. **Anomalias em log com MAD.** Massas têm cauda longa; média/desvio seriam dominados
   pelos extremos. Limiar |z| > 3,5 (Iglewicz & Hoaglin).
6. **k-means em numpy.** Evita depender do scikit-learn só para isso; rótulo 0 é sempre o
   perfil com maior fração inadequada, para que as cores do painel sejam estáveis.
7. **SQL puro em `sql/marts/`**, executado pelo DuckDB. Migrar para dbt é trocar os nomes
   de tabela por `{{ ref() }}`; a lógica não muda.
