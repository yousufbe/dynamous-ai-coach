"""Configuration helpers for the Docling-based ingestion pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_SUPPORTED_EXTENSIONS: tuple[str, ...] = (
    ".pdf",
    ".docx",
    ".doc",
    ".pptx",
    ".ppt",
    ".xlsx",
    ".xls",
    ".md",
    ".markdown",
    ".txt",
)


@dataclass(frozen=True, slots=True)
class RagIngestionConfig:
    """Configuration values that govern ingestion behaviour.

    Attributes:
        source_directories: Ordered list of directories that should be scanned
            by document discovery adapters.
        supported_extensions: File extensions that are eligible for ingestion.
        chunk_min_chars: Minimum character count per chunk before merging.
        chunk_max_chars: Maximum character count per chunk before splitting.
        chunk_overlap_chars: Desired overlap between neighbouring chunks.
        docling_chunk_target_tokens: Target number of tokens handed to
            Docling's HybridChunker.
        docling_language: Language hint for Docling tokenisation.
        embedding_model: Identifier for the embedding model.
        use_fine_tuned_embeddings: Toggle enabling a fine-tuned local model.
        fine_tuned_model_path: Filesystem path to the fine-tuned model when the
            flag above is enabled.
        embedding_batch_size: Number of chunks embedded per batch.
        embedding_retry_count: Total embedding retry attempts for transient
            failures.
        embedding_timeout_seconds: Per-request timeout for embedding calls.
        embedding_retry_backoff_seconds: Base wait time used for exponential
            backoff between embedding retries.
        embedding_dimension: Expected embedding vector size from the client.
        database_url: Connection string to Supabase/PostgreSQL with PGVector.
        supabase_schema: Database schema that owns sources/chunks tables.
        sources_table: Name of the table that stores document-level metadata.
        chunks_table: Name of the table that stores chunk rows.
        force_reingest: When true, every discovered document is re-processed
            regardless of stored content hashes.
        pipeline_id: Identifier emitted in logs/metrics to disambiguate runs.
    """

    source_directories: list[Path]
    supported_extensions: tuple[str, ...]
    chunk_min_chars: int
    chunk_max_chars: int
    chunk_overlap_chars: int
    docling_chunk_target_tokens: int
    docling_language: str
    embedding_model: str
    use_fine_tuned_embeddings: bool
    fine_tuned_model_path: Path | None
    embedding_batch_size: int
    embedding_retry_count: int
    embedding_timeout_seconds: int
    embedding_retry_backoff_seconds: float
    embedding_dimension: int
    database_url: str
    supabase_schema: str
    sources_table: str
    chunks_table: str
    force_reingest: bool
    pipeline_id: str

    def require_sources(self) -> None:
        """Ensure at least one source directory exists on disk."""
        missing: list[str] = [
            str(path)
            for path in self.source_directories
            if not path.exists()
        ]
        if missing:
            missing_str: str = ", ".join(missing)
            raise FileNotFoundError(
                f"Configured ingestion directories do not exist: {missing_str}",
            )


def get_rag_ingestion_config() -> RagIngestionConfig:
    """Load ingestion configuration from environment variables.

    Returns:
        RagIngestionConfig populated with sane defaults so that developers can
        test the pipeline without large amounts of setup.
    """
    source_directories: list[Path] = _parse_directories(
        os.getenv("RAG_SOURCE_DIRS") or "./documents",
    )
    supported_extensions: tuple[str, ...] = _parse_extensions(
        raw=os.getenv("RAG_SUPPORTED_EXTENSIONS"),
    )
    use_fine_tuned_embeddings: bool = _get_bool(
        "RAG_USE_FINE_TUNED_EMBEDDINGS",
        default=_get_bool("USE_FINE_TUNED_EMBEDDINGS", default=False),
    )
    fine_tuned_raw: str | None = os.getenv(
        "RAG_EMBEDDING_MODEL_FINE_TUNED_PATH",
        os.getenv("EMBEDDING_MODEL_FINE_TUNED_PATH"),
    )
    fine_tuned_model_path: Path | None = (
        Path(fine_tuned_raw).expanduser().resolve()
        if fine_tuned_raw
        else None
    )
    return RagIngestionConfig(
        source_directories=source_directories,
        supported_extensions=supported_extensions,
        chunk_min_chars=_get_int("RAG_CHUNK_MIN_CHARS", default=400),
        chunk_max_chars=_get_int("RAG_CHUNK_MAX_CHARS", default=1000),
        chunk_overlap_chars=_get_int("RAG_CHUNK_OVERLAP_CHARS", default=60),
        docling_chunk_target_tokens=_get_int(
            "RAG_DOCLING_TARGET_TOKENS",
            default=280,
        ),
        docling_language=os.getenv("RAG_DOCLING_LANGUAGE", "en"),
        embedding_model=os.getenv(
            "RAG_EMBEDDING_MODEL",
            "Qwen/Qwen3-Embedding-0.6B",
        ),
        use_fine_tuned_embeddings=use_fine_tuned_embeddings,
        fine_tuned_model_path=fine_tuned_model_path,
        embedding_batch_size=_get_int("RAG_EMBEDDING_BATCH_SIZE", 8),
        embedding_retry_count=_get_int("RAG_EMBEDDING_RETRY_COUNT", 1),
        embedding_timeout_seconds=_get_int(
            "RAG_EMBEDDING_TIMEOUT_SECONDS",
            60,
        ),
        embedding_retry_backoff_seconds=_get_float(
            "RAG_EMBEDDING_RETRY_BACKOFF_SECONDS",
            2.0,
        ),
        embedding_dimension=_get_int("RAG_EMBEDDING_DIMENSION", 1024),
        database_url=os.getenv("RAG_DATABASE_URL", ""),
        supabase_schema=os.getenv("RAG_SUPABASE_SCHEMA", "public"),
        sources_table=os.getenv("RAG_SOURCES_TABLE", "sources"),
        chunks_table=os.getenv("RAG_CHUNKS_TABLE", "chunks"),
        force_reingest=_get_bool("RAG_FORCE_REINGEST", default=False),
        pipeline_id=os.getenv("RAG_PIPELINE_ID", "local-dev"),
    )


def _parse_directories(raw: str) -> list[Path]:
    """Parse a comma-separated list of directories."""
    directories: list[Path] = []
    for chunk in raw.split(","):
        value: str = chunk.strip()
        if value:
            directories.append(Path(value).expanduser().resolve())
    return directories


def _parse_extensions(raw: str | None) -> tuple[str, ...]:
    """Parse custom extensions or fall back to defaults."""
    if not raw:
        return DEFAULT_SUPPORTED_EXTENSIONS
    extensions: list[str] = []
    for part in raw.split(","):
        value: str = part.strip().lower()
        if not value:
            continue
        if not value.startswith("."):
            value = f".{value}"
        extensions.append(value)
    return tuple(sorted(set(extensions)))


def _get_int(name: str, default: int) -> int:
    """Fetch an integer from environment variables."""
    raw: str | None = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid integer for {name}: {raw}") from exc


def _get_bool(name: str, default: bool) -> bool:
    """Parse a boolean flag from the environment."""
    raw: str | None = os.getenv(name)
    if raw is None:
        return default
    normalized: str = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean for {name}: {raw}")


def iter_supported_extensions(config: RagIngestionConfig) -> Iterable[str]:
    """Yield normalized supported extensions for convenience."""
    return tuple(ext.lower() for ext in config.supported_extensions)


def _get_float(name: str, default: float) -> float:
    """Parse a floating point value from environment variables."""
    raw: str | None = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid float for {name}: {raw}") from exc
