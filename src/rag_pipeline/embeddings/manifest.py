"""Manifests for fine-tuned embedding artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping


ManifestHyperparameters = Mapping[str, int | float | str | bool]


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    """Metadata stored alongside a fine-tuned embedding artifact.

    Attributes:
        version: Version identifier for the artifact directory (typically a
            timestamp or semantic version).
        base_model: Name or path of the base SentenceTransformer checkpoint.
        dataset_fingerprint: Stable hash of the training/validation pairs.
        train_pair_count: Number of training examples.
        validation_pair_count: Number of validation examples.
        embedding_dimension: Expected embedding vector size of the model.
        hyperparameters: Training hyperparameters used to produce the artifact.
        commit_hash: Git commit hash recorded at training time.
        created_at: ISO-8601 timestamp of when the artifact was written.
    """

    version: str
    base_model: str
    dataset_fingerprint: str
    train_pair_count: int
    validation_pair_count: int
    embedding_dimension: int
    hyperparameters: ManifestHyperparameters
    commit_hash: str
    created_at: str


def manifest_path(output_dir: Path) -> Path:
    """Return the canonical path for the manifest file under an artifact dir.

    Args:
        output_dir: Directory containing a fine-tuned artifact.

    Returns:
        Path to the manifest JSON file.
    """
    return output_dir / "manifest.json"


def save_manifest(manifest: ArtifactManifest, output_dir: Path) -> Path:
    """Write the manifest to ``manifest.json`` inside the artifact directory.

    Args:
        manifest: Metadata to persist.
        output_dir: Artifact directory where the manifest should be written.

    Returns:
        Path to the saved manifest file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_path(output_dir)
    path.write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_manifest(path: Path) -> ArtifactManifest:
    """Load a manifest from disk.

    Args:
        path: Path to a manifest JSON file.

    Returns:
        Parsed ArtifactManifest.

    Raises:
        ValueError: If the file contents are not a JSON object.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Manifest content must be a JSON object.")
    return ArtifactManifest(
        version=str(data["version"]),
        base_model=str(data["base_model"]),
        dataset_fingerprint=str(data["dataset_fingerprint"]),
        train_pair_count=int(data["train_pair_count"]),
        validation_pair_count=int(data["validation_pair_count"]),
        embedding_dimension=int(data["embedding_dimension"]),
        hyperparameters=dict(data["hyperparameters"]),
        commit_hash=str(data["commit_hash"]),
        created_at=str(data["created_at"]),
    )
