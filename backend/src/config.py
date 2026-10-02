"""Configuração por variáveis de ambiente (.env carregado via python-dotenv)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
RAIZ = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    supabase_url: str | None
    supabase_key: str | None
    supabase_bucket: str
    local_data_dir: Path
    file_ttl_minutes: int
    cors_origins: tuple[str, ...]

    @property
    def usa_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @classmethod
    def from_env(cls) -> "Settings":
        e = os.environ.get
        return cls(
            supabase_url=e("SUPABASE_URL") or None,
            supabase_key=e("SUPABASE_KEY") or None,
            supabase_bucket=e("SUPABASE_BUCKET", "uploads"),
            local_data_dir=Path(e("LOCAL_DATA_DIR", str(RAIZ / "data"))),
            file_ttl_minutes=int(e("FILE_TTL_MINUTES", "10")),
            cors_origins=tuple(o.strip() for o in e("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()),
        )
