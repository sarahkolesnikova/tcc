"""Ibama — Relatório Anual de Atividades Potencialmente Poluidoras (RAPP), formulários de resíduos."""
from __future__ import annotations

from pathlib import Path

from .base import Extractor

BASE = "https://dadosabertos.ibama.gov.br/dados/RAPP"
CKAN = "https://dadosabertos.ibama.gov.br/api/3/action"
FORMULARIOS = {
    "destinador": f"{BASE}/residuoSolidosDestinador/relatorio.csv",
    "gerador": f"{BASE}/residuoSolidosGerador/relatorio.csv",
    "armazenador": f"{BASE}/residuoSolidosArmazenador/relatorio.csv",
}


class IbamaExtractor(Extractor):
    """Baixa UM formulário do RAPP.

    Gerador, Destinador e Armazenador descrevem o mesmo resíduo em pontos diferentes
    da cadeia; somar mais de um formulário conta a mesma tonelada várias vezes.
    """

    fonte = "ibama_rapp"

    def __init__(self, raw_dir: Path, formulario: str = "destinador", **kw):
        if formulario not in FORMULARIOS:
            raise ValueError(f"formulário inválido: {formulario}. Use {sorted(FORMULARIOS)}")
        super().__init__(raw_dir, **kw)
        self.formulario = formulario

    def extract(self, forcar: bool = False, **kwargs) -> Path:
        return self.baixar(FORMULARIOS[self.formulario], f"rapp_{self.formulario}.csv", forcar)

    def listar_conjuntos(self, query: str = "residuos") -> list[dict]:
        r = self.session.get(f"{CKAN}/package_search", params={"q": query, "rows": 50}, timeout=60)
        r.raise_for_status()
        return [
            {"id": p["name"], "titulo": p["title"],
             "recursos": [{"formato": x.get("format"), "url": x.get("url")} for x in p.get("resources", [])]}
            for p in r.json()["result"]["results"]
        ]
