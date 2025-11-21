import pytest

from src.rag_pipeline.embeddings.qwen_client import EmbeddingResponse
from src.rag_pipeline.retrieval import DatabaseRetriever, NullRetriever, RetrievedChunk
from src.rag_pipeline.schemas import EmbeddingRecord, JSONValue


class _FakeEmbeddingClient:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed_texts(self, texts: list[str], *, correlation_id: str | None = None) -> EmbeddingResponse:
        self.calls.append(list(texts))
        return EmbeddingResponse(
            embeddings=[EmbeddingRecord(vector=(0.1, 0.2), model="demo", dimensions=2)],
            metrics=[],
        )


class _FakeStore:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[float, ...], int, float]] = []

    def match_chunks(
        self,
        *,
        query_embedding: tuple[float, ...],
        match_count: int,
        min_score: float,
    ) -> list[dict[str, JSONValue]]:
        self.calls.append((tuple(query_embedding), match_count, min_score))
        return [
            {
                "chunk_id": "chunk-1",
                "source_id": "source-1",
                "document_name": "doc-one",
                "content": "chunk text",
                "score": 0.95,
                "metadata": {"page_number": 1},
            },
        ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_database_retriever_returns_chunks() -> None:
    embedding_client = _FakeEmbeddingClient()
    store = _FakeStore()
    retriever = DatabaseRetriever(embedding_client=embedding_client, store=store)

    chunks = await retriever.retrieve("hello world", top_k=2, min_score=0.1)

    assert isinstance(chunks, list)
    assert len(chunks) == 1
    assert chunks[0] == RetrievedChunk(
        chunk_id="chunk-1",
        source_id="source-1",
        document_name="doc-one",
        content="chunk text",
        score=0.95,
        metadata={"page_number": 1},
    )
    assert store.calls[0][1] == 2
    assert embedding_client.calls == [["hello world"]]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_null_retriever_returns_empty() -> None:
    retriever = NullRetriever()
    chunks = await retriever.retrieve("anything", top_k=1, min_score=0.0)
    assert chunks == []
