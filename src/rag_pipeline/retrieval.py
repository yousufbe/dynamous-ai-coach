from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Mapping, Protocol, Sequence

from src.rag_pipeline.embeddings import QwenEmbeddingClient
from src.rag_pipeline.schemas import JSONValue
from src.shared.logging import LoggerProtocol, get_logger
from src.shared.tracing import Tracer, noop_tracer


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """Chunk returned by a retrieval query."""

    chunk_id: str
    source_id: str
    document_name: str
    content: str
    score: float
    metadata: dict[str, JSONValue]


class RetrieverProtocol(Protocol):
    """Contract for query-time retrieval services."""

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int,
        min_score: float,
        correlation_id: str | None = None,
    ) -> list[RetrievedChunk]:
        """Return relevant chunks for the provided query."""


class RetrievalStoreProtocol(Protocol):
    """Minimal interface required from a persistence store for retrieval."""

    def match_chunks(
        self,
        *,
        query_embedding: Sequence[float],
        match_count: int,
        min_score: float,
    ) -> Sequence[Mapping[str, Any]]:
        """Return chunk rows ordered by similarity to the query embedding."""


class NullRetriever(RetrieverProtocol):
    """No-op retriever used when dependencies are unavailable."""

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int,
        min_score: float,
        correlation_id: str | None = None,
    ) -> list[RetrievedChunk]:
        """Return an empty result set regardless of input."""
        return []


class DatabaseRetriever(RetrieverProtocol):
    """Retrieve context by embedding the query and calling the DB matcher."""

    def __init__(
        self,
        *,
        embedding_client: QwenEmbeddingClient,
        store: RetrievalStoreProtocol,
        logger: LoggerProtocol | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self._embedding_client = embedding_client
        self._store = store
        self._logger = logger or get_logger(__name__)
        self._tracer = tracer or noop_tracer()

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int,
        min_score: float,
        correlation_id: str | None = None,
    ) -> list[RetrievedChunk]:
        """Embed the query and return similar chunks.

        Args:
            query: User query text.
            top_k: Maximum number of chunks to return.
            min_score: Minimum similarity score filter.
            correlation_id: Optional identifier used for log correlation.

        Returns:
            Retrieved chunks ordered by similarity descending.
        """
        stripped_query = query.strip()
        if not stripped_query:
            return []
        safe_top_k = max(1, top_k)
        return await asyncio.to_thread(
            self._retrieve_sync,
            stripped_query,
            safe_top_k,
            min_score,
            correlation_id,
        )

    def _retrieve_sync(
        self,
        query: str,
        top_k: int,
        min_score: float,
        correlation_id: str | None,
    ) -> list[RetrievedChunk]:
        start = perf_counter()
        self._logger.info(
            "retrieval_started",
            query_length=len(query),
            top_k=top_k,
            min_score=min_score,
            correlation_id=correlation_id,
        )
        with self._tracer.span(
            name="retrieval",
            correlation_id=correlation_id,
            attributes={"top_k": top_k, "min_score": min_score},
        ):
            try:
                embedding_response = self._embedding_client.embed_texts(
                    [query],
                    correlation_id=correlation_id,
                )
                if not embedding_response.embeddings:
                    self._logger.warning("retrieval_skipped_no_embedding")
                    return []
                query_embedding = embedding_response.embeddings[0].vector
                rows = self._store.match_chunks(
                    query_embedding=query_embedding,
                    match_count=top_k,
                    min_score=min_score,
                )
                results = [self._map_row(row) for row in rows]
                self._logger.info(
                    "retrieval_completed",
                    results_count=len(results),
                    duration_ms=(perf_counter() - start) * 1000.0,
                    correlation_id=correlation_id,
                )
                return results
            except Exception as exc:  # noqa: BLE001
                self._logger.exception(
                    "retrieval_failed",
                    error=str(exc),
                    correlation_id=correlation_id,
                )
                return []

    @staticmethod
    def _map_row(row: Mapping[str, Any]) -> RetrievedChunk:
        metadata_value = row.get("metadata", {}) or {}
        metadata: dict[str, JSONValue]
        if isinstance(metadata_value, dict):
            metadata = dict(metadata_value)
        else:
            metadata = {}
        return RetrievedChunk(
            chunk_id=str(row["chunk_id"]),
            source_id=str(row["source_id"]),
            document_name=str(row.get("document_name", "")),
            content=str(row.get("content", "")),
            score=float(row.get("score", 0.0)),
            metadata=metadata,
        )
