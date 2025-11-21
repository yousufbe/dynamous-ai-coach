"""Helpers to prepare fine-tuning datasets for embeddings.

This module keeps data prep deterministic by hashing query/document pairs and
writing JSONL splits that can be reproduced and versioned. It intentionally
stays light on dependencies (no external synthesis) to comply with KISS/YAGNI.
"""

from __future__ import annotations

import json
import random
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class QueryDocumentPair:
    """Represents a training example linking a query to a document text."""

    query: str
    document: str
    source: str
    document_id: str
    corpus_version: str | None = None


def write_jsonl(pairs: Sequence[QueryDocumentPair], output_path: Path) -> None:
    """Persist query-document pairs to JSONL with deterministic ordering.

    Args:
        pairs: Examples to write.
        output_path: Destination path; parent directories are created if needed.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fp:
        for pair in pairs:
            fp.write(json.dumps(asdict(pair), ensure_ascii=False))
            fp.write("\n")


def read_jsonl(input_path: Path) -> list[QueryDocumentPair]:
    """Load query-document pairs from JSONL."""
    pairs: list[QueryDocumentPair] = []
    with input_path.open("r", encoding="utf-8") as fp:
        for line in fp:
            if not line.strip():
                continue
            data = json.loads(line)
            pairs.append(
                QueryDocumentPair(
                    query=str(data["query"]),
                    document=str(data["document"]),
                    source=str(data["source"]),
                    document_id=str(data["document_id"]),
                    corpus_version=data.get("corpus_version"),
                ),
            )
    return pairs


def split_pairs(
    pairs: Sequence[QueryDocumentPair],
    *,
    validation_fraction: float = 0.1,
    seed: int = 0,
) -> tuple[list[QueryDocumentPair], list[QueryDocumentPair]]:
    """Deterministically split pairs into train/validation sets.

    Args:
        pairs: Full dataset of query-document pairs.
        validation_fraction: Fraction of items to place in the validation set.
        seed: Seed for deterministic shuffling.

    Returns:
        Tuple of (train_pairs, validation_pairs).
    """
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation_fraction must be between 0 and 1.")
    shuffled = list(pairs)
    random.Random(seed).shuffle(shuffled)
    split_index = int(len(shuffled) * (1.0 - validation_fraction))
    return shuffled[:split_index], shuffled[split_index:]


def compute_fingerprint(pairs: Iterable[QueryDocumentPair]) -> str:
    """Compute a stable fingerprint for a dataset of pairs.

    The fingerprint is a SHA256 hash of sorted pair representations to ensure
    reproducibility across runs.
    """
    serialized = []
    for pair in pairs:
        serialized.append(
            json.dumps(
                {
                    "query": pair.query,
                    "document": pair.document,
                    "source": pair.source,
                    "document_id": pair.document_id,
                    "corpus_version": pair.corpus_version or "",
                },
                ensure_ascii=False,
            ),
        )
    serialized.sort()
    digest = hashlib.sha256("\n".join(serialized).encode("utf-8")).hexdigest()
    return digest
