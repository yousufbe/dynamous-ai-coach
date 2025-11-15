"""Integration helpers for Docling HybridChunker."""

from __future__ import annotations

from collections.abc import Mapping, Sequence as ABCSequence
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from src.rag_pipeline.schemas import ChunkData, ChunkMetadata, DocumentInput, JSONValue
from src.shared.logging import LoggerProtocol, get_logger

logger: LoggerProtocol = get_logger(__name__)


class ChunkingError(RuntimeError):
    """Raised when Docling fails to convert or chunk a document."""


@dataclass
class DoclingChunker:
    """Chunking facade that prefers Docling but falls back to plain text."""

    chunk_min_chars: int
    chunk_max_chars: int
    docling_target_tokens: int = 280
    tokenizer_id: str = "sentence-transformers/all-MiniLM-L6-v2"

    def __post_init__(self) -> None:
        if self.chunk_min_chars <= 0 or self.chunk_max_chars <= 0:
            raise ValueError("Chunk character bounds must be positive.")
        if self.chunk_min_chars >= self.chunk_max_chars:
            raise ValueError("chunk_min_chars must be less than chunk_max_chars.")
        self._docling_backend: _DoclingBackend | None = _DoclingBackend.try_create(
            target_tokens=self.docling_target_tokens,
            tokenizer_id=self.tokenizer_id,
        )

    def chunk_document(self, document: DocumentInput) -> list[ChunkData]:
        """Convert and chunk the given document."""
        chunks: list[ChunkData]
        if self._docling_backend is not None:
            try:
                chunks = self._docling_backend.chunk(document=document)
            except ChunkingError as exc:
                logger.warning(
                    "docling_chunking_failed",
                    file=str(document.metadata.location),
                    error=str(exc),
                )
                self._docling_backend = None
                chunks = self._fallback_chunks(document=document)
        else:
            chunks = self._fallback_chunks(document=document)
        return enforce_character_bounds(
            chunks=chunks,
            min_chars=self.chunk_min_chars,
            max_chars=self.chunk_max_chars,
        )
    
    def uses_docling(self) -> bool:
        """Return True when the Docling backend is active."""
        return self._docling_backend is not None

    def _fallback_chunks(self, document: DocumentInput) -> list[ChunkData]:
        """Simple paragraph splitter used when Docling is unavailable."""
        path: Path = document.metadata.location
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            raise ChunkingError(f"Failed to read {path}: {exc}") from exc
        paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
        if not paragraphs and text.strip():
            paragraphs = [text.strip()]
        result: list[ChunkData] = []
        for index, paragraph in enumerate(paragraphs):
            metadata = ChunkMetadata(
                page_number=None,
                chunk_index=index,
                section_heading=None,
                structural_type="paragraph",
            )
            result.append(
                ChunkData(
                    text=paragraph,
                    metadata=metadata,
                    character_count=len(paragraph),
                    token_estimate=_estimate_tokens(paragraph),
                ),
            )
        return result


