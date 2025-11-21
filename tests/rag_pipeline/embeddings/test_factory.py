from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.rag_pipeline.config import get_rag_ingestion_config
from src.rag_pipeline.embeddings.client_types import (
    EmbeddingBatchMetrics,
    EmbeddingModelInfo,
    EmbeddingResponse,
)
from src.rag_pipeline.embeddings.factory import create_embedding_client
from src.rag_pipeline.embeddings.manifest import ArtifactManifest, save_manifest


class DummyEmbeddingClient:
    def __init__(self, label: str) -> None:
        self.model_info = EmbeddingModelInfo(
            model=label,
            dataset_fingerprint=None,
            artifact_version=None,
        )

    def close(self) -> None:  # pragma: no cover - not used in test
        return None

    def embed_texts(self, texts, *, correlation_id=None):  # type: ignore[override]
        return EmbeddingResponse(embeddings=[], metrics=[EmbeddingBatchMetrics(batch_id="b", item_count=len(texts), retry_count=0, duration_ms=0.0)])

    def embed_document_chunks(self, chunks, *, correlation_id=None):  # type: ignore[override]
        return []


def test_create_embedding_client_prefers_fine_tuned(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manifest_dir = tmp_path / "model"
    manifest_dir.mkdir()
    save_manifest(
        ArtifactManifest(
            version="v1",
            base_model="base",
            dataset_fingerprint="fp",
            train_pair_count=1,
            validation_pair_count=1,
            embedding_dimension=2,
            hyperparameters={"epochs": 1},
            commit_hash="deadbeef",
            created_at="2024-01-01T00:00:00Z",
        ),
        manifest_dir,
    )
    dummy_client = DummyEmbeddingClient("ft")
    monkeypatch.setattr(
        "src.rag_pipeline.embeddings.factory.SentenceTransformerEmbeddingClient",
        lambda **_: dummy_client,
    )
    config = get_rag_ingestion_config()
    patched = replace(
        config,
        use_fine_tuned_embeddings=True,
        fine_tuned_model_path=manifest_dir,
    )
    client = create_embedding_client(patched)
    assert client is dummy_client


def test_create_embedding_client_raises_when_path_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    config = replace(get_rag_ingestion_config(), use_fine_tuned_embeddings=True, fine_tuned_model_path=None)
    with pytest.raises(ValueError):
        create_embedding_client(config)


def test_create_embedding_client_uses_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_client = DummyEmbeddingClient("remote")
    monkeypatch.setattr(
        "src.rag_pipeline.embeddings.factory.QwenEmbeddingClient.from_config",
        lambda **kwargs: dummy_client,
    )
    config = replace(get_rag_ingestion_config(), use_fine_tuned_embeddings=False)
    client = create_embedding_client(config, api_key="secret")
    assert client is dummy_client
