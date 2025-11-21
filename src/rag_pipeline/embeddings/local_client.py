"""Local embedding client backed by SentenceTransformer checkpoints."""

from __future__ import annotations

from time import perf_counter
from pathlib import Path
from typing import Callable, Iterable, Protocol, Sequence, cast
from uuid import uuid4

from sentence_transformers import SentenceTransformer

from src.rag_pipeline.embeddings.client_types import (
    EmbeddingBatchMetrics,
    EmbeddingModelInfo,
    EmbeddingResponse,
)
from src.rag_pipeline.embeddings.manifest import ArtifactManifest
from src.rag_pipeline.schemas import ChunkData, EmbeddingRecord
from src.shared.logging import LoggerProtocol, get_logger
from src.shared.tracing import Tracer, noop_tracer


class SentenceTransformerModel(Protocol):
    """Protocol describing the subset of SentenceTransformer required here."""

    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int | None = None,
        convert_to_numpy: bool = True,
        normalize_embeddings: bool | None = None,
    ) -> Sequence[Sequence[float]]:
        """Encode text into embeddings."""

    def get_sentence_embedding_dimension(self) -> int:
        """Return the embedding dimension."""


ModelLoader = Callable[[str], SentenceTransformerModel]


class SentenceTransformerEmbeddingClient:
    """Embed texts using a local fine-tuned SentenceTransformer model."""

    def __init__(
        self,
        *,
        model_path: Path,
        batch_size: int = 8,
        model_label: str | None = None,
        manifest: ArtifactManifest | None = None,
        model_loader: ModelLoader | None = None,
        logger: LoggerProtocol | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        """Initialize the local embedding client.

        Args:
            model_path: Path to the fine-tuned model directory.
            batch_size: Number of texts to embed per batch.
            model_label: Optional label to emit in embeddings and logs.
            manifest: Optional artifact manifest containing metadata.
            model_loader: Optional loader used to construct the model
                (defaults to ``SentenceTransformer``).
            logger: Structured logger for embedding events.
            tracer: Tracer for span reporting.
        """
        self._model_path = model_path
        self._batch_size = max(1, batch_size)
        self._logger = logger or get_logger(__name__)
        self._tracer = tracer or noop_tracer()
        loader = model_loader or _default_model_loader
        self._model = loader(str(model_path))
        self._manifest = manifest
        resolved_label = model_label
        if resolved_label is None and manifest is not None:
            resolved_label = f"{manifest.base_model}-ft-{manifest.version}"
        self._model_label = resolved_label or str(model_path)
        self._embedding_dimension = self._model.get_sentence_embedding_dimension()
        if manifest is not None and manifest.embedding_dimension != self._embedding_dimension:
            self._logger.warning(
                "fine_tuned_embedding_dimension_mismatch",
                manifest_dimension=manifest.embedding_dimension,
                model_dimension=self._embedding_dimension,
            )
        self.model_info = EmbeddingModelInfo(
            model=self._model_label,
            dataset_fingerprint=manifest.dataset_fingerprint if manifest else None,
            artifact_version=manifest.version if manifest else None,
        )
        self._logger.info(
            "local_embedding_client_initialized",
            model_label=self._model_label,
            batch_size=self._batch_size,
            dataset_fingerprint=self.model_info.dataset_fingerprint,
            artifact_version=self.model_info.artifact_version,
        )

    def embed_texts(self, texts: Sequence[str], *, correlation_id: str | None = None) -> EmbeddingResponse:
        """Embed the given texts, preserving order.

        Args:
            texts: Raw text inputs to embed.
            correlation_id: Optional request identifier.

        Returns:
            EmbeddingResponse containing embeddings and batch metrics.
        """
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
        """Embed chunk payloads.

        Args:
            chunks: Chunk payloads to embed.
            correlation_id: Optional request identifier.

        Returns:
            Embeddings in the same order as the provided chunks.
        """
        if not chunks:
            return []
        texts = [chunk.text for chunk in chunks]
        response = self.embed_texts(texts=texts, correlation_id=correlation_id)
        if len(response.embeddings) != len(chunks):
            raise ValueError("Embedding count mismatch for document chunks.")
        return response.embeddings

    def close(self) -> None:
        """No-op to mirror the remote client interface.

        Returns:
            None.
        """
        return None

    def _embed_batch(
        self,
        *,
        batch_id: str,
        texts: Sequence[str],
        correlation_id: str | None,
    ) -> tuple[list[EmbeddingRecord], EmbeddingBatchMetrics]:
        """Embed a single batch of texts.

        Args:
            batch_id: Unique identifier for the batch.
            texts: Texts to embed.
            correlation_id: Optional request identifier.

        Returns:
            Tuple of embeddings and batch metrics.
        """
        start = perf_counter()
        self._logger.info(
            "local_embedding_batch_started",
            batch_id=batch_id,
            item_count=len(texts),
            model=self._model_label,
            dataset_fingerprint=self.model_info.dataset_fingerprint,
            correlation_id=correlation_id,
        )
        with self._tracer.span(
            name="embedding_batch_local",
            correlation_id=correlation_id,
            attributes={
                "batch_id": batch_id,
                "item_count": len(texts),
                "embedding_model": self._model_label,
                "dataset_fingerprint": self.model_info.dataset_fingerprint or "",
            },
        ):
            vectors = self._model.encode(
                list(texts),
                batch_size=self._batch_size,
                convert_to_numpy=True,
                normalize_embeddings=False,
            )
        duration_ms = (perf_counter() - start) * 1000.0
        converted = self._convert_vectors(vectors=vectors, sample=texts[0] if texts else "")
        metrics = EmbeddingBatchMetrics(
            batch_id=batch_id,
            item_count=len(texts),
            retry_count=0,
            duration_ms=duration_ms,
        )
        self._logger.info(
            "local_embedding_batch_completed",
            batch_id=batch_id,
            item_count=len(texts),
            duration_ms=duration_ms,
            dataset_fingerprint=self.model_info.dataset_fingerprint,
            correlation_id=correlation_id,
        )
        return converted, metrics

    def _convert_vectors(self, *, vectors: Sequence[Sequence[float]], sample: str) -> list[EmbeddingRecord]:
        """Convert encoded vectors into embedding records.

        Args:
            vectors: Raw vectors returned by the SentenceTransformer model.
            sample: Sample text used only for error messages.

        Returns:
            List of EmbeddingRecord payloads ready for persistence.

        Raises:
            ValueError: If the embedding dimension differs from expectations.
        """
        embeddings: list[EmbeddingRecord] = []
        for vector in vectors:
            values = [float(value) for value in vector]
            if len(values) != self._embedding_dimension:
                raise ValueError(
                    (
                        "Embedding dimension mismatch "
                        f"for sample {sample!r} "
                        f"(expected {self._embedding_dimension}, received {len(values)})."
                    ),
                )
            embeddings.append(
                EmbeddingRecord(
                    vector=tuple(values),
                    model=self._model_label,
                    dimensions=self._embedding_dimension,
                ),
            )
        return embeddings


def _default_model_loader(model_name: str) -> SentenceTransformerModel:
    """Load a SentenceTransformer model from the provided path or name.

    Args:
        model_name: Model name or path passed to ``SentenceTransformer``.

    Returns:
        Loaded SentenceTransformer instance.
    """
    return cast(SentenceTransformerModel, SentenceTransformer(model_name))


def _batched(sequence: Sequence[str], batch_size: int) -> Iterable[Sequence[str]]:
    """Yield consecutive batches from a sequence.

    Args:
        sequence: Input sequence to batch.
        batch_size: Maximum batch size.

    Yields:
        Slices of the input sequence with size up to ``batch_size``.
    """
    start = 0
    total = len(sequence)
    while start < total:
        end = min(total, start + batch_size)
        yield sequence[start:end]
        start = end
