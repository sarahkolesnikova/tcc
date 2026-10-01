"""Linha de comando: `residuos run | listar | anomalias | exportar`."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .config import Settings
from .ingestao.base import ArquivoLocalExtractor
from .ingestao.ibama import FORMULARIOS, IbamaExtractor
from .ingestao.ibge import IbgeExtractor
from .ingestao.sinir import SinirExtractor
from .pipeline import Pipeline
from .qualidade.contratos import ContratoViolado


def _cmd_run(a, cfg: Settings) -> int:
    if a.arquivo:
        ext = ArquivoLocalExtractor(Path(a.arquivo), cfg.raw_dir)
    elif a.fonte == "sinir":
        ext = SinirExtractor(cfg.raw_dir)
    else:
        ext = IbamaExtractor(cfg.raw_dir, a.formulario)
    populacao = None
    if a.ibge_ano:
        ibge = IbgeExtractor(cfg.raw_dir)
        populacao = ibge.para_dataframe(ibge.extract(ano=a.ibge_ano))
    cols = {k: v for k, v in {"massa": a.col_massa, "descricao": a.col_desc,
                              "destinacao": a.col_dest, "uf": a.col_uf, "ano": a.col_ano}.items() if v}
    try:
        res = Pipeline(cfg).run(ext, populacao, **cols)
    except ContratoViolado as e:
        print("Contrato de dados violado; ouro NÃO atualizado.\n" + str(e), file=sys.stderr)
        return 2
    print(res.relatorio.resumo())
    print(f"\nMarts: {', '.join(res.marts)} → {cfg.db_path}")
    print(res.resumo_familia.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
    return 0


def _cmd_listar(a, cfg: Settings) -> int:
    print(json.dumps(IbamaExtractor(cfg.raw_dir).listar_conjuntos(a.query), ensure_ascii=False, indent=2))
    print(json.dumps(SinirExtractor(cfg.raw_dir).recursos(), ensure_ascii=False, indent=2))
    return 0


def _cmd_anomalias(a, cfg: Settings) -> int:
    import pandas as pd
    from .analytics.anomalias import detectar
    silver = pd.concat(pd.read_parquet(p) for p in (cfg.data_dir / "silver").glob("*.parquet"))
    out = detectar(silver, limiar=a.limiar)
    print(out[["uf", "ano", "categoria", "massa_t", "z_robusto"]].head(a.top).to_string(index=False))
    return 0


def _cmd_exportar(a, cfg: Settings) -> int:
    """CSV no formato do analisador do painel HTML (Massa (TON); Caracterização; Destinação; UF)."""
    from .repositorio import Repositorio
    df = Repositorio(cfg.data_dir, cfg.sql_dir, cfg.db_path).consultar(
        """SELECT f.uf AS "UF", f.ano, c.categoria AS "Caracterização - Descrição",
                  f.destinacao AS "Destinação", f.massa_t AS "Massa (TON)"
           FROM fato_residuo f JOIN dim_categoria c USING (cat_id)""")
    df.to_csv(a.saida, sep=";", decimal=",", index=False)
    print(f"{len(df):,} linhas → {a.saida}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="residuos", description="Observatório de Resíduos — pipeline")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="executa o pipeline completo")
    r.add_argument("--fonte", choices=["ibama", "sinir"], default="ibama")
    r.add_argument("--formulario", choices=sorted(FORMULARIOS), default="destinador")
    r.add_argument("--arquivo", help="CSV local em vez de baixar")
    r.add_argument("--ibge-ano", type=int, help="carrega população do IBGE (ex.: 2021)")
    for c in ("massa", "desc", "dest", "uf", "ano"):
        r.add_argument(f"--col-{c}", help=f"força o nome da coluna de {c}")

    ls = sub.add_parser("listar", help="lista conjuntos de resíduos nos CKAN do Ibama e MMA")
    ls.add_argument("--query", default="residuos")

    an = sub.add_parser("anomalias", help="declarações de massa atípicas na camada prata")
    an.add_argument("--limiar", type=float, default=3.5)
    an.add_argument("--top", type=int, default=20)

    ex = sub.add_parser("exportar", help="exporta o fato para o analisador do painel HTML")
    ex.add_argument("--saida", default="residuos_agregado.csv")

    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO if a.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    cfg = Settings.from_env()
    return {"run": _cmd_run, "listar": _cmd_listar, "anomalias": _cmd_anomalias,
            "exportar": _cmd_exportar}[a.cmd](a, cfg)


if __name__ == "__main__":
    raise SystemExit(main())
