"""Rotas de modelos e relatórios: listagem, geração, CSV e PDF."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from ..deps import Contexto, get_contexto
from ..models.schemas import GerarRelatorio, ModelosResposta
from ..models.storage import agora
from ..services import registry
from ..services.export_pdf import gerar_pdf
from ..services.report import Parametros, ParametrosInvalidos, executar, montar_relatorio, tabela_marcada

router = APIRouter(prefix="/api/report", tags=["relatórios"])


def _lista(v: str | None) -> tuple[str, ...]:
    return tuple(x for x in (v or "").split(",") if x)


def _gerar(file_id: str, params: Parametros, ctx: Contexto):
    rec = ctx.storage.get_file(file_id)
    if not rec:
        raise HTTPException(404, "Arquivo não encontrado ou expirado. Envie a planilha novamente.")
    chave = f"{file_id}:{params.chave()}"
    em_cache = ctx.relatorios.get(chave)
    if em_cache:
        return rec, *em_cache
    df = ctx.dataframe(file_id, rec)
    try:
        resultados = executar(df, params)
    except ParametrosInvalidos as e:
        raise HTTPException(422, str(e)) from e
    arquivo = {k: rec[k] for k in ("id", "filename", "sha256", "size_bytes", "rows")}
    rel = montar_relatorio(df, params, resultados, arquivo)
    ctx.storage.insert_analysis({"id": str(uuid.uuid4()), "file_id": file_id, "filename": rec["filename"],
                                 "sha256": rec["sha256"], "parameters": rel["parameters"],
                                 "summary": {**rel["summary"],
                                             "por_modelo": {m["id"]: m["anomalies"] for m in rel["models"]}},
                                 "created_at": agora().isoformat()})
    ctx.relatorios.set(chave, (df, resultados, rel))
    return rec, df, resultados, rel


def _params_query(models, numeric_columns, categorical_columns, threshold) -> Parametros:
    return Parametros(_lista(models), _lista(numeric_columns), _lista(categorical_columns), threshold)


@router.get("/models", response_model=ModelosResposta)
def modelos():
    return registry.listar()


@router.post("/generate/{file_id}")
def gerar(file_id: str, body: GerarRelatorio, ctx: Contexto = Depends(get_contexto)):
    params = Parametros(tuple(body.models), tuple(body.numeric_columns), tuple(body.categorical_columns),
                        body.threshold)
    return _gerar(file_id, params, ctx)[3]


@router.get("/cleaned/{file_id}")
def csv_limpo(file_id: str, models: str = Query(...), numeric_columns: str = "", categorical_columns: str = "",
              threshold: float = Query(0.05, gt=0, lt=0.5),
              remover: bool = Query(False, description="True: devolve só as linhas não sinalizadas"),
              ctx: Contexto = Depends(get_contexto)):
    rec, df, resultados, _ = _gerar(file_id, _params_query(models, numeric_columns, categorical_columns, threshold), ctx)
    corpo = tabela_marcada(df, resultados, remover).to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    base = rec["filename"].rsplit(".", 1)[0]
    sufixo = "sem_anomalias" if remover else "anomalias"
    return Response(corpo, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{base}_{sufixo}.csv"'})


@router.get("/pdf/{file_id}")
def pdf(file_id: str, models: str = Query(...), numeric_columns: str = "", categorical_columns: str = "",
        threshold: float = Query(0.05, gt=0, lt=0.5), ctx: Contexto = Depends(get_contexto)):
    rec, _, _, rel = _gerar(file_id, _params_query(models, numeric_columns, categorical_columns, threshold), ctx)
    base = rec["filename"].rsplit(".", 1)[0]
    return Response(gerar_pdf(rel), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{base}_relatorio.pdf"'})


@router.get("/history")
def historico(file_id: str | None = None, ctx: Contexto = Depends(get_contexto)):
    """Histórico de análises; permanece mesmo depois que o arquivo expira."""
    return ctx.storage.list_analyses(file_id)
