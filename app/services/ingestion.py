"""Document ingestion: extract -> chunk -> embed -> store vectors -> save metadata."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import Document
from app.services.chunking import ChunkingStrategy, chunk_text
from app.services.extraction import extract_text, get_extension
from app.services.llm import LLMClient
from app.services.vector_store import VectorStore


class EmptyDocumentError(ValueError):
    pass


class IngestionService:
    def __init__(self, llm: LLMClient, store: VectorStore) -> None:
        self._llm = llm
        self._store = store

    def ingest(
        self, filename: str, content: bytes, strategy: ChunkingStrategy, db: Session
    ) -> Document:
        text = extract_text(filename, content)
        chunks = chunk_text(text, strategy)
        if not chunks:
            raise EmptyDocumentError("No readable text found in this file.")

        vectors = self._llm.embed(chunks)
        document = Document(
            filename=filename,
            file_type=get_extension(filename).lstrip("."),
            chunking_strategy=strategy.value,
            chunk_count=len(chunks),
        )
        db.add(document)
        db.flush()  # gives the document its id before we save vectors
        self._store.add_chunks(document.id, filename, chunks, vectors)
        db.commit()
        return document
