"""Benchmark reproduzível dos 14 detectores do Anomaly Detector.

    python benchmark/run_benchmark.py              # completo (5 sementes)
    python benchmark/run_benchmark.py --rapido     # 1 semente, sem curva de tempo grande

Gera em benchmark/resultados/:
  metricas_por_execucao.csv   uma linha por modelo × dataset × semente
  metricas_por_dataset.csv    médias por modelo × dataset
  tabela_medias.csv / .md     médias por modelo (substitui a Tabela 3), com a linha de base aleatória
  roc_numericos.png, roc_categoricos.png   curvas ROC por dataset (pedido do avaliador)
  tempo_execucao.csv / .png   tempo × número de linhas (pedido do avaliador)
  RESUMO.md                   achados calculados a partir dos números acima

Protocolo:
- contaminação = taxa real de anomalias de cada dataset (como no TCC);
- detectores categóricos recebem as colunas discretizadas em 10 faixas de mesma largura
  (quantis anulam os detectores de frequência; ver datasets.Dataset.categorico);
- datasets reais são subamostrados com 5 sementes diferentes e as métricas são a média;
- "lift" = F1 ÷ taxa real. É o "F1-norm" do texto: um classificador aleatório tem F1 ≈ taxa,
  então lift 1 = acaso e lift 17 = F1 dezessete vezes o do acaso. O F1 em si vai de 0 a 1.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "backend"))
sys.path.insert(0, str(AQUI))

from datasets import Dataset, sintetico, todos  # noqa: E402
from src.services import registry  # noqa: E402

SAIDA = AQUI / "resultados"
NOMES = {d.id: d.name for d in registry.DETECTORES.values()}
TIPO = {d.id: d.kind for d in registry.DETECTORES.values()}
ORDEM_NUM = [d.id for d in registry.DETECTORES.values() if d.kind == "numeric"]
ORDEM_CAT = [d.id for d in registry.DETECTORES.values() if d.kind == "categorical"]
# paleta categórica validada (ordem fixa: a cor segue o modelo, nunca a posição no ranking)
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]


def metricas(y: np.ndarray, flags: np.ndarray, scores: np.ndarray) -> dict:
    tp = int((flags & (y == 1)).sum()); fp = int((flags & (y == 0)).sum())
    fn = int((~flags & (y == 1)).sum()); tn = int((~flags & (y == 0)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    auc = roc_auc_score(y, scores) if len(np.unique(scores)) > 1 else 0.5
    return {"f1": f1, "precisao": prec, "recall": rec, "especificidade": tn / (tn + fp) if tn + fp else 0.0,
            "auc_roc": auc, "taxa_real": float(y.mean()), "taxa_prevista": float(flags.mean()),
            "lift_f1": f1 / y.mean()}


def entradas(ds: Dataset) -> dict[str, pd.DataFrame]:
    return {"numeric": ds.X, "categorical": ds.categorico()}


def rodar_metricas(sementes: list[int]) -> tuple[pd.DataFrame, dict]:
    linhas, rocs = [], {}
    for seed in sementes:
        for ds in todos(seed):
            X = entradas(ds)
            for mid, det in registry.DETECTORES.items():
                r = det.run(X[det.kind], ds.taxa)
                linhas.append({"modelo": mid, "nome": det.name, "tipo": det.kind, "dataset": ds.nome,
                               "semente": seed, "tempo_s": r.elapsed_s, **metricas(ds.y, r.flags, r.scores)})
                if seed == sementes[0]:
                    rocs[(ds.nome, mid)] = roc_curve(ds.y, r.scores)[:2]
            # linha de base: rótulos aleatórios na taxa real (valor esperado analítico)
            c = ds.taxa
            linhas.append({"modelo": "aleatorio", "nome": "Aleatório (linha de base)", "tipo": "—",
                           "dataset": ds.nome, "semente": seed, "tempo_s": 0.0, "f1": c, "precisao": c,
                           "recall": c, "especificidade": 1 - c, "auc_roc": 0.5, "taxa_real": c,
                           "taxa_prevista": c, "lift_f1": 1.0})
    return pd.DataFrame(linhas), rocs


def grafico_roc(rocs: dict, ids: list[str], arquivo: Path, titulo: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dsets = list(dict.fromkeys(k[0] for k in rocs))
    fig, axs = plt.subplots(1, len(dsets), figsize=(4 * len(dsets), 4.3), sharey=True)
    for ax, ds in zip(axs, dsets):
        ax.plot([0, 1], [0, 1], ls="--", lw=1, color="#898781", label="Aleatório")
        for cor, mid in zip(PALETA, ids):
            fpr, tpr = rocs[(ds, mid)]
            ax.plot(fpr, tpr, lw=1.6, color=cor, label=NOMES[mid])
        ax.set_title(ds.replace("_", " "), fontsize=10)
        ax.set_xlabel("Taxa de falsos positivos", fontsize=9)
        ax.grid(color="#e1e0d9", lw=0.6)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1.01)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(labelsize=8)
    axs[0].set_ylabel("Taxa de verdadeiros positivos (recall)", fontsize=9)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=min(len(l), 5), fontsize=8.5, frameon=False)
    fig.suptitle(titulo, fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    fig.savefig(arquivo, dpi=160)
    plt.close(fig)


def medir_tempo(tamanhos: list[int], repeticoes: int = 3) -> pd.DataFrame:
    linhas = []
    for n in tamanhos:
        ds = sintetico(0.05, seed=0, n=n)
        X = entradas(ds)
        X["categorical"] = X["categorical"].iloc[:, :3]  # 3 colunas categóricas
        for mid, det in registry.DETECTORES.items():
            tempos = [det.run(X[det.kind], 0.05).elapsed_s for _ in range(repeticoes)]
            linhas.append({"modelo": mid, "nome": det.name, "tipo": det.kind, "linhas": n,
                           "tempo_s": float(np.median(tempos))})
        print(f"  tempo: {n} linhas ok")
    return pd.DataFrame(linhas)


def grafico_tempo(t: pd.DataFrame, arquivo: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, ids, titulo in ((axs[0], ORDEM_NUM, "Numéricos (6 colunas)"), (axs[1], ORDEM_CAT, "Categóricos (3 colunas)")):
        for cor, mid in zip(PALETA, ids):
            d = t[t.modelo == mid]
            ax.plot(d.linhas, d.tempo_s * 1000, marker="o", ms=4, lw=1.6, color=cor, label=NOMES[mid])
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_title(titulo, fontsize=10, loc="left")
        ax.set_xlabel("Linhas (escala log)", fontsize=9)
        ax.grid(color="#e1e0d9", lw=0.6, which="both")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(labelsize=8)
        ax.legend(fontsize=8, frameon=False)
    axs[0].set_ylabel("Tempo mediano (ms, escala log)", fontsize=9)
    fig.tight_layout()
    fig.savefig(arquivo, dpi=160)
    plt.close(fig)


def tabela_md(df: pd.DataFrame) -> str:
    cab = "| Modelo | Tipo | F1 | Precisão | Recall | Especif. | AUC-ROC | Lift F1 | Anom. real | Anom. prev. |\n"
    cab += "|---|---|---|---|---|---|---|---|---|---|\n"
    br = lambda v, c=3: f"{v:.{c}f}".replace(".", ",")  # noqa: E731
    pc = lambda v: f"{v:.1%}".replace(".", ",")  # noqa: E731
    tipo = {"numeric": "Numérico", "categorical": "Categórico", "—": "—"}
    return cab + "".join(
        f"| {'**' + r.nome + '**' if r.modelo == 'aleatorio' else r.nome} | {tipo[r.tipo]} | {br(r.f1)} | {br(r.precisao)} | "
        f"{br(r.recall)} | {br(r.especificidade)} | {br(r.auc_roc)} | {br(r.lift_f1, 2)} | {pc(r.taxa_real)} | {pc(r.taxa_prevista)} |\n"
        for r in df.itertuples())


def resumo(por_ds: pd.DataFrame, medias: pd.DataFrame, tempo: pd.DataFrame | None, sementes) -> str:
    base = medias[medias.modelo == "aleatorio"].iloc[0]
    mods = medias[medias.modelo != "aleatorio"]
    abaixo_acaso_auc = mods[mods.auc_roc < 0.5].nome.tolist()
    melhor_f1 = mods.iloc[0]
    melhor_auc = mods.sort_values("auc_roc", ascending=False).iloc[0]
    melhor_esp = mods.sort_values("especificidade", ascending=False).iloc[0]
    pior_ds = por_ds[por_ds.modelo != "aleatorio"]
    top_lift = pior_ds.sort_values("lift_f1", ascending=False).iloc[0]
    excesso = mods[mods.taxa_prevista > 2 * mods.taxa_real].nome.tolist()
    num = pior_ds[pior_ds.tipo == "numeric"]
    auc_med = num.groupby("dataset").auc_roc.median()
    ruins = auc_med[auc_med < 0.5]
    v = lambda x, c=3: f"{x:.{c}f}".replace(".", ",")  # noqa: E731
    L = [f"# Resumo do benchmark\n", f"Sementes: {list(sementes)}. Contaminação = taxa real de cada dataset.\n",
         "## Achados\n",
         f"- Linha de base aleatória: F1 = {v(base.f1)} (igual à taxa média de anomalias) e AUC = 0,5.",
         f"- Maior F1 médio: **{melhor_f1.nome}** ({v(melhor_f1.f1)}; lift {v(melhor_f1.lift_f1, 1)}× o acaso)"
         + (f", mas sinalizando {v(melhor_f1.taxa_prevista * 100, 1)}% das linhas para uma taxa real de {v(melhor_f1.taxa_real * 100, 1)}%: "
            "parte do F1 vem de recall comprado com falsos positivos." if melhor_f1.taxa_prevista > 2 * melhor_f1.taxa_real else "."),
         f"- Maior AUC-ROC médio: **{melhor_auc.nome}** ({v(melhor_auc.auc_roc)}).",
         f"- Maior especificidade: **{melhor_esp.nome}** ({v(melhor_esp.especificidade)}).",
         f"- Maior lift num único dataset: **{top_lift.nome}** em {top_lift.dataset} "
         f"(F1 = {v(top_lift.f1)}, {v(top_lift.lift_f1, 1)}× o acaso).",
         f"- Modelos com AUC médio abaixo de 0,5 (pior que o acaso): {', '.join(abaixo_acaso_auc) or 'nenhum'}.",
         f"- Modelos que sinalizam mais que o dobro da taxa real: {', '.join(excesso) or 'nenhum'}.",
         (f"- Datasets em que a mediana do AUC dos detectores numéricos fica abaixo de 0,5: "
          f"{', '.join(f'{d} ({v(a)})' for d, a in ruins.items())}. Nesses casos a classe rotulada como anomalia "
          "forma um grupo denso, não pontos isolados, e o protocolo não mede detecção de anomalias."
          if len(ruins) else "- Em todos os datasets a mediana do AUC dos detectores numéricos supera 0,5."),
         "",
         "## Por dataset (F1 / AUC-ROC)\n",
         por_ds.pivot_table(index="nome", columns="dataset", values="f1").round(3).to_markdown(), "\n",
         por_ds.pivot_table(index="nome", columns="dataset", values="auc_roc").round(3).to_markdown(), "\n"]
    if tempo is not None:
        maior = tempo.linhas.max()
        t = tempo[tempo.linhas == maior].sort_values("tempo_s")
        L += [f"## Tempo com {maior:,} linhas (mediana de 3 execuções)\n".replace(",", "."),
              t[["nome", "tempo_s"]].assign(tempo_ms=lambda d: (d.tempo_s * 1000).round(1))
              [["nome", "tempo_ms"]].to_markdown(index=False), "\n"]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapido", action="store_true")
    a = ap.parse_args()
    sementes = [0] if a.rapido else [0, 1, 2, 3, 4]
    tamanhos = [500, 1000, 5000] if a.rapido else [500, 1000, 5000, 10000, 20000]
    SAIDA.mkdir(exist_ok=True)

    print("métricas…")
    exec_, rocs = rodar_metricas(sementes)
    exec_.to_csv(SAIDA / "metricas_por_execucao.csv", index=False)
    cols = ["f1", "precisao", "recall", "especificidade", "auc_roc", "taxa_real", "taxa_prevista", "lift_f1", "tempo_s"]
    por_ds = exec_.groupby(["modelo", "nome", "tipo", "dataset"], as_index=False)[cols].mean()
    por_ds.to_csv(SAIDA / "metricas_por_dataset.csv", index=False)
    medias = (por_ds.groupby(["modelo", "nome", "tipo"], as_index=False)[cols].mean()
              .sort_values("f1", ascending=False))
    medias.to_csv(SAIDA / "tabela_medias.csv", index=False)
    (SAIDA / "tabela_medias.md").write_text(tabela_md(medias), encoding="utf-8")

    print("curvas ROC…")
    grafico_roc(rocs, ORDEM_NUM, SAIDA / "roc_numericos.png", "Curvas ROC — detectores numéricos (semente 0)")
    grafico_roc(rocs, ORDEM_CAT, SAIDA / "roc_categoricos.png",
                "Curvas ROC — detectores categóricos (10 faixas de mesma largura; semente 0)")

    print("tempo de execução…")
    tempo = medir_tempo(tamanhos)
    tempo.to_csv(SAIDA / "tempo_execucao.csv", index=False)
    grafico_tempo(tempo, SAIDA / "tempo_execucao.png")

    (SAIDA / "RESUMO.md").write_text(resumo(por_ds, medias, tempo, sementes), encoding="utf-8")
    print(f"\npronto → {SAIDA}")
    print(tabela_md(medias))


if __name__ == "__main__":
    main()
