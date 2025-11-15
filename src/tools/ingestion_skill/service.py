"""Service layer that wires the ingestion skill to the pipeline."""

from __future__ import annotations

from datetime import datetime

from src.rag_pipeline.config import RagIngestionConfig, get_rag_ingestion_config
from src.rag_pipeline.pipeline import IngestionRequest, IngestionResult, IngestionStatistics, run_ingestion_job
from src.rag_pipeline.runtime import cleanup_runtime, create_pipeline_runtime
from src.shared.logging import LoggerProtocol, get_logger
from src.tools.ingestion_skill.schemas import IngestionSkillRequest, IngestionSkillResponse

logger: LoggerProtocol = get_logger(__name__)


def run_ingestion_skill(
    request: IngestionSkillRequest,
    *,
    config: RagIngestionConfig | None = None,
) -> IngestionSkillResponse:
    """Run the ingestion pipeline using the provided request configuration."""
    cfg = config or get_rag_ingestion_config()
    logger.info(
        "ingestion_skill_invoked",
        directories=request.source_directories,
        glob_patterns=request.glob_patterns,
        force_reingest=request.force_reingest,
        response_format=request.response_format,
    )
    services, embedding_client, db_client = create_pipeline_runtime(cfg)
    warnings: list[str] = []
    try:
        ingestion_request = IngestionRequest(
            source_directories=request.source_directories,
            document_glob_patterns=request.glob_patterns,
            force_reingest=request.force_reingest,
            pipeline_id=request.pipeline_id,
        )
        result = run_ingestion_job(
            request=ingestion_request,
            config=cfg,
            services=services,
            max_failures=request.max_failures,
        )
        summary = _format_summary(
            pipeline_id=result.pipeline_id,
            stats=result.stats,
            response_format=request.response_format,
        )
        response = IngestionSkillResponse(
            summary_text=summary,
            ingested_count=result.stats.documents_ingested,
            failed_count=result.stats.documents_failed,
            duration_seconds=result.duration_seconds,
            warnings=warnings,
            result=result,
        )
        logger.info(
            "ingestion_skill_completed",
            pipeline_id=result.pipeline_id,
            documents_ingested=result.stats.documents_ingested,
            documents_failed=result.stats.documents_failed,
        )
        return response
    except FileNotFoundError as exc:
        warnings.append(str(exc))
        logger.warning("ingestion_skill_directory_missing", error=str(exc))
        empty_result = _empty_result(cfg, services.clock())
        summary = f"Ingestion aborted: {exc}"
        return IngestionSkillResponse(
            summary_text=summary,
            ingested_count=0,
            failed_count=0,
            duration_seconds=empty_result.duration_seconds,
            warnings=warnings,
            result=empty_result,
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Ingestion failed: {exc}")
        logger.exception("ingestion_skill_failed", error=str(exc))
        empty_result = _empty_result(cfg, services.clock())
        return IngestionSkillResponse(
            summary_text=f"Ingestion failed: {exc}",
            ingested_count=0,
            failed_count=0,
            duration_seconds=empty_result.duration_seconds,
            warnings=warnings,
            result=empty_result,
        )
    finally:
        cleanup_runtime(embedding_client, db_client)


def _format_summary(
    *,
    pipeline_id: str,
    stats: IngestionStatistics,
    response_format: str,
) -> str:
    base = (
        f"Pipeline {pipeline_id} processed {stats.documents_discovered} documents; "
        f"{stats.documents_ingested} ingested, {stats.documents_failed} failed."
    )
    if response_format == "detailed":
        return (
            f"{base} Total chunks created: {stats.chunks_created}. "
            "Use 'output_format=json' for the full result payload."
        )
    return base


def _empty_result(config: RagIngestionConfig, now: datetime) -> IngestionResult:
    return IngestionResult(
        started_at=now,
        completed_at=now,
        pipeline_id=config.pipeline_id,
        documents=[],
        stats=IngestionStatistics(
            documents_discovered=0,
            documents_ingested=0,
            documents_failed=0,
            chunks_created=0,
        ),
    )
