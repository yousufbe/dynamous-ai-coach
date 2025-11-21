"""Training entrypoint for fine-tuning embedding models."""

from __future__ import annotations

import random
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol, Sequence, cast

import torch
from sentence_transformers import InputExample, SentenceTransformer, losses
from torch.utils.data import DataLoader, Dataset

from src.rag_pipeline.embeddings.data_prep import (
    QueryDocumentPair,
    compute_fingerprint,
    read_jsonl,
)
from src.rag_pipeline.embeddings.manifest import ArtifactManifest, save_manifest
from src.shared.logging import LoggerProtocol, get_logger


class TrainableModel(Protocol):
    """Protocol describing the subset of SentenceTransformer used for training."""

    def fit(
        self,
        train_objectives: Sequence[tuple[DataLoader[InputExample], losses.MultipleNegativesRankingLoss]],
        *,
        epochs: int,
        warmup_steps: int,
        show_progress_bar: bool,
        optimizer_params: dict[str, float],
    ) -> None:
        """Run fine-tuning."""

    def save(self, path: str) -> None:
        """Persist the model to disk."""

    def get_sentence_embedding_dimension(self) -> int:
        """Return the embedding dimension for the model."""


ModelBuilder = Callable[[str], TrainableModel]


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """Configuration required to run a fine-tuning job.

    Attributes:
        train_path: JSONL file containing training pairs.
        validation_path: JSONL file containing validation pairs.
        output_dir: Directory where versioned artifacts will be written.
        base_model: Base checkpoint used to initialize the model.
        batch_size: Training batch size.
        epochs: Number of epochs to train.
        learning_rate: Optimizer learning rate.
        warmup_steps: Number of warmup steps for the scheduler.
        output_version: Optional precomputed version label for the artifact.
        dataset_fingerprint: Optional fingerprint override; if omitted it will
            be computed from the dataset contents.
        seed: Random seed for reproducible shuffling.
    """

    train_path: Path
    validation_path: Path
    output_dir: Path
    base_model: str = "Qwen/Qwen3-Embedding-0.6B"
    batch_size: int = 16
    epochs: int = 1
    learning_rate: float = 2e-5
    warmup_steps: int = 0
    output_version: str | None = None
    dataset_fingerprint: str | None = None
    seed: int = 42


@dataclass(frozen=True, slots=True)
class TrainingResult:
    """Outputs produced by a training run."""

    artifact_dir: Path
    manifest: ArtifactManifest


