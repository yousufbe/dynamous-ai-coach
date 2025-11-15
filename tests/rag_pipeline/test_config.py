from dataclasses import replace
from pathlib import Path

import pytest

from src.rag_pipeline.config import (
    DEFAULT_SUPPORTED_EXTENSIONS,
    RagIngestionConfig,
    get_rag_ingestion_config,
    iter_supported_extensions,
    _get_bool,
    _parse_directories,
    _parse_extensions,
)


@pytest.mark.unit
def test_get_rag_ingestion_config_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variables are optional and sensible defaults exist."""
    monkeypatch.delenv("RAG_SOURCE_DIRS", raising=False)
    config = get_rag_ingestion_config()
    assert isinstance(config, RagIngestionConfig)
    assert config.source_directories
    assert config.supported_extensions == DEFAULT_SUPPORTED_EXTENSIONS
    assert config.chunk_min_chars < config.chunk_max_chars


@pytest.mark.unit
def test_get_rag_ingestion_config_parses_custom_directories(monkeypatch: pytest.MonkeyPatch) -> None:
    """Multiple comma-separated directories should be parsed."""
    monkeypatch.setenv("RAG_SOURCE_DIRS", "docs, ../shared")
    config = get_rag_ingestion_config()
    resolved = [Path("docs").resolve(), Path("../shared").resolve()]
    assert config.source_directories == resolved


@pytest.mark.unit
def test_parse_directories_handles_whitespace(tmp_path: Path) -> None:
    """_parse_directories should strip whitespace and resolve paths."""
    first = tmp_path / "docs"
    second = tmp_path / "manuals"
    raw = f" {first} , {second} "
    directories = _parse_directories(raw)
    assert directories == [first.resolve(), second.resolve()]


@pytest.mark.unit
def test_parse_extensions_normalizes_values() -> None:
    """_parse_extensions should add leading dots and deduplicate."""
    extensions = _parse_extensions("pdf, TXT , .md, .pdf")
    assert set(extensions) == {".pdf", ".txt", ".md"}


@pytest.mark.unit
def test_get_bool_rejects_invalid_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid boolean environment variables should raise ValueError."""
    monkeypatch.setenv("RAG_FORCE_REINGEST", "later")
    with pytest.raises(ValueError):
        _get_bool("RAG_FORCE_REINGEST", default=False)


@pytest.mark.unit
def test_iter_supported_extensions_lowercases(monkeypatch: pytest.MonkeyPatch) -> None:
    """iter_supported_extensions normalizes casing."""
    monkeypatch.setenv("RAG_SUPPORTED_EXTENSIONS", "PDF,Doc")
    config = get_rag_ingestion_config()
    extensions = iter_supported_extensions(config)
    assert extensions == (".doc", ".pdf")


@pytest.mark.unit
def test_require_sources_raises_for_missing_directory(tmp_path: Path) -> None:
    """RagIngestionConfig.require_sources should detect missing directories."""
    config = get_rag_ingestion_config()
    missing = tmp_path / "missing"
    patched = replace(config, source_directories=[missing])
    with pytest.raises(FileNotFoundError):
        patched.require_sources()


@pytest.mark.unit
def test_embedding_dimension_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Embedding dimension should be configurable via environment variable."""
    monkeypatch.setenv("RAG_EMBEDDING_DIMENSION", "2048")
    config = get_rag_ingestion_config()
    assert config.embedding_dimension == 2048
