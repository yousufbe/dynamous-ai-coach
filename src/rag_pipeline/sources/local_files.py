"""Local filesystem discovery adapter."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence

from src.rag_pipeline.config import RagIngestionConfig, iter_supported_extensions
from src.rag_pipeline.schemas import DocumentInput, DocumentMetadata, SourceType
from src.shared.logging import LoggerProtocol, get_logger

logger: LoggerProtocol = get_logger(__name__)


def discover_documents(
    config: RagIngestionConfig,
    glob_patterns: Sequence[str] | None = None,
) -> Iterator[DocumentInput]:
    """Yield DocumentInput instances for every eligible file in source dirs."""
    patterns: Sequence[str] = glob_patterns or ["**/*"]
    extensions = set(iter_supported_extensions(config))
    for base_dir in config.source_directories:
        if not base_dir.exists():
            logger.warning(
                "discovery_directory_missing",
                directory=str(base_dir),
            )
            continue
        for pattern in patterns:
            yield from _yield_documents_for_pattern(
                base_dir=base_dir,
                pattern=pattern,
                extensions=extensions,
            )


def _yield_documents_for_pattern(
    base_dir: Path,
    pattern: str,
    extensions: set[str],
) -> Iterator[DocumentInput]:
    for path in base_dir.glob(pattern):
        if not path.is_file():
            continue
        extension: str = path.suffix.lower()
        if extension not in extensions:
            continue
        try:
            stat_result = path.stat()
            content_hash = _hash_file(path)
        except OSError as exc:
            logger.warning(
                "discovery_failed_to_read_file",
                file=str(path),
                error=str(exc),
            )
            continue
        metadata = DocumentMetadata(
            location=path.resolve(),
            document_type=extension.lstrip(".") or "unknown",
            source_type=SourceType.LOCAL_FILE,
            content_hash=content_hash,
            size_bytes=stat_result.st_size,
            last_modified=_safe_datetime(stat_result.st_mtime),
        )
        document = DocumentInput(
            metadata=metadata,
            display_name=path.name,
        )
        logger.debug(
            "discovered_document",
            file=str(path),
            hash=metadata.content_hash,
            size_bytes=metadata.size_bytes,
        )
        yield document


def _hash_file(path: Path) -> str:
    """Return SHA-256 hash of the file contents."""
    digest = hashlib.sha256()
    with path.open("rb") as buffer:
        for chunk in iter(lambda: buffer.read(65536), b""):
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _safe_datetime(timestamp: float | None) -> datetime | None:
    """Convert timestamps to aware datetime values."""
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
