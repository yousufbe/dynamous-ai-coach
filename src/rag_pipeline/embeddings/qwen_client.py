"""HTTP client for Qwen3 embedding endpoints.

The pipeline prefers the hosted Qwen3-Embedding-0.6B API exposed by DashScope
or an OpenAI-compatible gateway. The client keeps the implementation small and
type-safe while exposing structured metrics for observability and retries. The
API key is read from ``QWEN_API_KEY`` unless provided explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from time import perf_counter, sleep
from typing import Any, Iterable, Sequence
from uuid import uuid4
import random

import requests

from src.rag_pipeline.config import RagIngestionConfig
from src.rag_pipeline.schemas import ChunkData, EmbeddingRecord
from src.shared.logging import LoggerProtocol, get_logger
from src.shared.tracing import Tracer, noop_tracer

DEFAULT_QWEN_EMBEDDING_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding"
)

logger: LoggerProtocol = get_logger(__name__)


class EmbeddingError(RuntimeError):
    """Raised when the embedding API reports an error or malformed payload."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None,
        batch_id: str,
        retry_count: int,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.batch_id = batch_id
        self.retry_count = retry_count


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


class QwenEmbeddingClient:
    """Minimal embedding client with retry/backoff and structured logging."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        base_url: str = DEFAULT_QWEN_EMBEDDING_URL,
        timeout_seconds: int = 60,
        retry_count: int = 1,
        retry_backoff_seconds: float = 2.0,
        expected_dimensions: int = 1024,
        batch_size: int = 8,
        session: requests.Session | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds
        self._retry_count = retry_count
        self._retry_backoff_seconds = retry_backoff_seconds
        self._expected_dimensions = expected_dimensions
        self._batch_size = max(1, batch_size)
        self._session = session or requests.Session()
        self._tracer = tracer or noop_tracer()
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        logger.info(
            "qwen_embedding_client_initialized",
            model=model,
            base_url=base_url,
            batch_size=self._batch_size,
            retry_count=retry_count,
            timeout_seconds=timeout_seconds,
        )

    @classmethod
    def from_config(
        cls,
        config: RagIngestionConfig,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        session: requests.Session | None = None,
        tracer: Tracer | None = None,
    ) -> "QwenEmbeddingClient":
        """Construct the client using RagIngestionConfig defaults."""
        resolved_api_key = api_key if api_key is not None else os.getenv("QWEN_API_KEY")
        env_base_url = os.getenv("QWEN_EMBEDDING_BASE_URL")
        fallback_base_url = env_base_url if env_base_url is not None else DEFAULT_QWEN_EMBEDDING_URL
        resolved_base_url = base_url if base_url is not None else fallback_base_url
        return cls(
            model=config.embedding_model,
            api_key=resolved_api_key,
            base_url=resolved_base_url,
            timeout_seconds=config.embedding_timeout_seconds,
            retry_count=config.embedding_retry_count,
            retry_backoff_seconds=config.embedding_retry_backoff_seconds,
            expected_dimensions=config.embedding_dimension,
            batch_size=config.embedding_batch_size,
            session=session,
            tracer=tracer,
        )

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def embed_texts(self, texts: Sequence[str], *, correlation_id: str | None = None) -> EmbeddingResponse:
        """Embed the given texts, preserving order."""
        if not texts:
            return EmbeddingResponse(embeddings=[], metrics=[])
        embeddings: list[EmbeddingRecord] = []
        metrics: list[EmbeddingBatchMetrics] = []
        for batch in _batched(texts, self._batch_size):
            batch_id = uuid4().hex
            batch_embeddings, batch_metric = self._embed_batch(
                batch_id=batch_id,
                texts=batch,
                correlation_id=correlation_id,
            )
            embeddings.extend(batch_embeddings)
            metrics.append(batch_metric)
        return EmbeddingResponse(embeddings=embeddings, metrics=metrics)

    def embed_document_chunks(
        self,
        chunks: Sequence[ChunkData],
        *,
        correlation_id: str | None = None,
    ) -> list[EmbeddingRecord]:
        """Embed a list of ChunkData objects."""
        if not chunks:
            return []
        texts = [chunk.text for chunk in chunks]
        response = self.embed_texts(texts=texts, correlation_id=correlation_id)
        if len(response.embeddings) != len(chunks):
            raise EmbeddingError(
                "Embedding count mismatch for document chunks.",
                status_code=None,
                batch_id="pipeline",
                retry_count=0,
            )
        return response.embeddings

    def _embed_batch(
        self,
        *,
        batch_id: str,
        texts: Sequence[str],
        correlation_id: str | None,
    ) -> tuple[list[EmbeddingRecord], EmbeddingBatchMetrics]:
        attempts = 0
        last_error: EmbeddingError | None = None
        while attempts <= self._retry_count:
            start = perf_counter()
            logger.info(
                "embedding_batch_started",
                batch_id=batch_id,
                item_count=len(texts),
                attempt=attempts,
                correlation_id=correlation_id,
            )
            with self._tracer.span(
                name="embedding_batch",
                correlation_id=correlation_id,
                attributes={"batch_id": batch_id, "item_count": len(texts)},
            ):
                try:
                    vectors = self._invoke_api(
                        batch_id=batch_id,
                        texts=texts,
                        attempt=attempts,
                    )
                    duration_ms = (perf_counter() - start) * 1000.0
                    logger.info(
                        "embedding_batch_succeeded",
                        batch_id=batch_id,
                        item_count=len(texts),
                        duration_ms=duration_ms,
                        retry_count=attempts,
                        correlation_id=correlation_id,
                    )
                    embeddings = [
                        EmbeddingRecord(
                            vector=tuple(vector),
                            model=self._model,
                            dimensions=self._expected_dimensions,
                        )
                        for vector in vectors
                    ]
                    metrics = EmbeddingBatchMetrics(
                        batch_id=batch_id,
                        item_count=len(texts),
                        retry_count=attempts,
                        duration_ms=duration_ms,
                    )
                    return embeddings, metrics
                except EmbeddingError as exc:
                    last_error = exc
                    logger.warning(
                        "embedding_batch_failed",
                        batch_id=batch_id,
                        item_count=len(texts),
                        status_code=exc.status_code,
                        attempt=attempts,
                        error=str(exc),
                        correlation_id=correlation_id,
                    )
                    if attempts >= self._retry_count:
                        raise
                    attempts += 1
                    backoff = self._retry_backoff_seconds * (2 ** (attempts - 1))
                    jitter = random.uniform(0.0, 0.5)
                    logger.info(
                        "embedding_batch_retry_scheduled",
                        batch_id=batch_id,
                        attempt=attempts,
                        backoff_seconds=backoff + jitter,
                        correlation_id=correlation_id,
                    )
                    sleep(backoff + jitter)
        assert last_error is not None  # pragma: no cover - defensive
        raise last_error

    def _invoke_api(
        self,
        batch_id: str,
        texts: Sequence[str],
        attempt: int,
    ) -> list[list[float]]:
        payload = self._build_payload(texts=texts)
        preview = _preview(texts[0]) if texts else ""
        try:
            response = self._session.post(
                self._base_url,
                headers=self._headers,
                json=payload,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as exc:
            raise EmbeddingError(
                f"Failed to reach Qwen embeddings endpoint for sample {preview!r}: {exc}",
                status_code=None,
                batch_id=batch_id,
                retry_count=attempt,
            ) from exc
        if response.status_code >= 400:
            raise EmbeddingError(
                (
                    "Embedding request failed "
                    f"with status {response.status_code} "
                    f"for sample {preview!r}"
                ),
                status_code=response.status_code,
                batch_id=batch_id,
                retry_count=attempt,
            )
        try:
            payload_json = response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise EmbeddingError(
                "Embedding response did not contain valid JSON.",
                status_code=response.status_code,
                batch_id=batch_id,
                retry_count=attempt,
            ) from exc
        return self._parse_response(
            payload=payload_json,
            expected_count=len(texts),
            batch_id=batch_id,
            sample=texts[0] if texts else "",
            attempt=attempt,
        )

    def _build_payload(self, texts: Sequence[str]) -> dict[str, Any]:
        return {
            "model": self._model,
            "input": list(texts),
        }

    def _parse_response(
        self,
        *,
        payload: dict[str, Any],
        expected_count: int,
        batch_id: str,
        sample: str,
        attempt: int,
    ) -> list[list[float]]:
        data = payload.get("data")
        embeddings_field = payload.get("embeddings")
        vectors_raw: Iterable[Any]
        if isinstance(data, list):
            sorted_data = sorted(
                data,
                key=lambda item: int(item.get("index", 0)),
            )
            vectors_raw = [item.get("embedding") for item in sorted_data]
        elif isinstance(embeddings_field, list):
            vectors_raw = embeddings_field
        else:
            raise EmbeddingError(
                "Embedding response missing 'data' or 'embeddings'.",
                status_code=None,
                batch_id=batch_id,
                retry_count=attempt,
            )
        vectors: list[list[float]] = []
        for vector in vectors_raw:
            if not isinstance(vector, Sequence):
                raise EmbeddingError(
                    "Embedding vector payload was not a sequence.",
                    status_code=None,
                    batch_id=batch_id,
                    retry_count=attempt,
                )
            converted = [float(value) for value in vector]
            if len(converted) != self._expected_dimensions:
                text_preview = _preview(sample)
                raise EmbeddingError(
                    (
                        "Embedding dimension mismatch "
                        f"for sample {text_preview!r} "
                        f"(expected {self._expected_dimensions}, "
                        f"received {len(converted)})."
                    ),
                    status_code=None,
                    batch_id=batch_id,
                    retry_count=attempt,
                )
            vectors.append(converted)
        if len(vectors) != expected_count:
            raise EmbeddingError(
                "Embedding response size mismatch.",
                status_code=None,
                batch_id=batch_id,
                retry_count=attempt,
            )
        return vectors


def _batched(sequence: Sequence[str], batch_size: int) -> Iterable[Sequence[str]]:
    start = 0
    total = len(sequence)
    while start < total:
        end = min(total, start + batch_size)
        yield sequence[start:end]
        start = end


def _preview(text: str, limit: int = 96) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "…"
