"""API 1: Document ingestion."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_ingestion_service
from app.schemas import IngestResponse
from app.services.chunking import ChunkingStrategy
from app.services.extraction import SUPPORTED_EXTENSIONS, UnsupportedFileError, get_extension
from app.services.ingestion import EmptyDocumentError, IngestionService

router = APIRouter(prefix="/documents", tags=["Document Ingestion"])


@router.post("/ingest", response_model=IngestResponse, status_code=201)
def ingest_document(
    file: Annotated[UploadFile, File(description=".pdf or .txt file")],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
    chunking_strategy: Annotated[ChunkingStrategy, Form()] = ChunkingStrategy.FIXED,
) -> IngestResponse:
    filename = file.filename or "unnamed"
    if get_extension(filename) not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only .pdf and .txt files are supported")

    content = file.file.read()
    if len(content) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    try:
        doc = service.ingest(filename, content, chunking_strategy, db)
    except (UnsupportedFileError, EmptyDocumentError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return IngestResponse(
        document_id=doc.id,
        filename=doc.filename,
        chunking_strategy=chunking_strategy,
        chunk_count=doc.chunk_count,
    )
