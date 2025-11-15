from unittest import mock

import pytest

from src.rag_pipeline.embeddings.qwen_client import EmbeddingError, QwenEmbeddingClient
from src.rag_pipeline.schemas import ChunkData, ChunkMetadata


class DummyResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _payload_for(text_count: int) -> dict:
    return {
        "data": [
            {
                "index": idx,
                "embedding": [float(idx), float(idx) + 0.5],
            }
            for idx in range(text_count)
        ],
    }


@pytest.mark.unit
def test_embed_texts_batches_inputs() -> None:
    """Inputs should be batched according to configuration."""
    session = mock.Mock()
    session.post.side_effect = [
        DummyResponse(200, _payload_for(2)),
        DummyResponse(200, _payload_for(1)),
    ]
    client = QwenEmbeddingClient(
        model="demo",
        api_key=None,
        batch_size=2,
        expected_dimensions=2,
        session=session,
    )
    response = client.embed_texts(["a", "b", "c"])
    assert len(response.embeddings) == 3
    assert session.post.call_count == 2


@pytest.mark.unit
def test_embed_texts_retries_on_failure() -> None:
    """Transient failures should trigger a retry."""
    session = mock.Mock()
    session.post.side_effect = [
        DummyResponse(500, {}),
        DummyResponse(200, _payload_for(1)),
    ]
    client = QwenEmbeddingClient(
        model="demo",
        api_key=None,
        batch_size=1,
        retry_count=1,
        expected_dimensions=2,
        session=session,
    )
    response = client.embed_texts(["hello"])
    assert len(response.embeddings) == 1
    assert session.post.call_count == 2


@pytest.mark.unit
def test_embed_texts_raises_on_dimension_mismatch() -> None:
    """Mismatched vector dimension should raise EmbeddingError."""
    session = mock.Mock()
    bad_payload = {"data": [{"index": 0, "embedding": [0.1]}]}
    session.post.return_value = DummyResponse(200, bad_payload)
    client = QwenEmbeddingClient(
        model="demo",
        api_key=None,
        expected_dimensions=2,
        session=session,
    )
    with pytest.raises(EmbeddingError):
        client.embed_texts(["hello"])


@pytest.mark.unit
def test_embed_document_chunks_round_trip() -> None:
    """Embedding chunk helper should preserve ordering."""
    session = mock.Mock()
    session.post.return_value = DummyResponse(200, _payload_for(1))
    client = QwenEmbeddingClient(
        model="demo",
        api_key="secret",
        expected_dimensions=2,
        session=session,
    )
    chunk = ChunkData(
        text="example paragraph",
        metadata=ChunkMetadata(
            page_number=1,
            chunk_index=0,
            section_heading=None,
            structural_type="paragraph",
        ),
        character_count=18,
    )
    embeddings = client.embed_document_chunks([chunk])
    assert embeddings[0].model == "demo"
    headers = session.post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer secret"
