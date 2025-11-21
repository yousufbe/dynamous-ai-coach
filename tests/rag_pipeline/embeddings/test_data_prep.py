from __future__ import annotations

from pathlib import Path

import pytest

from src.rag_pipeline.embeddings.data_prep import (
    QueryDocumentPair,
    compute_fingerprint,
    read_jsonl,
    split_pairs,
    write_jsonl,
)


def _build_pairs() -> list[QueryDocumentPair]:
    return [
        QueryDocumentPair(
            query="What is policy?",
            document="Policy text A",
            source="handbook",
            document_id="docA",
            corpus_version="v1",
        ),
        QueryDocumentPair(
            query="How to reset password?",
            document="Reset steps",
            source="runbook",
            document_id="docB",
            corpus_version="v1",
        ),
        QueryDocumentPair(
            query="Who to contact?",
            document="Contact HR",
            source="handbook",
            document_id="docC",
            corpus_version="v1",
        ),
    ]


def test_split_pairs_is_deterministic() -> None:
    pairs = _build_pairs()
    train_a, valid_a = split_pairs(pairs, validation_fraction=0.33, seed=123)
    train_b, valid_b = split_pairs(pairs, validation_fraction=0.33, seed=123)
    assert train_a == train_b
    assert valid_a == valid_b
    assert len(valid_a) == 1
    assert len(train_a) == 2


def test_write_and_read_jsonl_round_trip(tmp_path: Path) -> None:
    pairs = _build_pairs()
    output = tmp_path / "pairs.jsonl"
    write_jsonl(pairs, output)
    loaded = read_jsonl(output)
    assert loaded == pairs


def test_compute_fingerprint_changes_on_content() -> None:
    pairs = _build_pairs()
    base_fp = compute_fingerprint(pairs)
    modified = list(pairs)
    modified[0] = QueryDocumentPair(
        query="Altered query",
        document=modified[0].document,
        source=modified[0].source,
        document_id=modified[0].document_id,
        corpus_version=modified[0].corpus_version,
    )
    new_fp = compute_fingerprint(modified)
    assert base_fp != new_fp


def test_split_pairs_invalid_fraction() -> None:
    with pytest.raises(ValueError):
        split_pairs(_build_pairs(), validation_fraction=0.0)
