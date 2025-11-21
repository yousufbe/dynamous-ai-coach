"""Shared interfaces for embedding clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from src.rag_pipeline.schemas import ChunkData, EmbeddingRecord


@dataclass(frozen=True, slots=True)
class EmbeddingBatchMetrics:
    """Metrics describing a single embedding batch invocation."""

    batch_id: str
    item_count: int
    retry_count: int
    duration_ms: float


@dataclass(frozen=True, slots=True)
class EmbeddingResponse:
    """Return type for batch embedding operations."""

    embeddings: list[EmbeddingRecord]
    metrics: list[EmbeddingBatchMetrics]


@dataclass(frozen=True, slots=True)
class EmbeddingModelInfo:
    """Metadata describing the embedding backend."""

    model: str
    dataset_fingerprint: str | None
    artifact_version: str | None


class EmbeddingClientProtocol(Protocol):
    """Contract implemented by embedding clients used for ingestion/retrieval."""

    model_info: EmbeddingModelInfo

    def embed_texts(self, texts: Sequence[str], *, correlation_id: str | None = None) -> EmbeddingResponse:
        """Embed a sequence of raw texts.

        Args:
            texts: Text snippets to encode.
            correlation_id: Optional identifier for tracing/logging.

        Returns:
            EmbeddingResponse containing vectors and batch metrics.
        """

    def embed_document_chunks(
        self,
        chunks: Sequence[ChunkData],
        *,
        correlation_id: str | None = None,
    ) -> list[EmbeddingRecord]:
        """Embed a sequence of ChunkData payloads.

        Args:
            chunks: Parsed chunk objects.
            correlation_id: Optional identifier for tracing/logging.

        Returns:
            Embedding vectors matching the order of the chunks.
        """

    def close(self) -> None:
        """Release client resources.

        Returns:
            None.
        """