class _DoclingBackend:
    """Lazily loads Docling + HybridChunker if the dependency is installed."""

    def __init__(self, target_tokens: int, tokenizer_id: str) -> None:
        from docling.chunking import HybridChunker
        from docling.document_converter import DocumentConverter
        from transformers import AutoTokenizer

        self._converter = DocumentConverter()
        self._hybrid_chunker_cls = HybridChunker
        self._tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)
        self._tokenizer.model_max_length = target_tokens
        self._target_tokens = target_tokens

    @classmethod
    def try_create(cls, target_tokens: int, tokenizer_id: str) -> "_DoclingBackend | None":
        try:
            backend = cls(target_tokens=target_tokens, tokenizer_id=tokenizer_id)
            logger.info("docling_backend_initialized", tokenizer_id=tokenizer_id)
            return backend
        except Exception as exc:  # pragma: no cover - depends on optional dependency
            logger.warning(
                "docling_backend_unavailable",
                error=str(exc),
                tokenizer_id=tokenizer_id,
            )
            return None

    def chunk(self, document: DocumentInput) -> list[ChunkData]:
        try:
            result = self._converter.convert(str(document.metadata.location))
            hybrid_chunker = self._hybrid_chunker_cls(
                tokenizer=self._tokenizer,
                merge_peers=True,
            )
            chunks: list[ChunkData] = []
            for index, chunk in enumerate(hybrid_chunker.chunk(dl_doc=result.document)):
                text = getattr(chunk, "text", "").strip()
                if not text:
                    continue
                meta = getattr(chunk, "meta", {}) or {}
                metadata = ChunkMetadata(
                    page_number=_safe_int(meta.get("page_number")),
                    chunk_index=index,
                    section_heading=_safe_str(meta.get("section_heading")),
                    structural_type=_safe_str(meta.get("block_type")),
                    extra=_coerce_dict(meta),
                )
                chunks.append(
                    ChunkData(
                        text=text,
                        metadata=metadata,
                        character_count=len(text),
                        token_estimate=_estimate_tokens(text),
                    ),
                )
            return chunks
        except Exception as exc:  # pragma: no cover - optional dependency
            raise ChunkingError(f"Docling chunking failed: {exc}") from exc


def enforce_character_bounds(
    chunks: Sequence[ChunkData],
    min_chars: int,
    max_chars: int,
) -> list[ChunkData]:
    """Merge and split chunks so every entry respects configured bounds."""
    if min_chars <= 0 or max_chars <= 0:
        raise ValueError("Chunk bounds must be positive.")
    if min_chars >= max_chars:
        raise ValueError("min_chars must be smaller than max_chars.")
    normalized: list[tuple[str, ChunkMetadata]] = []
    buffer_text: str = ""
    buffer_metadata: ChunkMetadata | None = None

    def flush_buffer(force: bool = False) -> None:
        nonlocal buffer_text, buffer_metadata
        if not buffer_text:
            return
        if len(buffer_text) < min_chars and not force:
            return
        metadata = buffer_metadata or ChunkMetadata(
            page_number=None,
            chunk_index=0,
            section_heading=None,
            structural_type=None,
        )
        normalized.append((buffer_text, metadata))
        buffer_text = ""
        buffer_metadata = None

    for chunk in chunks:
        for segment in _split_text(chunk.text.strip(), max_chars=max_chars):
            if not segment:
                continue
            if not buffer_text:
                buffer_text = segment
                buffer_metadata = chunk.metadata
            else:
                candidate = f"{buffer_text}\n\n{segment}"
                if len(candidate) <= max_chars:
                    buffer_text = candidate
                else:
                    flush_buffer(force=True)
                    buffer_text = segment
                    buffer_metadata = chunk.metadata
            if len(buffer_text) >= min_chars:
                flush_buffer()
    flush_buffer(force=True)

    result: list[ChunkData] = []
    for new_index, (text, metadata) in enumerate(normalized):
        result.append(
            ChunkData(
                text=text,
                metadata=ChunkMetadata(
                    page_number=metadata.page_number,
                    chunk_index=new_index,
                    section_heading=metadata.section_heading,
                    structural_type=metadata.structural_type,
                    extra=dict(metadata.extra),
                ),
                character_count=len(text),
                token_estimate=_estimate_tokens(text),
            ),
        )
    return result


def _split_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    segments: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(length, start + max_chars)
        split_at = end
        if end < length:
            newline = text.rfind("\n", start, end)
            space = text.rfind(" ", start, end)
            candidate = max(newline, space)
            if candidate > start + int(max_chars * 0.5):
                split_at = candidate
        segment = text[start:split_at].strip()
        if segment:
            segments.append(segment)
        start = split_at
    return segments


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _safe_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _coerce_dict(value: object) -> dict[str, JSONValue]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): _normalize_json_value(val) for key, val in value.items()}


def _normalize_json_value(value: object) -> JSONValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, ABCSequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_json_value(item) for item in value]
    return str(value)
