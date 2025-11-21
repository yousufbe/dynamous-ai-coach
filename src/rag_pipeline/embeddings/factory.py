"""Factory helpers for selecting an embedding client."""

from __future__ import annotations

from pathlib import Path

from src.rag_pipeline.config import RagIngestionConfig
from src.rag_pipeline.embeddings.client_types import EmbeddingClientProtocol
from src.rag_pipeline.embeddings.local_client import SentenceTransformerEmbeddingClient
from src.rag_pipeline.embeddings.manifest import ArtifactManifest, load_manifest, manifest_path
from src.rag_pipeline.embeddings.qwen_client import QwenEmbeddingClient
from src.shared.logging import LoggerProtocol, get_logger
from src.shared.tracing import Tracer


def create_embedding_client(
    config: RagIngestionConfig,
    *,
    tracer: Tracer | None = None,
    logger: LoggerProtocol | None = None,
    api_key: str | None = None,
) -> EmbeddingClientProtocol:
    """Construct an embedding client based on configuration flags.

    Args:
        config: Ingestion configuration.
        tracer: Optional tracer passed into the client.
        logger: Optional logger override.
        api_key: Optional API key forwarded to the remote client.

    Returns:
        Initialized embedding client ready for use.

    Raises:
        ValueError: If a fine-tuned model is requested but no path is provided.
    """
    log = logger or get_logger(__name__)
    if config.use_fine_tuned_embeddings:
        model_path = config.fine_tuned_model_path
        if model_path is None:
            raise ValueError("EMBEDDING_MODEL_FINE_TUNED_PATH must be set when USE_FINE_TUNED_EMBEDDINGS is true.")
        manifest = _load_manifest_if_present(model_path)
        client = SentenceTransformerEmbeddingClient(
            model_path=model_path,
            batch_size=config.embedding_batch_size,
            model_label=config.embedding_model,
            manifest=manifest,
            tracer=tracer,
            logger=log,
        )
        log.info(
            "embedding_client_selected",
            backend="sentence_transformer",
            model_label=client.model_info.model,
            dataset_fingerprint=client.model_info.dataset_fingerprint,
            artifact_version=client.model_info.artifact_version,
        )
        return client
    remote_client = QwenEmbeddingClient.from_config(
        config=config,
        api_key=api_key,
        tracer=tracer,
    )
    log.info(
        "embedding_client_selected",
        backend="qwen_http",
        model_label=remote_client.model_info.model,
    )
    return remote_client


def _load_manifest_if_present(model_path: Path) -> ArtifactManifest | None:
    """Load a manifest when available.

    Args:
        model_path: Path to the fine-tuned model directory.

    Returns:
        ArtifactManifest if ``manifest.json`` exists, otherwise ``None``.
    """
    path = manifest_path(model_path)
    if not path.exists():
        return None
    return load_manifest(path)
