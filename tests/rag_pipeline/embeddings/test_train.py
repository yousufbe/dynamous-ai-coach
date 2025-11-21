from __future__ import annotations

from pathlib import Path
import pytest

from src.rag_pipeline.embeddings.data_prep import QueryDocumentPair, write_jsonl
from src.rag_pipeline.embeddings.train import TrainingConfig, train_model


class StubLoss:
    def __init__(self, model: object) -> None:
        self.model = model


class StubModel:
    def __init__(self, name: str) -> None:
        self.name = name
        self.fit_calls: int = 0
        self.saved_path: Path | None = None
        self.received_objectives: object | None = None

    def fit(
        self,
        train_objectives: object,
        *,
        epochs: int,
        warmup_steps: int,
        show_progress_bar: bool,
        optimizer_params: dict[str, float],
    ) -> None:
        self.fit_calls += 1
        self.received_objectives = train_objectives

    def save(self, path: str) -> None:
        self.saved_path = Path(path)

    def get_sentence_embedding_dimension(self) -> int:
        return 2


def test_train_model_writes_artifact_and_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    train_path = tmp_path / "train.jsonl"
    valid_path = tmp_path / "valid.jsonl"
    write_jsonl(
        [
            QueryDocumentPair(query="q1", document="d1", source="s", document_id="1"),
            QueryDocumentPair(query="q2", document="d2", source="s", document_id="2"),
        ],
        train_path,
    )
    write_jsonl(
        [QueryDocumentPair(query="q3", document="d3", source="s", document_id="3")],
        valid_path,
    )
    stub = StubModel("stub")
    monkeypatch.setattr("src.rag_pipeline.embeddings.train.losses.MultipleNegativesRankingLoss", StubLoss)
    result = train_model(
        TrainingConfig(
            train_path=train_path,
            validation_path=valid_path,
            output_dir=tmp_path / "artifacts",
            output_version="unit-test",
            batch_size=2,
            epochs=1,
        ),
        model_builder=lambda _: stub,
    )
    assert stub.fit_calls == 1
    assert stub.saved_path == result.artifact_dir
    assert result.artifact_dir.name == "unit-test"
    assert result.manifest.train_pair_count == 2
    assert result.manifest.validation_pair_count == 1
    assert result.manifest.dataset_fingerprint
    assert result.manifest.embedding_dimension == 2
