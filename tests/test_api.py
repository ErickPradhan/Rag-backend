"""End-to-end test with a fake LLM and fake Redis (no internet needed)."""
from __future__ import annotations

import json
import os

os.environ.setdefault("LLM_API_KEY", "test")
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["QDRANT_LOCAL_PATH"] = "./test_qdrant"
os.environ["EMBEDDING_DIM"] = "8"

import fakeredis
from fastapi.testclient import TestClient

from app import deps
from app.config import get_settings
from app.main import app
from app.services.memory import ChatMemory


class FakeLLM:
    def embed(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        return [[float(len(t) % 7 + 1)] * 8 for t in texts]

    def chat(self, messages, *, json_mode: bool = False) -> str:  # type: ignore[no-untyped-def]
        if json_mode:
            last = messages[-1]["content"].lower()
            if "book" in last:
                return json.dumps({"intent": "booking", "name": "Vanitas"})
            if "@" in last:
                return json.dumps({"intent": "booking", "email": "v@x.com", "date": "2099-01-05", "time": "14:00"})
            return json.dumps({"intent": "question", "standalone_question": last})
        return "fake answer"


def test_full_flow() -> None:
    s = get_settings()
    deps.get_llm.cache_clear()
    deps.get_llm = lambda: FakeLLM()  # type: ignore[assignment]
    deps.get_memory = lambda: ChatMemory(fakeredis.FakeStrictRedis(decode_responses=True), 10, 60)  # type: ignore[assignment]
    memory = deps.get_memory()
    deps.get_memory = lambda: memory  # type: ignore[assignment]

    with TestClient(app) as client:
        for strat in ("fixed", "sentence"):
            r = client.post("/documents/ingest", files={"file": ("a.txt", b"Hello world. " * 200)}, data={"chunking_strategy": strat})
            assert r.status_code == 201 and r.json()["chunk_count"] > 0
        assert client.post("/documents/ingest", files={"file": ("a.docx", b"x")}).status_code == 415

        r = client.post("/chat", json={"message": "What is in the doc?"})
        assert r.json()["intent"] == "question" and r.json()["sources"]
        sid = r.json()["session_id"]

        r = client.post("/chat", json={"session_id": sid, "message": "I want to book an interview"})
        assert "still need" in r.json()["answer"]
        r = client.post("/chat", json={"session_id": sid, "message": "v@x.com, Jan 5 2099 at 2pm"})
        assert r.json()["booking_id"] is not None
        assert len(client.get("/bookings").json()) >= 1
