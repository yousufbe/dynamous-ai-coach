"""Ingestion orchestration for Docling-based pipelines."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Callable, Sequence

from src.rag_pipeline.chunking.docling_chunker import DoclingChunker
from src.rag_pipeline.config import RagIngestionConfig, get_rag_ingestion_config
from src.rag_pipeline.embeddings import EmbeddingClientProtocol
from src.rag_pipeline.persistence import PersistenceStoreProtocol, SourceRow
from src.rag_pipeline.schemas import (
    ChunkData,
    ChunkRecord,
    DocumentIngestionResult,
    DocumentInput,
    EmbeddingRecord,
    IngestionRequest,
    IngestionResult,
    IngestionStatistics,
    SourceIngestionStatus,
)
from src.rag_pipeline.sources.local_files import discover_documents
from src.shared.logging import LoggerProtocol, get_logger

logger: LoggerProtocol = get_logger(__name__)

ClockFunc = Callable[[], datetime]


def _default_clock() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class PipelineServices:
    """Aggregated dependencies needed by the ingestion pipeline."""

    chunker: DoclingChunker
    embedding_client: EmbeddingClientProtocol
    persistence: PersistenceStoreProtocol
    clock: ClockFunc = _default_clock
    logger: LoggerProtocol = field(default_factory=lambda: get_logger(__name__))


def ingest_single_document(
    document: DocumentInput,
    config: RagIngestionConfig,
    services: PipelineServices,
) -> DocumentIngestionResult:
    """Ingest a single document and return a status summary."""
    doc_logger = services.logger
    location = str(document.metadata.location)
    embedding_info = services.embedding_client.model_info
    doc_logger.info(
        "document_ingestion_started",
        file=location,
        pipeline_id=config.pipeline_id,
        embedding_model=embedding_info.model,
        embedding_dataset_fingerprint=embedding_info.dataset_fingerprint,
    )
    start_perf = perf_counter()
    chunk_duration_ms = 0.0
    embedding_duration_ms = 0.0
    db_duration_ms = 0.0
    chunk_count = 0
    final_status: SourceIngestionStatus = SourceIngestionStatus.FAILED
    error_message: str | None = None
    with ExitStack() as stack:
        def finalize_failure() -> None:
            if final_status == SourceIngestionStatus.FAILED and error_message:
                services.persistence.mark_source_failed(location, error_message)

        stack.callback(finalize_failure)
        source_row = services.persistence.upsert_source(
            document=document,
            status=SourceIngestionStatus.PENDING,
            embedding_model=embedding_info.model,
        )
        try:
            chunk_start = perf_counter()
            chunks = services.chunker.chunk_document(document)
            chunk_duration_ms = (perf_counter() - chunk_start) * 1000.0
            if not chunks:
                error_message = "Document produced no chunks."
                raise RuntimeError(error_message)
            embedding_start = perf_counter()
            embeddings = services.embedding_client.embed_document_chunks(chunks)
            embedding_duration_ms = (perf_counter() - embedding_start) * 1000.0
            chunk_records = _build_chunk_records(document=document, chunks=chunks, embeddings=embeddings)
            chunk_count = len(chunk_records)
            db_start = perf_counter()
            services.persistence.replace_chunks_for_source(
                source_id=source_row.id,
                chunk_records=chunk_records,
            )
            db_duration_ms = (perf_counter() - db_start) * 1000.0
            services.persistence.mark_source_status(
                location=location,
                status=SourceIngestionStatus.INGESTED,
                error_message=None,
            )
            final_status = SourceIngestionStatus.INGESTED
            total_duration_ms = (perf_counter() - start_perf) * 1000.0
            doc_logger.info(
                "document_ingestion_completed",
                file=location,
                pipeline_id=config.pipeline_id,
                chunk_duration_ms=chunk_duration_ms,
                embedding_duration_ms=embedding_duration_ms,
                db_duration_ms=db_duration_ms,
                chunks_ingested=chunk_count,
                status=final_status.value,
                embedding_model=embedding_info.model,
                embedding_dataset_fingerprint=embedding_info.dataset_fingerprint,
            )
            return DocumentIngestionResult(
                location=location,
                status=final_status,
                chunks_ingested=chunk_count,
                error=None,
                duration_ms=total_duration_ms,
            )
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            doc_logger.exception(
                "document_ingestion_failed",
                file=location,
                pipeline_id=config.pipeline_id,
                error=error_message,
            )
            final_status = (
                SourceIngestionStatus.PARTIAL
                if chunk_count > 0
                else SourceIngestionStatus.FAILED
            )
            if final_status == SourceIngestionStatus.PARTIAL:
                services.persistence.mark_source_status(
                    location=location,
                    status=final_status,
                    error_message=error_message,
                )
            total_duration_ms = (perf_counter() - start_perf) * 1000.0
            return DocumentIngestionResult(
                location=location,
                status=final_status,
                chunks_ingested=chunk_count,
                error=error_message,
                duration_ms=total_duration_ms,
            )


def run_ingestion_job(
    request: IngestionRequest | None = None,
    *,
    config: RagIngestionConfig | None = None,
    services: PipelineServices,
    max_failures: int | None = None,
) -> IngestionResult:
    """Run a full ingestion job across configured directories."""
    active_request = request or IngestionRequest()
    base_config = config or get_rag_ingestion_config()
    merged_config = _merge_request_overrides(config=base_config, request=active_request)
    merged_config.require_sources()
    job_logger = services.logger
    job_logger.info(
        "ingestion_job_started",
        pipeline_id=merged_config.pipeline_id,
        directories=[str(path) for path in merged_config.source_directories],
        force_reingest=merged_config.force_reingest,
    )
    started_at = services.clock()
    documents: list[DocumentIngestionResult] = []
    stats = IngestionStatistics(
        documents_discovered=0,
        documents_ingested=0,
        documents_failed=0,
        chunks_created=0,
    )
    discovered_docs = _discover_unique_documents(
        config=merged_config,
        glob_patterns=active_request.document_glob_patterns,
    )
    stats.documents_discovered = len(discovered_docs)
    failure_count = 0
    for document in discovered_docs:
        location = str(document.metadata.location)
        existing: SourceRow | None = services.persistence.get_source_by_location(location)
        should_skip = (
            not merged_config.force_reingest
            and existing is not None
            and not services.persistence.has_content_changed(document=document, existing=existing)
        )
        if should_skip:
            job_logger.info(
                "document_skipped",
                file=location,
                pipeline_id=merged_config.pipeline_id,
            )
            documents.append(
                DocumentIngestionResult(
                    location=location,
                    status=SourceIngestionStatus.INGESTED,
                    chunks_ingested=0,
                    error="Skipped (content hash unchanged).",
                    duration_ms=0.0,
                ),
            )
            continue
        result = ingest_single_document(
            document=document,
            config=merged_config,
            services=services,
        )
        documents.append(result)
        if result.status == SourceIngestionStatus.INGESTED:
            stats.documents_ingested += 1
        else:
            stats.documents_failed += 1
            failure_count += 1
            if max_failures is not None and failure_count >= max_failures:
                job_logger.warning(
                    "ingestion_job_aborted_due_to_failures",
                    pipeline_id=merged_config.pipeline_id,
                    failure_count=failure_count,
                    max_failures=max_failures,
                )
                break
        stats.chunks_created += result.chunks_ingested
    completed_at = services.clock()
    result_summary = IngestionResult(
        started_at=started_at,
        completed_at=completed_at,
        pipeline_id=merged_config.pipeline_id,
        documents=documents,
        stats=stats,
    )
    job_logger.info(
        "ingestion_job_completed",
        pipeline_id=merged_config.pipeline_id,
        duration_seconds=result_summary.duration_seconds,
        documents_ingested=stats.documents_ingested,
        documents_failed=stats.documents_failed,
    )
    return result_summary


def _merge_request_overrides(
    config: RagIngestionConfig,
    request: IngestionRequest,
) -> RagIngestionConfig:
    updated_config = config
    if request.source_directories:
        source_dirs = [Path(entry).expanduser().resolve() for entry in request.source_directories]
        updated_config = replace(updated_config, source_directories=source_dirs)
    if request.pipeline_id:
        updated_config = replace(updated_config, pipeline_id=request.pipeline_id)
    if request.force_reingest or config.force_reingest:
        updated_config = replace(updated_config, force_reingest=True)
    return updated_config


def _discover_unique_documents(
    *,
    config: RagIngestionConfig,
    glob_patterns: Sequence[str],
) -> list[DocumentInput]:
    seen: dict[str, DocumentInput] = {}
    for document in discover_documents(config=config, glob_patterns=glob_patterns):
        key = str(document.metadata.location)
        if key not in seen:
            seen[key] = document
    return list(seen.values())


def _build_chunk_records(
    *,
    document: DocumentInput,
    chunks: Sequence[ChunkData],
    embeddings: Sequence[EmbeddingRecord],
) -> list[ChunkRecord]:
    if len(chunks) != len(embeddings):
        raise ValueError("Chunk and embedding counts do not match.")
    records: list[ChunkRecord] = []
    for chunk, embedding in zip(chunks, embeddings):
        metadata = dict(chunk.metadata.extra)
        metadata.update(
            {
                "page_number": chunk.metadata.page_number,
                "section_heading": chunk.metadata.section_heading,
                "structural_type": chunk.metadata.structural_type,
            },
        )
        records.append(
            ChunkRecord(
                source_location=str(document.metadata.location),
                chunk_index=chunk.metadata.chunk_index,
                text=chunk.text,
                embedding=tuple(float(value) for value in embedding.vector),
                metadata=metadata,
                embedding_model=embedding.model,
            ),
        )
    return records
