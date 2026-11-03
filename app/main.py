"""FastAPI application entry point."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.deps import get_vector_store
from app.routers import chat, ingestion


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    get_vector_store().ensure_collection()
    yield


app = FastAPI(title="Palm Mind RAG Backend", version="1.0.0", lifespan=lifespan)
app.include_router(ingestion.router)
app.include_router(chat.router)
