"""Qdrant vector database wrapper."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import Settings


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    filename: str
    score: float


class VectorStore:
    def __init__(self, settings: Settings) -> None:
        if settings.qdrant_url:
            self._client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        else:  # no server needed: stores vectors in a local folder
            self._client = QdrantClient(path=settings.qdrant_local_path)
        self._collection = settings.qdrant_collection
        self._dim = settings.embedding_dim

    def ensure_collection(self) -> None:
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                self._collection,
                vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE),
            )

    def add_chunks(
        self, document_id: str, filename: str, chunks: list[str], vectors: list[list[float]]
    ) -> None:
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": index,
                    "text": chunk,
                },
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        self._client.upsert(self._collection, points=points)

    def search(self, vector: list[float], top_k: int) -> list[RetrievedChunk]:
        result = self._client.query_points(
            self._collection, query=vector, limit=top_k, with_payload=True
        )
        return [
            RetrievedChunk(
                text=str((p.payload or {}).get("text", "")),
                filename=str((p.payload or {}).get("filename", "")),
                score=p.score,
            )
            for p in result.points
        ]
