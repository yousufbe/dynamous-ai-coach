"""Helpers for constructing pipeline dependencies."""

from __future__ import annotations

from src.rag_pipeline.chunking.docling_chunker import DoclingChunker
from src.rag_pipeline.config import RagIngestionConfig
from src.rag_pipeline.embeddings import QwenEmbeddingClient
from src.rag_pipeline.persistence import PsycopgDatabaseClient, SupabaseStore
from src.rag_pipeline.pipeline import PipelineServices
from src.shared.logging import get_logger


def create_pipeline_runtime(
    config: RagIngestionConfig,
) -> tuple[PipelineServices, QwenEmbeddingClient, PsycopgDatabaseClient]:
    """Build pipeline services along with the resources that require cleanup."""
    if not config.database_url:
        raise ValueError("RAG_DATABASE_URL must be configured.")
    embedding_client: QwenEmbeddingClient | None = None
    db_client: PsycopgDatabaseClient | None = None
    try:
        chunker = DoclingChunker(
            chunk_min_chars=config.chunk_min_chars,
            chunk_max_chars=config.chunk_max_chars,
            docling_target_tokens=config.docling_chunk_target_tokens,
        )
        embedding_client = QwenEmbeddingClient.from_config(config=config)
        db_client = PsycopgDatabaseClient(config.database_url)
        store = SupabaseStore(db=db_client, config=config)
        services = PipelineServices(
            chunker=chunker,
            embedding_client=embedding_client,
            persistence=store,
        )
        return services, embedding_client, db_client
    except Exception:
        if embedding_client is not None:
            embedding_client.close()
        if db_client is not None:
            db_client.close()
        raise


def cleanup_runtime(
    embedding_client: QwenEmbeddingClient,
    db_client: PsycopgDatabaseClient,
) -> None:
    """Close runtime resources while swallowing cleanup errors."""
    log = get_logger(__name__)
    try:
        embedding_client.close()
    except Exception:  # pragma: no cover - defensive
        log.warning("embedding_client_close_failed")
    try:
        db_client.close()
    except Exception:  # pragma: no cover - defensive
        log.warning("db_client_close_failed")
