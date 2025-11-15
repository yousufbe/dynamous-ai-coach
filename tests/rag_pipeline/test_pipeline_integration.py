import datetime as dt
from dataclasses import replace
from pathlib import Path

import pytest

from src.rag_pipeline.config import get_rag_ingestion_config
from src.rag_pipeline.persistence import InMemoryStore
from src.rag_pipeline.pipeline import PipelineServices, run_ingestion_job
from src.rag_pipeline.schemas import EmbeddingRecord, IngestionRequest


class FakeEmbeddingClient:
    def embed_document_chunks(self, chunks):
        return [
            EmbeddingRecord(vector=(float(idx), float(idx) + 1.0), model="fake", dimensions=2)
            for idx, _chunk in enumerate(chunks)
        ]

    def close(self) -> None:
        """No-op for compatibility."""


def _chunker(chunk_min_chars: int, chunk_max_chars: int):
    from src.rag_pipeline.chunking.docling_chunker import DoclingChunker

    return DoclingChunker(chunk_min_chars=chunk_min_chars, chunk_max_chars=chunk_max_chars)


@pytest.mark.integration
def test_run_ingestion_job_with_inmemory_store(tmp_path: Path) -> None:
    """End-to-end ingestion should succeed with the in-memory store."""
    sample = tmp_path / "sample.txt"
    sample.write_text("Docling pipeline integration test.", encoding="utf-8")
    config = get_rag_ingestion_config()
    config = replace(config, source_directories=[tmp_path])
    services = PipelineServices(
        chunker=_chunker(config.chunk_min_chars, config.chunk_max_chars),
        embedding_client=FakeEmbeddingClient(),
        persistence=InMemoryStore(),
        clock=lambda: dt.datetime.now(tz=dt.timezone.utc),
    )
    request = IngestionRequest()
    result = run_ingestion_job(request=request, config=config, services=services)
    assert result.stats.documents_ingested == 1
    assert result.stats.documents_failed == 0
    assert result.stats.chunks_created >= 1
