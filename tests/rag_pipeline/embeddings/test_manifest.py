from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.rag_pipeline.embeddings.manifest import (
    ArtifactManifest,
    load_manifest,
    manifest_path,
    save_manifest,
)


def test_save_and_load_manifest(tmp_path: Path) -> None:
    created_at = datetime.now(tz=timezone.utc).isoformat()
    manifest = ArtifactManifest(
        version="2024-01-01T00:00:00Z",
        base_model="Qwen/Qwen3-Embedding-0.6B",
        dataset_fingerprint="abc123",
        train_pair_count=10,
        validation_pair_count=2,
        embedding_dimension=1024,
        hyperparameters={"epochs": 2, "batch_size": 8},
        commit_hash="deadbeef",
        created_at=created_at,
    )
    path = save_manifest(manifest, tmp_path)
    assert path == manifest_path(tmp_path)
    loaded = load_manifest(path)
    assert loaded == manifest
