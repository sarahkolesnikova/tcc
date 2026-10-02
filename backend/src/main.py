"""Anomaly Detector — API. Rode: uvicorn src.main:app --reload (na pasta backend)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .deps import get_contexto
from .routes import file_routes, model_routes

app = FastAPI(title="Anomaly Detector", version="1.0.0",
              description="Detecção de inconsistências e erros em planilhas CSV, XLSX e XLS.")
app.add_middleware(CORSMiddleware, allow_origins=list(Settings.from_env().cors_origins),
                   allow_methods=["*"], allow_headers=["*"],
                   expose_headers=["Content-Disposition"])
app.include_router(file_routes.router)
app.include_router(model_routes.router)


@app.get("/api/health")
def health():
    ctx = get_contexto()
    return {"status": "ok", "storage": "supabase" if ctx.cfg.usa_supabase else "local"}
