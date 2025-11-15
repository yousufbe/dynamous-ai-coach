import pytest

from src.rag_pipeline.chunking.docling_chunker import DoclingChunker, enforce_character_bounds
from src.rag_pipeline.schemas import ChunkData, ChunkMetadata, DocumentInput, DocumentMetadata, SourceType


def _chunk(text: str, index: int) -> ChunkData:
    return ChunkData(
        text=text,
        metadata=ChunkMetadata(
            page_number=None,
            chunk_index=index,
            section_heading=None,
            structural_type="paragraph",
        ),
        character_count=len(text),
    )


@pytest.mark.unit
def test_enforce_character_bounds_merges_and_splits() -> None:
    """Chunks shorter than the minimum should merge and larger ones should split."""
    chunks = [
        _chunk("short text", 0),
        _chunk("another short text", 1),
        _chunk("x" * 1200, 2),
    ]
    normalized = enforce_character_bounds(chunks=chunks, min_chars=30, max_chars=200)
    assert normalized[0].character_count >= 30  # merged chunk
    assert all(chunk.character_count <= 200 for chunk in normalized)


@pytest.mark.unit
def test_chunk_document_fallback_reads_plain_text(tmp_path) -> None:
    """DoclingChunker should fall back to plain-text chunking when Docling is unavailable."""
    sample = tmp_path / "sample.txt"
    sample.write_text("Paragraph one.\n\nParagraph two with more text.", encoding="utf-8")
    chunker = DoclingChunker(chunk_min_chars=10, chunk_max_chars=200)
    document = DocumentInput(
        metadata=DocumentMetadata(
            location=sample,
            document_type="txt",
            source_type=SourceType.LOCAL_FILE,
            content_hash="abc",
            size_bytes=sample.stat().st_size,
        ),
        display_name=sample.name,
    )
    chunks = chunker.chunk_document(document)
    assert chunks
    assert all(chunk.text for chunk in chunks)
    assert chunker.uses_docling() is False
