"""Conversational RAG with interview booking (custom: no RetrievalQAChain)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Literal

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import Booking
from app.schemas import ChatMessage, ChatResponse, SourceChunk
from app.services.llm import LLMClient
from app.services.memory import ChatMemory
from app.services.vector_store import RetrievedChunk, VectorStore

BOOKING_FIELDS: tuple[str, ...] = ("name", "email", "date", "time")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Analysis(BaseModel):
    """What the LLM understood from the latest user message."""

    intent: Literal["question", "booking"] = "question"
    standalone_question: str | None = None
    name: str | None = None
    email: str | None = None
    date: str | None = None
    time: str | None = None

    def booking_fields(self) -> dict[str, str]:
        found = {f: getattr(self, f) for f in BOOKING_FIELDS}
        return {k: v.strip() for k, v in found.items() if v and v.strip()}


def _analysis_prompt(pending: dict[str, str]) -> str:
    return (
        "You analyse the latest message of a chat between a user and an assistant.\n"
        f"Today's date is {date.today().isoformat()}.\n"
        f"Booking details already collected: {json.dumps(pending)}\n\n"
        "Return ONLY a JSON object with these keys:\n"
        '- "intent": "booking" if the user wants to book/schedule an interview or is '
        'giving booking details, otherwise "question".\n'
        '- "standalone_question": the user\'s message rewritten so it makes sense without '
        "the earlier chat (resolve words like 'it' or 'that'). Same as the message if already clear.\n"
        '- "name", "email": taken from the latest message only, else null.\n'
        '- "date": as YYYY-MM-DD (work out words like "tomorrow" or "next Friday"), else null.\n'
        '- "time": 24-hour HH:MM, else null.\n'
        "Never invent values the user did not state."
    )


def _validate_booking(fields: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Keep only valid fields; return (clean_fields, problems)."""
    clean: dict[str, str] = {}
    problems: list[str] = []
    for key, value in fields.items():
        if key == "email" and not EMAIL_RE.match(value):
            problems.append("that email address doesn't look valid")
        elif key == "date":
            try:
                if date.fromisoformat(value) < date.today():
                    problems.append("that date is in the past")
                else:
                    clean[key] = value
            except ValueError:
                problems.append("I couldn't understand that date")
        elif key == "time":
            try:
                datetime.strptime(value, "%H:%M")
                clean[key] = value
            except ValueError:
                problems.append("I couldn't understand that time")
        else:
            clean[key] = value
    return clean, problems


class ChatService:
    def __init__(
        self, llm: LLMClient, store: VectorStore, memory: ChatMemory, settings: Settings
    ) -> None:
        self._llm = llm
        self._store = store
        self._memory = memory
        self._top_k = settings.top_k

    # ---- public entry point -------------------------------------------------
    def handle(self, session_id: str, message: str, db: Session) -> ChatResponse:
        history = self._memory.get_history(session_id)
        pending = self._memory.get_pending_booking(session_id)
        analysis = self._analyze(message, history, pending)
        new_fields = analysis.booking_fields()

        sources: list[SourceChunk] = []
        booking_id: int | None = None
        if analysis.intent == "booking" or (pending and new_fields):
            intent: Literal["question", "booking"] = "booking"
            answer, booking_id = self._booking_step(session_id, pending, new_fields, db)
        else:
            intent = "question"
            answer, sources = self._answer_question(
                message, analysis.standalone_question or message, history
            )

        self._memory.add_message(session_id, ChatMessage(role="user", content=message))
        self._memory.add_message(session_id, ChatMessage(role="assistant", content=answer))
        return ChatResponse(
            session_id=session_id, answer=answer, intent=intent, sources=sources, booking_id=booking_id
        )

    # ---- step 1: understand the message -------------------------------------
    def _analyze(
        self, message: str, history: list[ChatMessage], pending: dict[str, str]
    ) -> Analysis:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": _analysis_prompt(pending)}
        ]
        for m in history[-6:]:
            messages.append({"role": m.role, "content": m.content})  # type: ignore[arg-type]
        messages.append({"role": "user", "content": message})
        raw = self._llm.chat(messages, json_mode=True)
        raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
        try:
            return Analysis.model_validate_json(raw)
        except ValueError:
            return Analysis(standalone_question=message)

    # ---- step 2a: normal question -> retrieve + answer ----------------------
    def _answer_question(
        self, message: str, standalone: str, history: list[ChatMessage]
    ) -> tuple[str, list[SourceChunk]]:
        query_vector = self._llm.embed([standalone])[0]
        chunks: list[RetrievedChunk] = self._store.search(query_vector, self._top_k)
        context = "\n\n".join(f"[{c.filename}] {c.text}" for c in chunks) or "(no documents found)"

        system = (
            "You are a helpful assistant. Answer using ONLY the context below. "
            "If the answer is not in the context, say you don't know. "
            "Be concise. Users can also ask you to book an interview.\n\n"
            f"CONTEXT:\n{context}"
        )
        messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": system}]
        for m in history:
            messages.append({"role": m.role, "content": m.content})  # type: ignore[arg-type]
        messages.append({"role": "user", "content": message})

        answer = self._llm.chat(messages)
        sources = [SourceChunk(filename=c.filename, text=c.text, score=c.score) for c in chunks]
        return answer, sources

    # ---- step 2b: interview booking -----------------------------------------
    def _booking_step(
        self, session_id: str, pending: dict[str, str], new_fields: dict[str, str], db: Session
    ) -> tuple[str, int | None]:
        clean, problems = _validate_booking(new_fields)
        details = {**pending, **clean}
        missing = [f for f in BOOKING_FIELDS if f not in details]

        if missing:
            self._memory.set_pending_booking(session_id, details)
            note = f"Sorry, {' and '.join(problems)}. " if problems else ""
            labels = {"name": "full name", "email": "email", "date": "preferred date", "time": "preferred time"}
            asked = ", ".join(labels[m] for m in missing)
            return f"{note}Happy to book your interview! I still need your {asked}.", None

        booking = Booking(session_id=session_id, **details)
        db.add(booking)
        db.commit()
        self._memory.clear_pending_booking(session_id)
        return (
            f"Done! Interview booked for {details['name']} on {details['date']} at "
            f"{details['time']}. Your email on file is {details['email']}. "
            f"(Booking #{booking.id})",
            booking.id,
        )
