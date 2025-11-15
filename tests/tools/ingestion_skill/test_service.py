import datetime as dt
from unittest import mock

import pytest

from src.rag_pipeline.pipeline import IngestionResult, IngestionStatistics
from src.tools.ingestion_skill.schemas import IngestionSkillRequest
from src.tools.ingestion_skill.service import run_ingestion_skill


def _ingestion_result() -> IngestionResult:
    now = dt.datetime.now(tz=dt.timezone.utc)
    return IngestionResult(
        started_at=now,
        completed_at=now,
        pipeline_id="demo",
        documents=[],
        stats=IngestionStatistics(
            documents_discovered=1,
            documents_ingested=1,
            documents_failed=0,
            chunks_created=2,
        ),
    )


@pytest.mark.unit
def test_run_ingestion_skill_returns_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service should return a structured response using pipeline results."""
    services = mock.Mock()
    services.clock.return_value = dt.datetime.now(tz=dt.timezone.utc)
    embedding_client = mock.Mock()
    db_client = mock.Mock()
    monkeypatch.setattr(
        "src.tools.ingestion_skill.service.create_pipeline_runtime",
        lambda cfg: (services, embedding_client, db_client),
    )
    monkeypatch.setattr(
        "src.tools.ingestion_skill.service.cleanup_runtime",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.tools.ingestion_skill.service.run_ingestion_job",
        lambda **kwargs: _ingestion_result(),
    )
    response = run_ingestion_skill(IngestionSkillRequest())
    assert response.ingested_count == 1
    assert "processed" in response.summary_text


@pytest.mark.unit
def test_run_ingestion_skill_handles_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service should surface warnings when pipeline execution fails."""
    services = mock.Mock()
    services.clock.return_value = dt.datetime.now(tz=dt.timezone.utc)
    embedding_client = mock.Mock()
    db_client = mock.Mock()
    monkeypatch.setattr(
        "src.tools.ingestion_skill.service.create_pipeline_runtime",
        lambda cfg: (services, embedding_client, db_client),
    )
    monkeypatch.setattr(
        "src.tools.ingestion_skill.service.cleanup_runtime",
        lambda *args, **kwargs: None,
    )

    def _raise(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "src.tools.ingestion_skill.service.run_ingestion_job",
        _raise,
    )
    response = run_ingestion_skill(IngestionSkillRequest())
    assert response.ingested_count == 0
    assert response.warnings
    assert "failed" in response.summary_text.lower()
