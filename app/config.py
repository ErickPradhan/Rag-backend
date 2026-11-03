"""Application settings, read from environment variables / the .env file."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM + embeddings (any OpenAI-compatible provider)
    llm_api_key: str
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_model: str = "gemini-3.5-flash"
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    # Vector database (Qdrant)
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_local_path: str = "./qdrant_data"
    qdrant_collection: str = "documents"

    # Redis chat memory
    redis_url: str = "redis://localhost:6379/0"
    chat_history_limit: int = 10  # messages kept per session
    chat_ttl_seconds: int = 60 * 60 * 24

    # SQL metadata database
    database_url: str = "sqlite:///./app.db"

    # RAG / upload behaviour
    top_k: int = 4
    max_upload_mb: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
