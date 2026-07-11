from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.schemas.kb_debug import (
    KBDebugEvalRequest,
    KBDebugFeedbackRequest,
    KBDebugFileRequest,
    KBDebugIndexRequest,
    KBDebugPreviewRequest,
    KBDebugSearchRequest,
)
from app.services.embedding_service import EmbeddingError
from app.services.kb_debug_service import KBDebugService, get_kb_debug_service_singleton

router = APIRouter(prefix="/knowledge/debug", tags=["knowledge-debug"])
_sync_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="kb-debug")


async def _run_sync(func, /, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_sync_pool, partial(func, *args, **kwargs))


def require_kb_debug(settings: Settings = Depends(get_settings)) -> Settings:
    if not settings.kb_debug_enabled:
        raise HTTPException(status_code=404, detail="Not Found")
    return settings


def get_kb_debug_service(settings: Settings = Depends(require_kb_debug)) -> KBDebugService:
    return get_kb_debug_service_singleton(settings)


@router.get("/files")
def kb_debug_list_files(svc: KBDebugService = Depends(get_kb_debug_service)):
    try:
        files = svc.list_corpus_files()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"code": 200, "data": {"items": files}}


@router.post("/preview-file")
async def kb_debug_preview_file(body: KBDebugFileRequest, svc: KBDebugService = Depends(get_kb_debug_service)):
    try:
        path = Path(body.corpus_path) if body.corpus_path else None
        report = await _run_sync(svc.preview_file, body.filename, path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"code": 200, "data": report}


@router.get("/status")
def kb_debug_status(svc: KBDebugService = Depends(get_kb_debug_service)):
    return {"code": 200, "data": svc.get_status()}


@router.post("/preview-ingest")
async def kb_debug_preview(body: KBDebugPreviewRequest, svc: KBDebugService = Depends(get_kb_debug_service)):
    try:
        path = Path(body.corpus_path) if body.corpus_path else None
        report = await _run_sync(svc.preview_ingest, path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"code": 200, "data": report}


@router.get("/chunks")
def kb_debug_list_chunks(
    doc_type: str | None = None,
    source_file: str | None = None,
    limit: int = Query(50, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    svc: KBDebugService = Depends(get_kb_debug_service),
):
    return {
        "code": 200,
        "data": svc.list_chunks(doc_type=doc_type, source_file=source_file, limit=limit, offset=offset),
    }


@router.get("/chunks/{chunk_id}")
def kb_debug_get_chunk(chunk_id: str, svc: KBDebugService = Depends(get_kb_debug_service)):
    chunk = svc.get_chunk(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return {"code": 200, "data": chunk}


@router.post("/index")
async def kb_debug_index(body: KBDebugIndexRequest, svc: KBDebugService = Depends(get_kb_debug_service)):
    try:
        path = Path(body.corpus_path) if body.corpus_path else None
        if body.filename:
            result = await _run_sync(svc.index_file, body.filename, path, clear=body.clear)
        else:
            result = await _run_sync(svc.index_corpus, path, clear=body.clear)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"code": 200, "data": result}


@router.post("/search")
def kb_debug_search(body: KBDebugSearchRequest, svc: KBDebugService = Depends(get_kb_debug_service)):
    try:
        results = svc.search(
            body.query,
            top_k=body.top_k,
            function_filter=body.function_filter,
            doc_type_filter=body.doc_type_filter,
        )
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"code": 200, "data": {"results": results}}


@router.post("/feedback")
def kb_debug_feedback(body: KBDebugFeedbackRequest, svc: KBDebugService = Depends(get_kb_debug_service)):
    try:
        record = svc.submit_feedback(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"code": 200, "data": record}


@router.post("/eval/run")
async def kb_debug_eval(body: KBDebugEvalRequest, svc: KBDebugService = Depends(get_kb_debug_service)):
    try:
        payload = [q.model_dump() for q in body.queries]
        result = await _run_sync(svc.run_eval, payload, top_k=body.top_k)
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"code": 200, "data": result}
