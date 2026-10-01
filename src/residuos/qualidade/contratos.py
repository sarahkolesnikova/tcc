"""Contratos de dados da camada prata. Uma violação bloqueante impede a publicação do ouro."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..transformacao.staging import UFS


@dataclass
class Checagem:
    nome: str
    ok: bool
    linhas_afetadas: int
    bloqueante: bool
    detalhe: str = ""


@dataclass
class Relatorio:
    total_linhas: int
    checagens: list[Checagem] = field(default_factory=list)

    @property
    def aprovado(self) -> bool:
        return all(c.ok for c in self.checagens if c.bloqueante)

    def resumo(self) -> str:
        linhas = [f"{self.total_linhas:,} linhas · {'APROVADO' if self.aprovado else 'REPROVADO'}"]
        for c in self.checagens:
            marca = "ok " if c.ok else ("ERRO" if c.bloqueante else "aviso")
            linhas.append(f"  [{marca}] {c.nome}: {c.linhas_afetadas:,} linhas {c.detalhe}".rstrip())
        return "\n".join(linhas)


class ContratoViolado(Exception):
    def __init__(self, relatorio: Relatorio):
        super().__init__(relatorio.resumo())
        self.relatorio = relatorio


class ValidadorPrata:
    """Regras configuráveis. Limiares em fração do total de linhas."""

    def __init__(self, max_nao_classificado: float = 0.30, max_sem_massa: float = 0.05,
                 ano_min: int = 2000, ano_max: int = 2100):
        self.max_nc = max_nao_classificado
        self.max_sem_massa = max_sem_massa
        self.ano_min, self.ano_max = ano_min, ano_max

    def validar(self, df: pd.DataFrame) -> Relatorio:
        n = len(df)
        rel = Relatorio(n)
        frac = (lambda k: k / n) if n else (lambda k: 0.0)

        def add(nome, afetadas, bloqueante, limite=0.0, detalhe=""):
            ok = frac(afetadas) <= limite
            rel.checagens.append(Checagem(nome, ok, int(afetadas), bloqueante, detalhe))

        rel.checagens.append(Checagem("arquivo não vazio", n > 0, 0 if n else 1, True))
        add("massa negativa", (df["massa_t"] < 0).sum(), True)
        add("massa ausente/não numérica", df["massa_t"].isna().sum(), True, self.max_sem_massa,
            f"(limite {self.max_sem_massa:.0%})")
        uf_preenchida = df["uf"].fillna("").astype(str).str.len() > 0
        add("UF inexistente", (uf_preenchida & ~df["uf"].isin(UFS)).sum(), True)
        anos = df["ano"].dropna()
        add("ano fora do intervalo", ((anos < self.ano_min) | (anos > self.ano_max)).sum(), True)
        add("não classificado", (df["cat_id"] == "nc").sum(), False, self.max_nc,
            f"(limite {self.max_nc:.0%})")
        add("destinação não informada", (df["destinacao"] == "Não informada").sum(), False, 0.5)
        return rel

    def exigir(self, df: pd.DataFrame) -> Relatorio:
        rel = self.validar(df)
        if not rel.aprovado:
            raise ContratoViolado(rel)
        return rel
