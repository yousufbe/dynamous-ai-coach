"""Typed schemas shared across the ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence

from pydantic import BaseModel, Field, model_validator

JSONValue = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]


class SourceType(str, Enum):
    """Enumerates supported document source types."""

    LOCAL_FILE = "local_file"
    SUPABASE_STORAGE = "supabase_storage"
    EXTERNAL_URL = "external_url"


class SourceIngestionStatus(str, Enum):
    """States tracked for entries in the ``sources`` table."""

    PENDING = "pending"
    INGESTED = "ingested"
    PARTIAL = "partially_ingested"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    """Metadata describing a document scheduled for ingestion."""

    location: Path
    document_type: str
    source_type: SourceType
    content_hash: str
    size_bytes: int
    last_modified: datetime | None = None
    extra_metadata: dict[str, JSONValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentInput:
    """Input passed from discovery adapters to the pipeline."""

    metadata: DocumentMetadata
    display_name: str


@dataclass(frozen=True, slots=True)
class ChunkMetadata:
    """Chunk-level metadata captured for tracing and observability."""

    page_number: int | None
    chunk_index: int
    section_heading: str | None
    structural_type: str | None
    extra: dict[str, JSONValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChunkData:
    """Text chunk produced by Docling hybrid chunker."""

    text: str
    metadata: ChunkMetadata
    character_count: int
    token_estimate: int | None = None

    def truncated_text(self, limit: int = 120) -> str:
        """Return a preview of the chunk for logging."""
        return self.text[:limit] + ("…" if len(self.text) > limit else "")


@dataclass(frozen=True, slots=True)
class EmbeddingRecord:
    """Dense vector representation of a chunk."""

    vector: Sequence[float]
    model: str
    dimensions: int


@dataclass(frozen=True, slots=True)
class ChunkRecord:
    """Combined chunk and embedding payload stored in the database."""

    source_location: str
    chunk_index: int
    text: str
    embedding: Sequence[float]
    metadata: dict[str, JSONValue]
    embedding_model: str


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """Represents a row in the ``sources`` table."""

    location: str
    content_hash: str
    status: SourceIngestionStatus
    document_type: str
    source_type: SourceType
    metadata: dict[str, JSONValue]
    error_message: str | None = None


class IngestionRequest(BaseModel):
    """User-facing options for triggering an ingestion run."""

    source_directories: list[str] = Field(
        default_factory=list,
        description="Override config-defined directories on a per-run basis.",
    )
    document_glob_patterns: list[str] = Field(
        default_factory=lambda: ["**/*"],
        description="Glob patterns applied within each source directory.",
    )
    force_reingest: bool = Field(
        default=False,
        description="Reprocess all documents even if hashes match.",
    )
    pipeline_id: str | None = Field(
        default=None,
        description="Override the pipeline identifier for this run.",
    )

    @model_validator(mode="after")
    def _dedupe_globs(self) -> "IngestionRequest":
        """Ensure glob patterns are unique while preserving order."""
        unique: list[str] = []
        for pattern in self.document_glob_patterns:
            if pattern not in unique:
                unique.append(pattern)
        self.document_glob_patterns = unique or ["**/*"]
        return self

class DocumentIngestionResult(BaseModel):
    """Per-document summary returned at the end of ingestion."""

    location: str
    status: SourceIngestionStatus
    chunks_ingested: int
    error: str | None = None
    duration_ms: float | None = None


class IngestionStatistics(BaseModel):
    """Aggregated metrics for an ingestion run."""

    documents_discovered: int
    documents_ingested: int
    documents_failed: int
    chunks_created: int


class IngestionResult(BaseModel):
    """Return type for both CLI and ingestion skill invocations."""

    started_at: datetime
    completed_at: datetime
    pipeline_id: str
    documents: list[DocumentIngestionResult]
    stats: IngestionStatistics

    @property
    def duration_seconds(self) -> float:
        """Compute duration using timestamps."""
        return (self.completed_at - self.started_at).total_seconds()

    def failed_documents(self) -> Iterable[DocumentIngestionResult]:
        """Iterate over failed document results."""
        return (doc for doc in self.documents if doc.status == SourceIngestionStatus.FAILED)