def train_model(
    config: TrainingConfig,
    *,
    model_builder: ModelBuilder | None = None,
    logger: LoggerProtocol | None = None,
) -> TrainingResult:
    """Fine-tune the embedding model using prepared query-document pairs.

    Args:
        config: Training parameters and dataset locations.
        model_builder: Optional factory for constructing the model; defaults to
            ``SentenceTransformer``.
        logger: Structured logger to use during training.

    Returns:
        TrainingResult containing the artifact location and manifest metadata.

    Raises:
        FileNotFoundError: If the training or validation files do not exist.
        ValueError: If the training dataset is empty.
    """
    log = logger or get_logger(__name__)
    if not config.train_path.exists():
        raise FileNotFoundError(f"Training data not found at {config.train_path}")
    if not config.validation_path.exists():
        raise FileNotFoundError(f"Validation data not found at {config.validation_path}")
    train_pairs = read_jsonl(config.train_path)
    validation_pairs = read_jsonl(config.validation_path)
    if not train_pairs:
        raise ValueError("Training dataset is empty; cannot run fine-tuning.")
    dataset_fingerprint = config.dataset_fingerprint or compute_fingerprint([*train_pairs, *validation_pairs])
    random.seed(config.seed)
    torch.manual_seed(config.seed)
    builder = model_builder or _default_model_builder
    model = builder(config.base_model)
    train_loader = _build_dataloader(train_pairs, batch_size=config.batch_size)
    loss = losses.MultipleNegativesRankingLoss(cast(SentenceTransformer, model))
    version = config.output_version or datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = config.output_dir / version
    log.info(
        "embedding_training_started",
        base_model=config.base_model,
        train_examples=len(train_pairs),
        validation_examples=len(validation_pairs),
        batch_size=config.batch_size,
        epochs=config.epochs,
        version=version,
    )
    model.fit(
        train_objectives=[(train_loader, loss)],
        epochs=config.epochs,
        warmup_steps=config.warmup_steps,
        show_progress_bar=False,
        optimizer_params={"lr": config.learning_rate},
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model.save(str(artifact_dir))
    manifest = _build_manifest(
        version=version,
        config=config,
        dataset_fingerprint=dataset_fingerprint,
        train_pair_count=len(train_pairs),
        validation_pair_count=len(validation_pairs),
        embedding_dimension=model.get_sentence_embedding_dimension(),
    )
    manifest_path = save_manifest(manifest, artifact_dir)
    log.info(
        "embedding_training_completed",
        artifact_dir=str(artifact_dir),
        manifest=str(manifest_path),
        dataset_fingerprint=dataset_fingerprint,
        embedding_dimension=manifest.embedding_dimension,
    )
    return TrainingResult(artifact_dir=artifact_dir, manifest=manifest)


def _build_dataloader(pairs: Sequence[QueryDocumentPair], *, batch_size: int) -> DataLoader[InputExample]:
    """Create a dataloader of InputExample instances.

    Args:
        pairs: Training pairs to convert into ``InputExample`` objects.
        batch_size: Batch size for the dataloader.

    Returns:
        Torch dataloader configured for shuffling.
    """
    examples: list[InputExample] = [
        InputExample(texts=[pair.query, pair.document])
        for pair in pairs
    ]
    dataset = _ExampleDataset(examples)
    return DataLoader(dataset, batch_size=batch_size, shuffle=True)


def _build_manifest(
    *,
    version: str,
    config: TrainingConfig,
    dataset_fingerprint: str,
    train_pair_count: int,
    validation_pair_count: int,
    embedding_dimension: int,
) -> ArtifactManifest:
    """Construct a manifest for the trained artifact.

    Args:
        version: Version label used for the artifact directory.
        config: Training configuration.
        dataset_fingerprint: Stable fingerprint for the dataset.
        train_pair_count: Number of training examples.
        validation_pair_count: Number of validation examples.
        embedding_dimension: Output embedding dimension of the model.

    Returns:
        ArtifactManifest populated with metadata for the training run.
    """
    created_at = datetime.now(tz=timezone.utc).isoformat()
    return ArtifactManifest(
        version=version,
        base_model=config.base_model,
        dataset_fingerprint=dataset_fingerprint,
        train_pair_count=train_pair_count,
        validation_pair_count=validation_pair_count,
        embedding_dimension=embedding_dimension,
        hyperparameters={
            "batch_size": config.batch_size,
            "epochs": config.epochs,
            "learning_rate": config.learning_rate,
            "warmup_steps": config.warmup_steps,
            "seed": config.seed,
        },
        commit_hash=_current_commit_hash(),
        created_at=created_at,
    )


def _current_commit_hash() -> str:
    """Return the current git commit hash or ``unknown``.

    Returns:
        Git commit hash string if available, otherwise ``unknown``.
    """
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _default_model_builder(model_name: str) -> TrainableModel:
    """Construct a SentenceTransformer for training.

    Args:
        model_name: Model name or path passed to ``SentenceTransformer``.

    Returns:
        Instantiated SentenceTransformer model.
    """
    return cast(TrainableModel, SentenceTransformer(model_name))


class _ExampleDataset(Dataset[InputExample]):
    """Dataset wrapper to satisfy type checking for training examples."""

    def __init__(self, items: Sequence[InputExample]) -> None:
        self._items = list(items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> InputExample:
        return self._items[index]
