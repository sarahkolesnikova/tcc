"""MMA/SINIR — planilhas do módulo Estados e Municípios, publicadas no CKAN do MMA."""
from __future__ import annotations

from pathlib import Path

from .base import Extractor

CKAN = "https://dados.mma.gov.br/api/3/action"


class SinirExtractor(Extractor):
    """Lista os recursos do pacote `sinir` e baixa o escolhido (por ano ou índice)."""

    fonte = "sinir_mma"

    def recursos(self) -> list[dict]:
        r = self.session.get(f"{CKAN}/package_show", params={"id": "sinir"}, timeout=60)
        r.raise_for_status()
        return [
            {"nome": x.get("name", ""), "formato": (x.get("format") or "").upper(), "url": x["url"]}
            for x in r.json()["result"]["resources"]
        ]

    def extract(self, ano: int | None = None, indice: int = 0, forcar: bool = False, **kwargs) -> Path:
        recursos = self.recursos()
        if ano is not None:
            recursos = [x for x in recursos if str(ano) in x["nome"]] or recursos
        if not recursos:
            raise LookupError("Nenhum recurso no pacote sinir")
        alvo = recursos[indice]
        extensao = Path(alvo["url"].split("?")[0]).suffix or ".bin"
        return self.baixar(alvo["url"], f"sinir_{ano or 'ultimo'}{extensao}", forcar)
