"""Contrato das fontes de dados (padrão Strategy)."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import requests

log = logging.getLogger(__name__)


class Extractor(ABC):
    """Uma fonte pública. `extract()` devolve o caminho do arquivo bruto (camada raw)."""

    fonte: str = "abstrata"

    def __init__(self, raw_dir: Path, session: requests.Session | None = None, timeout: int = 120):
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.session = session or requests.Session()
        self.timeout = timeout

    @abstractmethod
    def extract(self, **kwargs) -> Path:
        ...

    def baixar(self, url: str, nome: str, forcar: bool = False) -> Path:
        destino = self.raw_dir / nome
        if destino.exists() and not forcar:
            log.info("cache %s", destino)
            return destino
        log.info("download %s", url)
        tmp = destino.with_suffix(destino.suffix + ".part")
        with self.session.get(url, stream=True, timeout=self.timeout) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        tmp.replace(destino)  # grava atomicamente: download interrompido não vira cache
        return destino


class ArquivoLocalExtractor(Extractor):
    """Usa um CSV já baixado (Ibama, planilha municipal do SINIR ou saída de outro sistema)."""

    fonte = "arquivo_local"

    def __init__(self, caminho: Path, raw_dir: Path | None = None):
        self.caminho = Path(caminho)
        super().__init__(raw_dir or self.caminho.parent)

    def extract(self, **kwargs) -> Path:
        if not self.caminho.exists():
            raise FileNotFoundError(self.caminho)
        return self.caminho
