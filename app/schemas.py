"""Request / response models (what the API accepts and returns)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.services.chunking import ChunkingStrategy


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    chunking_strategy: ChunkingStrategy
    chunk_count: int


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, description="Leave empty to start a new chat")
    message: str = Field(min_length=1)


class SourceChunk(BaseModel):
    filename: str
    text: str
    score: float


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    intent: Literal["question", "booking"]
    sources: list[SourceChunk] = []
    booking_id: int | None = None


class BookingOut(BaseModel):
    id: int
    session_id: str
    name: str
    email: str
    date: str
    time: str
    created_at: datetime

    model_config = {"from_attributes": True}
