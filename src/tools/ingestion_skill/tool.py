"""Agent-facing tool entrypoint for the ingestion pipeline."""

from __future__ import annotations

import asyncio

from src.tools.ingestion_skill.schemas import IngestionSkillRequest, IngestionSkillResponse
from src.tools.ingestion_skill.service import run_ingestion_skill


async def ingestion_skill_tool(request: IngestionSkillRequest) -> IngestionSkillResponse:
    """Reindex document collections with the Docling-based ingestion pipeline.

    Use this when you need to:
    - Refresh hybrid search/vector stores after updating on-disk documentation
    - Force re-ingestion of targeted directories before answering sensitive questions
    - Validate ingestion in lower environments before promoting a pipeline change
    - Capture structured ingestion metrics (counts, failures, duration) for runbooks

    Do NOT use this for:
    - Answering user questions or retrieving documents (call retrieval/chat tools instead)
    - Uploading remote content (pipeline only reads local directories configured on the host)
    - Lightweight status checks (use agent logging APIs if you only need current state)

    Args:
        request: Structured ingestion request driving the pipeline. Key fields:
            - ``source_directories``: Optional overrides for configured folders.
              Provide explicit paths when you only want to reprocess a subset;
              leave empty to use the default config.
            - ``glob_patterns``: Filters inside each directory. Use tighter globs
              (e.g., ``['**/*.pdf']``) to reduce runtime when previewing changes.
            - ``force_reingest``: Set to True when hashes have not changed but you
              must rebuild embeddings (e.g., new embedding model, schema change).
            - ``pipeline_id``: Override to tag logs/metrics for ad-hoc runs such as
              ``"staging-smoke-test"``.
            - ``max_failures``: Abort after N failures to keep long-running jobs
              from burning time; omit to process entire corpus regardless of errors.
            - ``response_format``: Controls the textual summary returned to the agent.
              ``"concise"`` (~200 tokens) is best for status updates, while
              ``"detailed"`` (~800-1200 tokens) includes per-directory statistics.

    Returns:
        IngestionSkillResponse with a natural-language summary plus the structured
        ``IngestionResult``. The response exposes counts (ingested vs. failed),
        duration, warnings (e.g., missing directories), and the full result payload
        for downstream agents to inspect programmatically.

    Performance Notes:
        - ``response_format="concise"``: ~200 tokens, completes fastest and is preferred
          for operational confirmations.
        - ``response_format="detailed"``: ~1K tokens, only use when the user explicitly
          requests a blow-by-blow summary.
        - Execution time scales with corpus size: a small docset finishes in seconds,
          while thousands of PDFs may require multiple minutes.
        - Memory usage is dominated by the largest document being converted/chunked.
          Avoid invoking the tool concurrently unless the host has ample RAM.
        - Pipeline stops early when ``max_failures`` is provided; otherwise it collects
          every failure for reporting.

    Examples:
        # Refresh default directories before answering a compliance question
        ingestion_skill_tool(IngestionSkillRequest())

        # Target only finance PDFs with a detailed summary for auditors
        ingestion_skill_tool(
            IngestionSkillRequest(
                source_directories=[\"/data/rag/finance\"],
                glob_patterns=[\"**/*.pdf\"],
                response_format=\"detailed\",
            ),
        )

        # Smoke-test staging pipeline but stop after 2 failures
        ingestion_skill_tool(
            IngestionSkillRequest(
                source_directories=[\"/mnt/staging\"],
                max_failures=2,
                pipeline_id=\"staging-smoke-001\",
                force_reingest=True,
            ),
        )
    """

    return await asyncio.to_thread(run_ingestion_skill, request)
