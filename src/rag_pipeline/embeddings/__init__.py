"""Embedding utilities and clients used by the ingestion pipeline."""

from __future__ import annotations

from .client_types import (
    EmbeddingBatchMetrics,
    EmbeddingClientProtocol,
    EmbeddingModelInfo,
    EmbeddingResponse,
)
from .factory import create_embedding_client
from .local_client import SentenceTransformerEmbeddingClient
from .qwen_client import EmbeddingError, QwenEmbeddingClient
from .manifest import ArtifactManifest, load_manifest, manifest_path, save_manifest
from .train import TrainingConfig, TrainingResult, train_model
from .eval import (
    EvaluationReport,
    EvaluationRequest,
    ModelEvaluation,
    run_evaluation,
    write_report,
)

__all__ = [
    "EmbeddingBatchMetrics",
    "EmbeddingClientProtocol",
    "EmbeddingModelInfo",
    "EmbeddingError",
    "EmbeddingResponse",
    "QwenEmbeddingClient",
    "ArtifactManifest",
    "EvaluationReport",
    "EvaluationRequest",
    "ModelEvaluation",
    "SentenceTransformerEmbeddingClient",
    "create_embedding_client",
    "TrainingConfig",
    "TrainingResult",
    "load_manifest",
    "manifest_path",
    "run_evaluation",
    "save_manifest",
    "train_model",
    "write_report",
]
