from unittest import mock

import pytest

from src.rag_pipeline.config import get_rag_ingestion_config
from src.rag_pipeline.persistence.supabase_store import SourceRow, SupabaseStore
from src.rag_pipeline.schemas import (
    ChunkRecord,
    DocumentInput,
    DocumentMetadata,
    SourceIngestionStatus,
    SourceType,
)


def _mock_db() -> mock.Mock:
    db = mock.Mock()
    transaction = mock.MagicMock()
    transaction.__enter__.return_value = None
    transaction.__exit__.return_value = False
    db.transaction.return_value = transaction
    return db


def _document_input(tmp_path) -> DocumentInput:
    doc = tmp_path / "doc.pdf"
    doc.write_text("content", encoding="utf-8")
    metadata = DocumentMetadata(
        location=doc.resolve(),
        document_type="pdf",
        source_type=SourceType.LOCAL_FILE,
        content_hash="abc123",
        size_bytes=doc.stat().st_size,
    )
    return DocumentInput(metadata=metadata, display_name=doc.name)


@pytest.mark.unit
def test_upsert_source_returns_source_row(tmp_path) -> None:
    """Upserting a source should return the persisted SourceRow."""
    db = _mock_db()
    db.fetchrow.return_value = {
        "id": "source-id",
        "location": "doc.pdf",
        "document_name": "doc.pdf",
        "content_hash": "abc123",
        "status": "ingested",
        "metadata": {},
        "error_message": None,
    }
    store = SupabaseStore(db=db, config=get_rag_ingestion_config())
    result = store.upsert_source(
        document=_document_input(tmp_path),
        status=SourceIngestionStatus.INGESTED,
        embedding_model="demo",
    )
    assert isinstance(result, SourceRow)
    assert db.fetchrow.called


@pytest.mark.unit
def test_replace_chunks_for_source_deletes_then_inserts() -> None:
    """Chunk replacement should delete previous rows before inserting new ones."""
    db = _mock_db()
    store = SupabaseStore(db=db, config=get_rag_ingestion_config())
    chunk = ChunkRecord(
        source_location="doc.pdf",
        chunk_index=0,
        text="hello",
        embedding=(0.1, 0.2),
        metadata={"page_number": 1},
        embedding_model="demo",
    )
    store.replace_chunks_for_source(source_id="source-id", chunk_records=[chunk])
    delete_sql = db.execute.call_args[0][0]
    assert "delete from" in delete_sql.lower()
    assert db.executemany.called


@pytest.mark.unit
def test_mark_source_failed_updates_status(tmp_path) -> None:
    """mark_source_failed should delegate to mark_source_status."""
    db = _mock_db()
    db.fetchrow.return_value = {
        "id": "source-id",
        "location": "doc.pdf",
        "document_name": "doc.pdf",
        "content_hash": "abc123",
        "status": "failed",
        "metadata": {},
        "error_message": "boom",
    }
    store = SupabaseStore(db=db, config=get_rag_ingestion_config())
    result = store.mark_source_failed("doc.pdf", "boom")
    assert result is not None
    assert db.fetchrow.called
