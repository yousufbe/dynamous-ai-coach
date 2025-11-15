import time
from dataclasses import replace

import pytest

from src.rag_pipeline.config import get_rag_ingestion_config
from src.rag_pipeline.persistence import InMemoryStore
from src.rag_pipeline.pipeline import PipelineServices, run_ingestion_job
from src.rag_pipeline.schemas import IngestionRequest


class FastEmbeddingClient:
    def embed_document_chunks(self, chunks):
        from src.rag_pipeline.schemas import EmbeddingRecord

        return [
            EmbeddingRecord(vector=(0.0, 1.0), model="fast", dimensions=2)
            for _ in chunks
        ]

    def close(self) -> None:
        """No-op."""


@pytest.mark.performance
@pytest.mark.skip(reason="Enable manually to collect throughput numbers.")
def test_ingestion_performance_baseline(tmp_path) -> None:
    """Simple benchmark that ingests synthetic files and records duration."""
    for index in range(10):
        (tmp_path / f"doc{index}.txt").write_text("performance", encoding="utf-8")
    config = replace(get_rag_ingestion_config(), source_directories=[tmp_path])
    services = PipelineServices(
        chunker=_chunker(config),
        embedding_client=FastEmbeddingClient(),
        persistence=InMemoryStore(),
        clock=time.time,
    )
    start = time.perf_counter()
    result = run_ingestion_job(request=IngestionRequest(), config=config, services=services)
    duration = time.perf_counter() - start
    assert result.stats.documents_discovered == 10
    assert duration >= 0.0


def _chunker(config):
    from src.rag_pipeline.chunking.docling_chunker import DoclingChunker

    return DoclingChunker(
        chunk_min_chars=config.chunk_min_chars,
        chunk_max_chars=config.chunk_max_chars,
        docling_target_tokens=config.docling_chunk_target_tokens,
    )
