import datetime as dt
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from src.rag_pipeline.schemas import (
    ChunkMetadata,
    ChunkRecord,
    DocumentIngestionResult,
    DocumentMetadata,
    IngestionRequest,
    IngestionResult,
    IngestionStatistics,
    SourceIngestionStatus,
    SourceType,
)


@pytest.mark.unit
def test_ingestion_request_defaults() -> None:
    """IngestionRequest should provide sensible defaults."""
    request = IngestionRequest()
    assert request.source_directories == []
    assert request.document_glob_patterns == ["**/*"]
    assert request.force_reingest is False


@pytest.mark.unit
def test_ingestion_request_deduplicates_globs() -> None:
    """Duplicate glob patterns should be removed while preserving order."""
    request = IngestionRequest(document_glob_patterns=["**/*.pdf", "**/*.pdf", "**/*.md"])
    assert request.document_glob_patterns == ["**/*.pdf", "**/*.md"]


@pytest.mark.unit
def test_ingestion_result_properties() -> None:
    """IngestionResult exposes helper properties used by the CLI."""
    started = dt.datetime.now(tz=dt.timezone.utc)
    completed = started + dt.timedelta(seconds=5)
    documents = [
        DocumentIngestionResult(
            location="a.pdf",
            status=SourceIngestionStatus.INGESTED,
            chunks_ingested=3,
        ),
        DocumentIngestionResult(
            location="b.pdf",
            status=SourceIngestionStatus.FAILED,
            chunks_ingested=0,
            error="conversion failed",
        ),
    ]
    result = IngestionResult(
        started_at=started,
        completed_at=completed,
        pipeline_id="demo",
        documents=documents,
        stats=IngestionStatistics(
            documents_discovered=2,
            documents_ingested=1,
            documents_failed=1,
            chunks_created=3,
        ),
    )
    assert pytest.approx(result.duration_seconds, rel=1e-6) == 5
    failed = list(result.failed_documents())
    assert failed and failed[0].location == "b.pdf"


@pytest.mark.unit
def test_chunk_record_metadata_round_trip() -> None:
    """Chunk record metadata stores structural hints."""
    metadata = ChunkMetadata(
        page_number=1,
        chunk_index=0,
        section_heading="Intro",
        structural_type="paragraph",
    )
    chunk_record = ChunkRecord(
        source_location="docs/a.pdf",
        chunk_index=metadata.chunk_index,
        text="Hello world",
        embedding=(0.1, 0.2, 0.3),
        metadata={"section": metadata.section_heading},
        embedding_model="Qwen/Qwen3-Embedding-0.6B",
    )
    assert chunk_record.metadata["section"] == "Intro"


@pytest.mark.unit
def test_document_metadata_dataclass() -> None:
    """DocumentMetadata dataclass carries file information."""
    metadata = DocumentMetadata(
        location=Path("docs/a.pdf").resolve(),
        document_type="pdf",
        source_type=SourceType.LOCAL_FILE,
        content_hash="abc123",
        size_bytes=123,
    )
    assert metadata.location.name == "a.pdf"


@pytest.mark.unit
def test_document_metadata_immutable() -> None:
    """DocumentMetadata instances should be frozen."""
    metadata = DocumentMetadata(
        location=Path("docs/a.pdf").resolve(),
        document_type="pdf",
        source_type=SourceType.LOCAL_FILE,
        content_hash="abc123",
        size_bytes=123,
    )
    with pytest.raises(FrozenInstanceError):
        metadata.content_hash = "def456"  # type: ignore[attr-defined]


@pytest.mark.unit
def test_document_metadata_equality() -> None:
    """Two metadata instances with equal fields compare equal."""
    base_args = {
        "location": Path("docs/a.pdf").resolve(),
        "document_type": "pdf",
        "source_type": SourceType.LOCAL_FILE,
        "content_hash": "abc123",
        "size_bytes": 123,
    }
    assert DocumentMetadata(**base_args) == DocumentMetadata(**base_args)


@pytest.mark.unit
def test_ingestion_result_subsecond_duration() -> None:
    """duration_seconds should remain positive for sub-second runs."""
    started = dt.datetime.now(tz=dt.timezone.utc)
    completed = started + dt.timedelta(microseconds=250)
    result = IngestionResult(
        started_at=started,
        completed_at=completed,
        pipeline_id="demo",
        documents=[],
        stats=IngestionStatistics(
            documents_discovered=0,
            documents_ingested=0,
            documents_failed=0,
            chunks_created=0,
        ),
    )
    assert result.duration_seconds > 0


@pytest.mark.unit
def test_document_ingestion_result_optional_fields() -> None:
    """DocumentIngestionResult should support optional error/duration."""
    result = DocumentIngestionResult(
        location="docs/a.pdf",
        status=SourceIngestionStatus.FAILED,
        chunks_ingested=0,
        error="missing file",
        duration_ms=0.0,
    )
    assert result.error == "missing file"
    assert result.duration_ms == 0.0
