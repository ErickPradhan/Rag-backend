"""Redis-backed chat memory (+ a half-finished booking per chat session)."""
from __future__ import annotations

import json

from redis import Redis

from app.schemas import ChatMessage


class ChatMemory:
    def __init__(self, client: "Redis[str]", history_limit: int, ttl_seconds: int) -> None:
        self._r = client
        self._limit = history_limit
        self._ttl = ttl_seconds

    def _hist_key(self, session_id: str) -> str:
        return f"chat:{session_id}:history"

    def _booking_key(self, session_id: str) -> str:
        return f"chat:{session_id}:pending_booking"

    def get_history(self, session_id: str) -> list[ChatMessage]:
        raw = self._r.lrange(self._hist_key(session_id), 0, -1)
        return [ChatMessage.model_validate_json(item) for item in raw]

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        key = self._hist_key(session_id)
        self._r.rpush(key, message.model_dump_json())
        self._r.ltrim(key, -self._limit, -1)  # keep only the latest N messages
        self._r.expire(key, self._ttl)

    def get_pending_booking(self, session_id: str) -> dict[str, str]:
        raw = self._r.get(self._booking_key(session_id))
        return json.loads(raw) if raw else {}

    def set_pending_booking(self, session_id: str, fields: dict[str, str]) -> None:
        self._r.set(self._booking_key(session_id), json.dumps(fields), ex=self._ttl)

    def clear_pending_booking(self, session_id: str) -> None:
        self._r.delete(self._booking_key(session_id))
