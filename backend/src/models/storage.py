"""Persistência: Supabase (PostgreSQL + Object Storage) ou fallback local (SQLite + disco).

A interface é a mesma nos dois casos, então rotas e serviços não sabem qual está ativa.
O fallback local existe para desenvolvimento, testes e demonstração sem credenciais.

Rastreabilidade: o arquivo enviado é apagado após FILE_TTL_MINUTES (privacidade), mas o
registro de cada ANÁLISE (nome, SHA-256 do conteúdo, modelos, parâmetros e contagens)
permanece na tabela `analyses`. Assim é possível provar o que foi analisado e com que
resultado sem guardar os dados do usuário indefinidamente.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..config import Settings


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Storage(ABC):
    # --- objetos (conteúdo do arquivo)
    @abstractmethod
    def put_object(self, key: str, data: bytes, content_type: str) -> None: ...
    @abstractmethod
    def get_object(self, key: str) -> bytes: ...
    @abstractmethod
    def delete_object(self, key: str) -> None: ...

    # --- metadados
    @abstractmethod
    def insert_file(self, rec: dict) -> None: ...
    @abstractmethod
    def get_file(self, file_id: str) -> dict | None: ...
    @abstractmethod
    def delete_file(self, file_id: str) -> None: ...
    @abstractmethod
    def files_older_than(self, limite: datetime) -> list[dict]: ...
    @abstractmethod
    def insert_analysis(self, rec: dict) -> None: ...
    @abstractmethod
    def list_analyses(self, file_id: str | None = None) -> list[dict]: ...

    def limpar_expirados(self, ttl_minutes: int) -> list[str]:
        """Apaga arquivos enviados há mais de `ttl_minutes`. Mantém o histórico de análises."""
        removidos = []
        for rec in self.files_older_than(agora() - timedelta(minutes=ttl_minutes)):
            try:
                self.delete_object(rec["storage_key"])
            except Exception:  # noqa: BLE001 - objeto já ausente não impede apagar o registro
                pass
            self.delete_file(rec["id"])
            removidos.append(rec["id"])
        return removidos


class LocalStorage(Storage):
    def __init__(self, base: Path):
        self.base = Path(base)
        (self.base / "objects").mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.base / "metadata.sqlite3", check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(self.DDL)

    # mesmas colunas de supabase/migrations/001_init.sql, com tipos do SQLite
    DDL = """
    create table if not exists files (id text primary key, filename text not null, storage_key text not null,
        size_bytes integer not null, sha256 text not null, rows integer not null, columns text not null,
        created_at text not null);
    create index if not exists files_created_at_idx on files (created_at);
    create table if not exists analyses (id text primary key, file_id text not null, filename text not null,
        sha256 text not null, parameters text not null, summary text not null, created_at text not null);
    create index if not exists analyses_file_idx on analyses (file_id);
    """

    def _path(self, key: str) -> Path:
        raiz = (self.base / "objects").resolve()
        p = (raiz / key).resolve()
        if raiz not in p.parents:
            raise ValueError("chave inválida")
        return p

    def put_object(self, key, data, content_type):
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get_object(self, key):
        return self._path(key).read_bytes()

    def delete_object(self, key):
        self._path(key).unlink(missing_ok=True)

    def insert_file(self, rec):
        with self._lock:
            self._db.execute("insert into files values (:id,:filename,:storage_key,:size_bytes,:sha256,:rows,:columns,:created_at)",
                             {**rec, "columns": json.dumps(rec["columns"], ensure_ascii=False)})
            self._db.commit()

    def _file(self, row) -> dict:
        d = dict(row)
        d["columns"] = json.loads(d["columns"])
        return d

    def get_file(self, file_id):
        with self._lock:
            row = self._db.execute("select * from files where id = ?", (file_id,)).fetchone()
        return self._file(row) if row else None

    def delete_file(self, file_id):
        with self._lock:
            self._db.execute("delete from files where id = ?", (file_id,))
            self._db.commit()

    def files_older_than(self, limite):
        with self._lock:
            rows = self._db.execute("select * from files where created_at < ?", (limite.isoformat(),)).fetchall()
        return [self._file(r) for r in rows]

    def insert_analysis(self, rec):
        with self._lock:
            self._db.execute("insert into analyses values (:id,:file_id,:filename,:sha256,:parameters,:summary,:created_at)",
                             {**rec, "parameters": json.dumps(rec["parameters"], ensure_ascii=False),
                              "summary": json.dumps(rec["summary"], ensure_ascii=False)})
            self._db.commit()

    def list_analyses(self, file_id=None):
        with self._lock:
            q = "select * from analyses" + (" where file_id = ?" if file_id else "") + " order by created_at"
            rows = self._db.execute(q, (file_id,) if file_id else ()).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["parameters"], d["summary"] = json.loads(d["parameters"]), json.loads(d["summary"])
            out.append(d)
        return out


class SupabaseStorage(Storage):
    """Usa a biblioteca oficial `supabase`. Tabelas e bucket: supabase/migrations/001_init.sql."""

    def __init__(self, url: str, key: str, bucket: str, client=None):
        if client is None:
            from supabase import create_client
            client = create_client(url, key)
        self.client = client
        self.bucket = bucket

    def put_object(self, key, data, content_type):
        self.client.storage.from_(self.bucket).upload(key, data, {"content-type": content_type, "upsert": "true"})

    def get_object(self, key):
        return self.client.storage.from_(self.bucket).download(key)

    def delete_object(self, key):
        self.client.storage.from_(self.bucket).remove([key])

    def insert_file(self, rec):
        self.client.table("files").insert(rec).execute()

    def get_file(self, file_id):
        data = self.client.table("files").select("*").eq("id", file_id).limit(1).execute().data
        return data[0] if data else None

    def delete_file(self, file_id):
        self.client.table("files").delete().eq("id", file_id).execute()

    def files_older_than(self, limite):
        return self.client.table("files").select("*").lt("created_at", limite.isoformat()).execute().data

    def insert_analysis(self, rec):
        self.client.table("analyses").insert(rec).execute()

    def list_analyses(self, file_id=None):
        q = self.client.table("analyses").select("*")
        if file_id:
            q = q.eq("file_id", file_id)
        return q.order("created_at").execute().data


def criar_storage(cfg: Settings) -> Storage:
    if cfg.usa_supabase:
        return SupabaseStorage(cfg.supabase_url, cfg.supabase_key, cfg.supabase_bucket)
    return LocalStorage(cfg.local_data_dir)
