"""Schemas shared by the ingestion skill."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.rag_pipeline.schemas import IngestionResult


class IngestionSkillRequest(BaseModel):
    """Request payload accepted by the ingestion skill."""

    source_directories: list[str] = Field(
        default_factory=list,
        description="Optional override for configured ingestion directories.",
    )
    glob_patterns: list[str] = Field(
        default_factory=lambda: ["**/*"],
        description="Glob patterns applied to each directory.",
    )
    force_reingest: bool = Field(
        default=False,
        description="Reprocess documents even if the content hash matches the database.",
    )
    pipeline_id: str | None = Field(
        default=None,
        description="Override the pipeline identifier so logs and metrics can be grouped.",
    )
    max_failures: int | None = Field(
        default=None,
        description="Optional limit after which the ingestion run aborts early.",
    )
    response_format: Literal["concise", "detailed"] = Field(
        default="concise",
        description="Controls the verbosity of the textual summary returned to the caller.",
    )


class IngestionSkillResponse(BaseModel):
    """Response model returned by the ingestion skill."""

    summary_text: str = Field(
        ...,
        description="Human-readable summary that the agent can quote back to the user.",
    )
    ingested_count: int = Field(
        ...,
        ge=0,
        description="Number of documents successfully ingested.",
    )
    failed_count: int = Field(
        ...,
        ge=0,
        description="Number of documents that failed or were partially ingested.",
    )
    duration_seconds: float = Field(
        ...,
        ge=0.0,
        description="Duration of the ingestion run in seconds.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Additional information surfaced to the agent (e.g., missing directories).",
    )
    result: IngestionResult = Field(
        ...,
        description="Raw ingestion result for structured inspection or downstream tooling.",
    )

    def summary(self) -> str:
        """Return the summary text."""
        return self.summary_text
