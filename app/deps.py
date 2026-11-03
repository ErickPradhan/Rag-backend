"""Builds the shared services once and hands them to the routes."""
from __future__ import annotations

from functools import lru_cache

from redis import Redis

from app.config import get_settings
from app.services.chat_service import ChatService
from app.services.ingestion import IngestionService
from app.services.llm import LLMClient
from app.services.memory import ChatMemory
from app.services.vector_store import VectorStore


@lru_cache
def get_llm() -> LLMClient:
    return LLMClient(get_settings())


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore(get_settings())


@lru_cache
def get_memory() -> ChatMemory:
    s = get_settings()
    client: Redis[str] = Redis.from_url(s.redis_url, decode_responses=True)
    return ChatMemory(client, s.chat_history_limit, s.chat_ttl_seconds)


def get_ingestion_service() -> IngestionService:
    return IngestionService(get_llm(), get_vector_store())


def get_chat_service() -> ChatService:
    return ChatService(get_llm(), get_vector_store(), get_memory(), get_settings())
