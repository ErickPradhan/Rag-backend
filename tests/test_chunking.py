from app.services.chunking import ChunkingStrategy, chunk_text


def test_fixed_chunks_respect_size() -> None:
    chunks = chunk_text("a" * 2000, ChunkingStrategy.FIXED)
    assert len(chunks) > 1
    assert all(len(c) <= 800 for c in chunks)


def test_sentence_chunks_keep_sentences_whole() -> None:
    text = " ".join(f"This is sentence number {i}." for i in range(100))
    chunks = chunk_text(text, ChunkingStrategy.SENTENCE)
    assert len(chunks) > 1
    assert all(c.endswith(".") for c in chunks)
