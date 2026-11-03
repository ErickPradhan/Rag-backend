"""Talks to the LLM and the embedding model (any OpenAI-compatible provider)."""
from __future__ import annotations

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.config import Settings


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
        self._chat_model = settings.llm_model
        self._embedding_model = settings.embedding_model
        self._dim = settings.embedding_dim

    def chat(self, messages: list[ChatCompletionMessageParam], *, json_mode: bool = False) -> str:
        if json_mode:
            resp = self._client.chat.completions.create(
                model=self._chat_model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
        else:
            resp = self._client.chat.completions.create(
                model=self._chat_model, messages=messages, temperature=0.2
            )
        return resp.choices[0].message.content or ""

    def embed(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = self._client.embeddings.create(
                model=self._embedding_model, input=batch, dimensions=self._dim
            )
            vectors.extend(item.embedding for item in resp.data)
        return vectors
