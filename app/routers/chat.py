"""API 2: Conversational RAG (+ interview booking)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Booking, get_db
from app.deps import get_chat_service
from app.schemas import BookingOut, ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(tags=["Conversational RAG"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    session_id = request.session_id or str(uuid.uuid4())
    return service.handle(session_id, request.message, db)


@router.get("/bookings", response_model=list[BookingOut])
def list_bookings(db: Annotated[Session, Depends(get_db)]) -> list[Booking]:
    return list(db.scalars(select(Booking).order_by(Booking.id)))
