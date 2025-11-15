import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from src.rag_pipeline.config import RagIngestionConfig, get_rag_ingestion_config
from src.rag_pipeline.sources import local_files


def _config_with_directory(directory: Path) -> RagIngestionConfig:
    config = get_rag_ingestion_config()
    return replace(config, source_directories=[directory])


@pytest.mark.unit
def test_discover_documents_filters_extensions(tmp_path: Path) -> None:
    """Only supported file extensions should be discovered."""
    config = _config_with_directory(tmp_path)
    allowed = tmp_path / "doc1.pdf"
    disallowed = tmp_path / "script.exe"
    allowed.write_text("hello", encoding="utf-8")
    disallowed.write_text("should be ignored", encoding="utf-8")
    documents = list(local_files.discover_documents(config))
    assert len(documents) == 1
    assert documents[0].metadata.location == allowed.resolve()


@pytest.mark.unit
def test_discover_documents_hash_matches(tmp_path: Path) -> None:
    """SHA-256 content hash should match actual file contents."""
    config = _config_with_directory(tmp_path)
    sample = tmp_path / "doc2.txt"
    payload = b"Docling pipeline\n"
    sample.write_bytes(payload)
    expected_hash = hashlib.sha256(payload).hexdigest()
    documents = list(local_files.discover_documents(config))
    assert documents
    assert documents[0].metadata.content_hash == expected_hash


@pytest.mark.unit
def test_discover_documents_with_glob_patterns(tmp_path: Path) -> None:
    """Glob patterns should limit which files are discovered."""
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "match.md").write_text("match me", encoding="utf-8")
    (tmp_path / "skip.md").write_text("skip me", encoding="utf-8")
    config = _config_with_directory(tmp_path)
    documents = list(local_files.discover_documents(config, glob_patterns=["nested/*.md"]))
    assert len(documents) == 1
    assert documents[0].metadata.location.name == "match.md"


@pytest.mark.unit
def test_missing_directory_logs_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Missing directories should emit a warning instead of raising."""
    missing = tmp_path / "missing"
    config = _config_with_directory(missing)
    with caplog.at_level("WARNING"):
        documents = list(local_files.discover_documents(config))
    assert documents == []
    assert any("discovery_directory_missing" in record.message for record in caplog.records)
