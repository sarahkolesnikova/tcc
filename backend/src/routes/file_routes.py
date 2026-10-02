"""Rotas de arquivos: upload, consulta e exclusão."""
from __future__ import annotations

import hashlib
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..deps import Contexto, get_contexto
from ..models.schemas import ArquivoResposta
from ..models.storage import agora
from ..services.io import MAX_BYTES, ArquivoInvalido, inferir_tipos, ler_planilha

router = APIRouter(prefix="/api/files", tags=["arquivos"])

CONTENT_TYPES = {"csv": "text/csv",
                 "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                 "xls": "application/vnd.ms-excel"}


def _limpar(ctx: Contexto):
    for fid in ctx.storage.limpar_expirados(ctx.cfg.file_ttl_minutes):
        ctx.esquecer(fid)


def _resposta(rec: dict) -> dict:
    return {"file_id": rec["id"], "filename": rec["filename"], "size_bytes": rec["size_bytes"],
            "rows": rec["rows"], "sha256": rec["sha256"], "created_at": rec["created_at"],
            "columns": rec["columns"]}


@router.post("/upload", response_model=ArquivoResposta, status_code=201)
async def upload(file: UploadFile = File(...), ctx: Contexto = Depends(get_contexto)):
    _limpar(ctx)
    raw = await file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "Arquivo maior que 50 MB.")
    nome = file.filename or "arquivo"
    try:
        df = ler_planilha(raw, nome)
    except ArquivoInvalido as e:
        raise HTTPException(422, str(e)) from e
    fid = str(uuid.uuid4())
    ext = nome.rsplit(".", 1)[-1].lower()
    rec = {"id": fid, "filename": nome, "storage_key": f"{fid}.{ext}", "size_bytes": len(raw),
           "sha256": hashlib.sha256(raw).hexdigest(), "rows": len(df), "columns": inferir_tipos(df),
           "created_at": agora().isoformat()}
    ctx.storage.put_object(rec["storage_key"], raw, CONTENT_TYPES.get(ext, "application/octet-stream"))
    ctx.storage.insert_file(rec)
    ctx.dataframes.set(fid, df)
    return _resposta(rec)


@router.get("/{file_id}", response_model=ArquivoResposta)
def obter(file_id: str, ctx: Contexto = Depends(get_contexto)):
    _limpar(ctx)
    rec = ctx.storage.get_file(file_id)
    if not rec:
        raise HTTPException(404, "Arquivo não encontrado ou expirado. Envie a planilha novamente.")
    return _resposta(rec)


@router.delete("/{file_id}", status_code=204)
def excluir(file_id: str, ctx: Contexto = Depends(get_contexto)):
    rec = ctx.storage.get_file(file_id)
    if not rec:
        raise HTTPException(404, "Arquivo não encontrado.")
    ctx.storage.delete_object(rec["storage_key"])
    ctx.storage.delete_file(file_id)
    ctx.esquecer(file_id)
