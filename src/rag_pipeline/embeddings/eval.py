"""Evaluation harness for fine-tuned vs baseline embeddings."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol, Sequence, cast

from sentence_transformers import SentenceTransformer

from src.rag_pipeline.embeddings.data_prep import (
    QueryDocumentPair,
    compute_fingerprint,
    read_jsonl,
)
from src.shared.logging import LoggerProtocol, get_logger


class EmbeddingModel(Protocol):
    """Protocol for encoding text into fixed-size embeddings."""

    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int | None = None,
        convert_to_numpy: bool = False,
        normalize_embeddings: bool | None = None,
    ) -> list[list[float]]:
        """Encode text into embeddings."""

    def get_sentence_embedding_dimension(self) -> int:
        """Return the embedding dimension."""


ModelLoader = Callable[[str], EmbeddingModel]


@dataclass(frozen=True, slots=True)
class EvaluationRequest:
    """Parameters required to run an evaluation."""

    validation_path: Path
    base_model_path: str
    tuned_model_path: str
    top_k: int = 5


@dataclass(frozen=True, slots=True)
class ModelEvaluation:
    """Computed metrics for a single model."""

    model_name: str
    recall_at_k: float
    mean_rank: float
    total_queries: int
    top_k: int
    dataset_fingerprint: str
    embedding_dimension: int


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Summary comparing baseline and fine-tuned models."""

    created_at: str
    dataset_fingerprint: str
    base: ModelEvaluation
    tuned: ModelEvaluation


def run_evaluation(
    request: EvaluationRequest,
    *,
    model_loader: ModelLoader | None = None,
    logger: LoggerProtocol | None = None,
) -> EvaluationReport:
    """Evaluate baseline vs tuned embeddings on the validation set.

    Args:
        request: Evaluation inputs and configuration.
        model_loader: Optional loader to construct models; defaults to
            ``SentenceTransformer``.
        logger: Structured logger to use for progress updates.

    Returns:
        EvaluationReport containing metrics for both models.
    """
    log = logger or get_logger(__name__)
    if not request.validation_path.exists():
        raise FileNotFoundError(f"Validation data not found at {request.validation_path}")
    pairs = read_jsonl(request.validation_path)
    if not pairs:
        raise ValueError("Validation dataset is empty; cannot compute recall@k.")
    if request.top_k <= 0:
        raise ValueError("top_k must be greater than zero.")
    dataset_fingerprint = compute_fingerprint(pairs)
    loader = model_loader or _default_model_loader
    base_model = loader(request.base_model_path)
    tuned_model = loader(request.tuned_model_path)
    log.info(
        "embedding_evaluation_started",
        validation_examples=len(pairs),
        top_k=request.top_k,
        dataset_fingerprint=dataset_fingerprint,
        base_model=request.base_model_path,
        tuned_model=request.tuned_model_path,
    )
    base_metrics = _compute_metrics(
        pairs=pairs,
        model=base_model,
        model_name=request.base_model_path,
        top_k=request.top_k,
        dataset_fingerprint=dataset_fingerprint,
    )
    tuned_metrics = _compute_metrics(
        pairs=pairs,
        model=tuned_model,
        model_name=request.tuned_model_path,
        top_k=request.top_k,
        dataset_fingerprint=dataset_fingerprint,
    )
    report = EvaluationReport(
        created_at=datetime.now(tz=timezone.utc).isoformat(),
        dataset_fingerprint=dataset_fingerprint,
        base=base_metrics,
        tuned=tuned_metrics,
    )
    log.info(
        "embedding_evaluation_completed",
        dataset_fingerprint=dataset_fingerprint,
        base_recall_at_k=base_metrics.recall_at_k,
        tuned_recall_at_k=tuned_metrics.recall_at_k,
        top_k=request.top_k,
    )
    return report


def write_report(report: EvaluationReport, output_path: Path) -> None:
    """Persist an evaluation report to disk as JSON.

    Args:
        report: Evaluation results to write.
        output_path: Destination file path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")


def _compute_metrics(
    *,
    pairs: Sequence[QueryDocumentPair],
    model: EmbeddingModel,
    model_name: str,
    top_k: int,
    dataset_fingerprint: str,
) -> ModelEvaluation:
    """Compute recall@k and mean rank for a single model.

    Args:
        pairs: Validation pairs used for evaluation.
        model: Model used to encode queries/documents.
        model_name: Human-readable identifier for the model.
        top_k: Recall@k cutoff.
        dataset_fingerprint: Fingerprint shared by the evaluation dataset.

    Returns:
        ModelEvaluation populated with computed metrics.
    """
    documents = [pair.document for pair in pairs]
    queries = [pair.query for pair in pairs]
    document_embeddings = model.encode(documents, convert_to_numpy=False, normalize_embeddings=True)
    query_embeddings = model.encode(queries, convert_to_numpy=False, normalize_embeddings=True)
    _validate_dimensions(document_embeddings=document_embeddings, query_embeddings=query_embeddings)
    recall_hits = 0
    ranks: list[int] = []
    for index, query_embedding in enumerate(query_embeddings):
        scores = [
            _cosine_similarity(query_embedding, document_embedding)
            for document_embedding in document_embeddings
        ]
        sorted_indices = sorted(range(len(scores)), key=scores.__getitem__, reverse=True)
        rank = sorted_indices.index(index) + 1
        ranks.append(rank)
        if rank <= top_k:
            recall_hits += 1
    total = len(pairs)
    recall_at_k = recall_hits / float(total) if total > 0 else 0.0
    mean_rank = sum(ranks) / float(total) if total > 0 else 0.0
    return ModelEvaluation(
        model_name=model_name,
        recall_at_k=recall_at_k,
        mean_rank=mean_rank,
        total_queries=total,
        top_k=top_k,
        dataset_fingerprint=dataset_fingerprint,
        embedding_dimension=len(document_embeddings[0]),
    )


def _validate_dimensions(
    *,
    document_embeddings: Sequence[Sequence[float]],
    query_embeddings: Sequence[Sequence[float]],
) -> None:
    """Ensure embeddings are non-empty and share the same dimensionality.

    Args:
        document_embeddings: Embeddings produced for documents.
        query_embeddings: Embeddings produced for queries.

    Raises:
        ValueError: If embeddings are empty or dimensions mismatch.
    """
    if not document_embeddings or not query_embeddings:
        raise ValueError("Embeddings must not be empty.")
    doc_dim = len(document_embeddings[0])
    query_dim = len(query_embeddings[0])
    if doc_dim == 0 or query_dim == 0:
        raise ValueError("Embedding vectors must contain at least one dimension.")
    if doc_dim != query_dim:
        raise ValueError(
            f"Embedding dimensions differ (documents={doc_dim}, queries={query_dim}).",
        )


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First embedding vector.
        b: Second embedding vector.

    Returns:
        Cosine similarity value in the range [-1, 1].

    Raises:
        ValueError: If vector lengths differ.
    """
    if len(a) != len(b):
        raise ValueError("Cannot compute similarity on vectors of different lengths.")
    numerator = sum(x * y for x, y in zip(a, b))
    denominator = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def _default_model_loader(model_name: str) -> EmbeddingModel:
    """Construct a SentenceTransformer model for evaluation.

    Args:
        model_name: Model name or path passed to ``SentenceTransformer``.

    Returns:
        Instantiated SentenceTransformer model.
    """
    return cast(EmbeddingModel, SentenceTransformer(model_name))
