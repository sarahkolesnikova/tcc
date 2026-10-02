"""Modelos Pydantic da API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Coluna(BaseModel):
    name: str
    type: Literal["numeric", "categorical"]
    missing: int
    unique: int


class ArquivoResposta(BaseModel):
    file_id: str
    filename: str
    size_bytes: int
    rows: int
    sha256: str
    created_at: str
    columns: list[Coluna]


class ModeloInfo(BaseModel):
    id: str
    name: str
    type: Literal["numeric", "categorical"]
    description: str


class ModelosResposta(BaseModel):
    numeric: list[ModeloInfo]
    categorical: list[ModeloInfo]


class GerarRelatorio(BaseModel):
    models: list[str] = Field(min_length=1)
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []
    threshold: float = Field(0.05, gt=0, lt=0.5, description="Contaminação esperada (fração de anomalias)")
