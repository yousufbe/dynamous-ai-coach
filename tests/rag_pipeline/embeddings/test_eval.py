from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pytest

from src.rag_pipeline.embeddings.data_prep import QueryDocumentPair, write_jsonl
from src.rag_pipeline.embeddings.eval import EvaluationRequest, run_evaluation


class MappingModel:
    def __init__(self, name: str, mapping: dict[str, Sequence[float]]) -> None:
        self.name = name
        self._mapping = mapping

    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int | None = None,
        convert_to_numpy: bool = False,
        normalize_embeddings: bool | None = None,
    ) -> list[list[float]]:
        return [list(self._mapping[text]) for text in sentences]

    def get_sentence_embedding_dimension(self) -> int:
        first = next(iter(self._mapping.values()))
        return len(first)


def test_run_evaluation_reports_improvement(tmp_path: Path) -> None:
    validation_path = tmp_path / "valid.jsonl"
    pairs = [
        QueryDocumentPair(query="q1", document="doc-one", source="s", document_id="1"),
        QueryDocumentPair(query="q2", document="doc-two", source="s", document_id="2"),
    ]
    write_jsonl(pairs, validation_path)
    base_mapping = {
        "doc-one": [1.0, 0.0],
        "doc-two": [0.0, 1.0],
        "q1": [0.0, 1.0],
        "q2": [1.0, 0.0],
    }
    tuned_mapping = {
        "doc-one": [1.0, 0.0],
        "doc-two": [0.0, 1.0],
        "q1": [1.0, 0.0],
        "q2": [0.0, 1.0],
    }

    base_model = MappingModel("base", base_mapping)
    tuned_model = MappingModel("tuned", tuned_mapping)

    def loader(name: str) -> MappingModel:
        return base_model if name == "base" else tuned_model

    report = run_evaluation(
        EvaluationRequest(
            validation_path=validation_path,
            base_model_path="base",
            tuned_model_path="tuned",
            top_k=1,
        ),
        model_loader=loader,
    )
    assert report.base.recall_at_k == 0.0
    assert report.tuned.recall_at_k == 1.0
    assert report.dataset_fingerprint == report.base.dataset_fingerprint
    assert report.base.embedding_dimension == 2


def test_run_evaluation_validates_top_k(tmp_path: Path) -> None:
    validation_path = tmp_path / "valid.jsonl"
    write_jsonl(
        [QueryDocumentPair(query="q1", document="d1", source="s", document_id="1")],
        validation_path,
    )
    with pytest.raises(ValueError):
        run_evaluation(
            EvaluationRequest(
                validation_path=validation_path,
                base_model_path="base",
                tuned_model_path="tuned",
                top_k=0,
            ),
        )
