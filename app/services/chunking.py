"""Two ways of cutting text into chunks."""
from __future__ import annotations

import re
from enum import Enum


class ChunkingStrategy(str, Enum):
    FIXED = "fixed"        # equal-size windows with overlap
    SENTENCE = "sentence"  # keeps whole sentences together


def chunk_fixed(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    """Cut every `size` characters, stepping back `overlap` so context isn't lost."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    step = size - overlap
    chunks: list[str] = []
    for start in range(0, len(text), step):
        piece = text[start : start + size].strip()
        if piece:
            chunks.append(piece)
    return chunks


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def chunk_sentences(text: str, max_chars: int = 800) -> list[str]:
    """Pack whole sentences into chunks of at most `max_chars` characters."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:  # one giant sentence: fall back to fixed cutting
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(chunk_fixed(sentence, max_chars, max_chars // 8))
        elif current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


def chunk_text(text: str, strategy: ChunkingStrategy) -> list[str]:
    if strategy is ChunkingStrategy.FIXED:
        return chunk_fixed(text)
    return chunk_sentences(text)
