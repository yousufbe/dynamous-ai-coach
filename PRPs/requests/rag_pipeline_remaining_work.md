# Implementation Plan: Remaining Docling Hybrid RAG Pipeline + Archon Skill

## Overview
The ingestion foundation now exists (configuration, schemas, discovery, Docling chunking, documentation, and base tests), but the pipeline still needs a full execution path from embedding to CLI invocation and the Archon ingestion skill integration. This plan describes how to complete the remaining implementation tasks, validate them, and operationalize the pipeline so it can ingest documents reliably, expose tooling for the agent, and provide regression coverage.

## Requirements Summary
- Implement Qwen3-Embedding-0.6B client with retry, metrics, batching.
- Build Supabase/PostgreSQL persistence helpers for `sources` and `chunks` tables (schema already drafted in `PRPs/examples/rag_pipeline_docling_supabase.sql`).
- Implement ingestion orchestration: single-document ingestion, ingestion job runner, CLI entrypoint.
- Create Archon-style ingestion skill (schemas, service, tool registration) per `docs/archon_SKILL.md` and `PRPs/ai_docs/tool_guide.md`.
- Expand unit and integration test coverage for new modules plus ingestion flow.
- Add validator/integration test automation and finalize documentation/runbooks.
- Maintain Archon project/task updates throughout execution.
- Keep everything type-safe, well logged, with Google-style docstrings.

## Research Findings
### Best Practices
1. **Embedding Resilience**
   - Use exponential backoff (single retry) on remote embedding errors.
   - Validate vector dimensionality per model metadata.
   - Log embedding latency and failure context for observability (per `PRPs/ai_docs/logging_guide.md`).
2. **Supabase/PGVector Persistence**
   - Use batched inserts for chunks to minimize transaction overhead.
   - Store embedding model metadata alongside each chunk for future experiments (Fine-tuned Embeddings Strategy in `AGENTS.md`).
   - Keep `content_hash` to avoid duplicates and enable idempotent ingestion.
   - Use `ON CONFLICT` upserts keyed on `location` (sources) and `(source_id, chunk_index)` (chunks).
   - Manage transactions carefully (commit only when embeddings/chunks succeed).
3. **Orchestrating Pipelines**
   - Separation of concerns: discovery → chunking → embedding → persistence.
   - Provide typed events/logging at stage boundaries for debugging.
   - Use structured results (`IngestionResult`) for CLI + skill reuse.
4. **Skill Design**
   - Follow tool docstring guidelines (`PRPs/ai_docs/tool_guide.md`).
   - Keep skill service thin: validate request, load config, call pipeline, map result.
   - Include metadata such as run IDs, directories acted upon, success/failure counts.
5. **Testing Strategy**
   - `pytest` fixtures for temporary directories and fake DB clients to isolate modules.
   - Use mocks for network-dependent pieces (embedding, Supabase) to keep tests offline-friendly.
   - Integration tests should spin minimal Postgres (or a stub) when possible, but provide skip markers if environment not present.
   - Follow `PRPs/ai_docs/testing_guide.md` for structure.
6. **Documentation/Runbooks**
   - Document CLI usage, env vars, failure handling, “force reingest” semantics, and Archon skill invocation steps in `docs/rag_pipeline_ingestion.md`.

### Reference Implementations
1. **PRPs/examples/rag_agent.py**
   - Illustrates PGVector usage, search functions, and simple CLI invocation.
2. **PRPs/examples/docling_hybrid_chunking.py**
   - Demonstrates Docling conversion + chunking; use as baseline for error handling, metadata capture.
3. **docs/docling.md**
   - Describes ingestion workflow and hints at chunk sizing requirements.
4. **docs/hybrid_search.md**
   - Specifies indexes (vector, tsvector, trigram) and hybrid retrieval rationale.
5. **PRPs/ai_docs/tool_guide.md**
   - Template for tool docstrings and usage guidance.
6. **PRPs/ai_docs/logging_guide.md**
   - Logging standards for pipeline/skill operations.
7. **PRPs/ai_docs/testing_guide.md**
   - Testing structure requirements (mirrors src layout).
8. **docs/archon_SKILL.md**
   - Mandatory workflow for Archon integration.

### Technology Decisions
- **Embedding Model**: Continue Qwen/Qwen3-Embedding-0.6B, but keep configuration-driven for future fine-tuned models.
- **Supabase Client**: Use `asyncpg` or `psycopg` depending on existing stack (prefers async for throughput; plan will design for an injectable interface allowing either). Provide synchronous fallback for CLI usage.
- **Docling Integration**: Already in place with fallback chunker; plan extends to cover optional dependencies gracefully.
- **CLI**: Standard `argparse` CLI executed via `python -m src.rag_pipeline.cli`. Provide JSON output for automation.
- **Skill**: Implement in `src/tools/ingestion_skill` with `schemas.py`, `service.py`, `tool.py` following existing patterns.
- **Testing**: Use `pytest`, `unittest.mock`, and optionally `pytest-asyncio` for async persistence tests.

## Implementation Tasks

### Phase 1: Embeddings & Persistence Foundations
1. **Task 10: Implement Qwen embedding client (sync + retry)**
   - Description: Create `src/rag_pipeline/embeddings/qwen_client.py` with `QwenEmbeddingClient` handling batching, HTTP calls or local inference, logging, and retries.
   - Files: `src/rag_pipeline/embeddings/__init__.py`, `src/rag_pipeline/embeddings/qwen_client.py`, tests under `tests/rag_pipeline/test_embeddings_qwen_client.py`.
   - Dependencies: `RagIngestionConfig`, logging utility.
   - Effort: 4-5h.
2. **Task 11: Supabase persistence layer**
   - Description: Implement `src/rag_pipeline/persistence/supabase_store.py` with typed operations for sources/chunks. Provide DB interface abstraction for easier testing.
   - Files: `src/rag_pipeline/persistence/__init__.py`, `src/rag_pipeline/persistence/supabase_store.py`, tests `tests/rag_pipeline/test_persistence_supabase_store.py`.
   - Dependencies: Database schema file, config module.
   - Effort: 4-6h.
3. **Task 12: Single-document ingestion**
   - Description: Implement `ingest_single_document` orchestrating Docling chunking, embedding, persistence, error handling, logging, and result creation.
   - Files: `src/rag_pipeline/pipeline.py`, tests `tests/rag_pipeline/test_pipeline_single_document.py`.
   - Dependencies: config, chunker, embeddings, persistence.
   - Effort: 5-6h.
4. **Task 13: Ingestion job orchestrator**
   - Description: Implement `run_ingestion_job()` to tie together config loading, document discovery, deduplication vs existing sources, metrics logging, aggregated results.
   - Files: `src/rag_pipeline/pipeline.py`, tests `tests/rag_pipeline/test_pipeline_job.py`.
   - Dependencies: Document discovery adapter, single-document ingestion.
   - Effort: 3-4h.
5. **Task 14: CLI entrypoint**
   - Description: Build `src/rag_pipeline/cli.py` with argparse, `IngestionRequest` parsing, config overrides, structured stdout summary, proper exit codes.
   - Files: `src/rag_pipeline/cli.py`, tests `tests/rag_pipeline/test_cli.py`.
   - Dependencies: Pipeline orchestrator.
   - Effort: 2-3h.

### Phase 2: Archon Ingestion Skill
6. **Task 15: Skill schemas**
   - Description: Map `IngestionRequest`/`IngestionResult` into tool-friendly `IngestionSkillRequest` and `IngestionSkillResponse` Pydantic models. Include metadata fields (requested directories, forced reingest flag).
   - Files: `src/tools/ingestion_skill/schemas.py`, tests `tests/tools/ingestion_skill/test_schemas.py`.
   - Dependencies: `src/rag_pipeline/schemas.py`.
   - Effort: 1-2h.
7. **Task 16: Skill service**
   - Description: Implement `run_ingestion` service function calling pipeline and handling logging/errors.
   - Files: `src/tools/ingestion_skill/service.py`, tests `tests/tools/ingestion_skill/test_service.py`.
   - Dependencies: pipeline, config loader.
   - Effort: 2-3h.
8. **Task 17: Tool registration**
   - Description: Add `tool.py` with `@agent.tool` metadata + docstring per guide, integrate into agent’s tool registry.
   - Files: `src/tools/ingestion_skill/tool.py`, updates to agent registry (likely `src/agent/agent.py` or central tool loader).
   - Dependencies: service + schemas.
   - Effort: 2h.

### Phase 3: Testing & Validation
9. **Task 18: Config/schema unit tests (expand)**
   - Description: Extend tests to cover new config edge cases (invalid env values, directories missing) and schema behaviours (IngestionResult failure listing, etc.).
   - Files: `tests/rag_pipeline/test_config.py`, `tests/rag_pipeline/test_schemas.py`.
   - Effort: 1-2h.
10. **Task 19: Local file discovery tests**
    - Description: Add tests verifying hash computation, extension filtering, missing directories logging behaviour.
    - Files: `tests/rag_pipeline/test_sources_local_files.py`.
    - Dependencies: `pytest` tmp_path fixtures.
    - Effort: 2-3h.
11. **Task 20: Docling chunking tests**
    - Description: Tests for `DoclingChunker` fallback path and `enforce_character_bounds` splitting/merging logic (Docling optional dependency path should be stubbed).
    - Files: `tests/rag_pipeline/test_chunking_docling.py`.
    - Effort: 3-4h.
12. **Task 21: Embedding client tests**
    - Description: Use mocks/fakes to simulate network errors, timeouts, and ensure retry/backoff works.
    - Files: `tests/rag_pipeline/test_embeddings_qwen_client.py`.
    - Effort: 3h.
13. **Task 22: Persistence layer tests**
    - Description: Mock DB connection to verify SQL generation, transaction usage, error handling, upserts.
    - Files: `tests/rag_pipeline/test_persistence_supabase_store.py`.
    - Effort: 4h.
14. **Task 23: Integration tests**
    - Description: Optionally spin up Postgres via Docker (skippable if not available). Cover discovery → chunking → embedding (mock) → persistence cycle.
    - Files: `tests/rag_pipeline/test_pipeline_integration.py` (with markers for `integration`).
    - Effort: 5-6h.
15. **Task 24: Skill unit tests**
    - Description: Ensure service returns expected `IngestionSkillResponse`, logs events, handles pipeline errors gracefully.
    - Files: `tests/tools/ingestion_skill/test_service.py`.
    - Effort: 2-3h.
16. **Task 25: Agent integration tests**
    - Description: Confirm agent sees ingestion skill, can call it with sample request, and surfaces response to user.
    - Files: `tests/agent/test_ingestion_skill_integration.py` or manual check documented.
    - Effort: 3h.

### Phase 4: Performance, Docs, Finalization
17. **Task 26: Performance testing**
    - Description: Add optional benchmarks (maybe `tests/performance/test_ingestion_performance.py`) to measure throughput, memory usage, and log results.
    - Effort: 4-6h.
18. **Task 27: Documentation/runbook completion**
    - Description: Update `docs/rag_pipeline_ingestion.md`, `docs/architecture.md` with pipeline diagrams, CLI usage, skill invocation instructions, environment matrix.
    - Effort: 2-3h.
19. **Task 28: Final review/refactor + Archon updates**
    - Description: Ensure KISS/YAGNI compliance, remove dead code, run `ruff`, `mypy`, `pytest`. Update Archon tasks from `review` to `done` post-validation.
    - Effort: 2h.

## Codebase Integration Points
### Files to Modify
- `src/rag_pipeline/config.py` – ensure final configs match CLI overrides; add helper for CLI.
- `src/rag_pipeline/schemas.py` – may need additional fields for embeddings/persistence.
- `src/rag_pipeline/sources/local_files.py` – ensure new tests pass, possible logging adjustments.
- `src/rag_pipeline/chunking/docling_chunker.py` – minor tweaks from testing (Docling detection, chunk indices).
- `src/rag_pipeline/pipeline.py` – implement ingestion orchestration logic.
- `src/agent/agent.py` (or tool registry module) – register ingestion skill tool.
- `docs/architecture.md`, `docs/rag_pipeline_ingestion.md` – include final diagrams/instructions.

### New Files to Create
- `src/rag_pipeline/embeddings/__init__.py` – package exports.
- `src/rag_pipeline/embeddings/qwen_client.py` – embedding client implementation.
- `src/rag_pipeline/persistence/__init__.py` – exports for persistence subpackage.
- `src/rag_pipeline/persistence/supabase_store.py` – DB integration.
- `src/rag_pipeline/pipeline.py` – orchestrator (if not already created for partial functionality).
- `src/rag_pipeline/cli.py` – CLI entrypoint.
- `src/tools/ingestion_skill/__init__.py` (if missing), `schemas.py`, `service.py`, `tool.py`.
- Tests for every module per `PRPs/ai_docs/testing_guide.md` (multiple files listed earlier).

### Existing Patterns to Follow
- `src/shared/logging.py` – structured logger usage.
- `src/shared/config.py` – dataclass-based config approach.
- `tests/shared/test_logging.py` – test style reference.
- `docs/archon_SKILL.md` – process for Archon integration.
- `PRPs/examples` – for DB schema, CLI patterns, Docling chunking approach.

## Technical Design
### Architecture Diagram (Text)
```
CLI / Skill Request
        |
        v
  IngestionRequest ----> run_ingestion_job()
        |                        |
        v                        v
   discover_documents()    ingest_single_document()
                                  |
                                  v
                      DoclingChunker (Docling + fallback)
                                  |
                                  v
                         QwenEmbeddingClient
                                  |
                                  v
                        SupabasePersistenceStore
                                  |
                                  v
                            PostgreSQL (PGVector)
```

### Data Flow
1. CLI or skill constructs `IngestionRequest`.
2. Config loader merges environment + overrides.
3. Document discovery enumerates candidate files with hashes.
4. For each new/changed document, Docling chunker generates chunk candidates.
5. Character enforcement ensures chunk sizes.
6. Embedding client batches chunk text, handles retries, returns vectors with metadata.
7. Persistence store upserts source row, deletes stale chunks (if needed), inserts new chunk rows with embeddings and metadata.
8. Pipeline aggregates success/failure stats, returns `IngestionResult` to CLI or skill.
9. Structured logs capture durations, counts, errors.

### API Endpoints
- CLI: `python -m src.rag_pipeline.cli --source-dir ...`
- FastAPI tool registration: ingestion skill accessible via `agent` tool invocation (no new HTTP endpoint beyond existing `/chat`).

## Dependencies and Libraries
- `docling` (optional) – Document conversion and chunking.
- `transformers` – Tokenizer for Docling chunker fallback.
- `httpx` or `requests` – Embedding API client (depending on Qwen integration path).
- `asyncpg`/`psycopg` – Postgres access.
- `pydantic` – Schemas for requests/responses.
- `pytest`, `pytest-asyncio`, `unittest.mock` – Testing.

## Testing Strategy
- **Unit Tests**: Config parsing, schema validation, discovery, chunking normalization, embedding retry logic, persistence SQL building, pipeline flows (with mocks).
- **Integration Tests**: End-to-end ingestion using ephemeral Postgres (skippable). Could run `docker-compose` service or use Supabase local stack.
- **Performance Tests**: Optional benchmarking script measuring ingestion time per 100 documents, memory usage.
- **Edge Cases**: Missing directories, unsupported file types, Docling missing (fallback path), embedding API failure, DB transaction failure, `force_reingest` true/false, skill request with custom directories, CLI invalid args, chunk splitting/merging extremes.

## Success Criteria
- [ ] Qwen embedding client handles success + retry cases with structured logs.
- [ ] Supabase persistence upserts correctly and idempotently; duplicates prevented.
- [ ] Pipeline ingests new documents, skips unchanged ones based on `content_hash`.
- [ ] CLI prints structured summary and exits with proper status codes.
- [ ] Ingestion skill surfaces results to agent and is discoverable via tools list.
- [ ] All unit/integration tests pass locally via `uv run pytest tests/ -v`.
- [ ] Linting and typing succeed (`uv run ruff check src/`, `uv run mypy src/`).
- [ ] Documentation updated with env vars, CLI usage, skill invocation steps.
- [ ] Archon tasks completed and moved to `done` after validation.

## Notes and Considerations
- Docling dependency may not be installed in every environment; keep fallback path robust and ensure optional imports are guarded to avoid runtime crashes.
- Embedding API credentials (if remote) should be read from secure env vars; avoid logging sensitive tokens.
- Persistence layer should handle network/DB outages gracefully, marking documents as failed with error messages for later retry.
- CLI should support dry-run mode in future (out of scope now but mention in docs).
- For Supabase-hosted Postgres, respect Row Level Security policies if enabling public access; ingestion service likely uses service key.
- Consider adding metrics (counts, durations) to aggregator; in future, export to Prometheus or Archon metrics dashboards.
- Evaluate concurrency options later (currently sequential for simplicity, per KISS/YAGNI).
- Keep ingestion skill docstring token-efficient so Qwen LLM can decide when to call.
- Document manual validation steps (embedding dimension check, DB row inspection) for operations team.
- When finalizing, run validator agent per execute-plan instructions to auto-generate targeted tests.

---
*This plan is ready for execution with `/execute-plan PRPs/requests/rag_pipeline_remaining_work.md`*

## Detailed Task Notes and Acceptance Criteria

### Task 10: Qwen Embedding Client Deep Dive
- Implement `QwenEmbeddingClient` with clear separation between configuration, HTTP invocation, and retry/backoff.
- Provide synchronous API for CLI compatibility plus optional async wrappers for future use.
- Accept both text batches and pre-encoded tokens; start with plain text support.
- Validate that `len(vector)` matches `config.embedding_dimension` (add to config if needed).
- Emit logs: `embedding_batch_started`, `embedding_batch_succeeded`, `embedding_batch_failed` with durations and sizes.
- Implement `request_id` or `batch_id` in logs for cross-correlation.
- Retry strategy: only once, with exponential backoff (configurable default 2 seconds) and jitter.
- Surfacing errors: raise custom `EmbeddingError` capturing request metadata, HTTP status, partial responses.
- Provide metrics hooks (counts of successes/failures) returned via dataclass for future instrumentation.
- Ensure tests mock HTTP layer to cover success, failure, retry, and max-attempt error.
- Document environment variables required for API credentials (e.g., `QWEN_API_KEY`).
- Provide convenience method `embed_document_chunks(chunks: list[ChunkData]) -> list[EmbeddingRecord]` for pipeline integration.
- Guard against empty input lists; return immediately with empty output.
- Confirm thread-safety if reused (avoid storing mutable state beyond session object).
- Expose `close()` for HTTP session cleanup.

### Task 11: Supabase Persistence Layer Deep Dive
- Implement connection abstraction: `DatabaseClientProtocol` with `execute`, `executemany`, `fetchrow`, `fetchval`.
- Provide synchronous wrapper around `psycopg` with context managers for transactions.
- Implement `SupabaseStore` class with methods: `get_source_by_location`, `upsert_source`, `mark_source_status`, `replace_chunks_for_source`.
- Use SQL from schema file; ensure parameterized queries to avoid SQL injection.
- Model DB rows with dataclasses `SourceRow`, `ChunkRow` for clarity.
- Add helper to compute changed documents (compare `content_hash`).
- Logging: `db_query_started`, `db_query_completed`, `db_query_failed` include SQL operation names (not full SQL text to avoid noise) and durations.
- Handle transaction scope: start transaction before chunk upsert, roll back on failure, update source status accordingly.
- Provide convenience method to mark document as `failed` with error message if any step fails.
- Implement `delete_chunks_for_source` to remove outdated rows before inserting new ones.
- Ensure proper usage of PGVector parameter type (list of floats); convert to tuple if required by driver.
- Tests should mock DB client and assert SQL parameter dictionaries match expectation.
- Provide fallback `InMemoryStore` for tests without DB (optional but recommended).
- Document environment variables for DB credentials and required extensions.

### Task 12: Single Document Ingestion Specifics
- Function signature: `ingest_single_document(document: DocumentInput, config: RagIngestionConfig, services: PipelineServices) -> DocumentIngestionResult`.
- `PipelineServices` aggregates dependencies: logger, chunker, embedding client, persistence store, clock provider.
- Steps: upsert source to `pending`, run Docling chunker, enforce character bounds (already in chunker), call embedding client, persist chunks, mark source `ingested` or `failed`.
- Use `contextlib.ExitStack` to manage resource cleanup (embedding session, DB transaction, timers).
- Capture durations for chunking, embedding, DB writes; include in logs and `DocumentIngestionResult` metadata.
- Handle partial chunk/embedding failure: mark status `partially_ingested`, include detail.
- When `force_reingest` false, skip ingestion if existing `content_hash` matches and log `document_skipped`.
- Check for zero chunk output (Docling might skip empty docs); mark `failed` with message.
- Provide instrumentation hooks to allow future metrics export.
- Tests should mock dependencies to ensure each branch (success, skip, failure) covered.
- Return error messages sanitized (no stack traces) but include unique IDs for log correlation.

### Task 13: Ingestion Job Orchestrator Specifics
- Accept `IngestionRequest`, optional `RagIngestionConfig` override, and `PipelineServices`.
- Steps: merge config overrides (source directories, pipeline_id, force flag), call `config.require_sources()`.
- Iterate over directories using `discover_documents`; deduplicate by location; filter using `supported_extensions`.
- Pre-fetch stored sources to skip unchanged documents (call persistence `get_source_by_location` once per doc or use bulk fetch).
- Execute ingestion sequentially initially; plan for future concurrency.
- Track counts: discovered, queued, ingested, skipped, failed, total chunks.
- For each document, catch exceptions and log `document_ingestion_failed` with `exception()`.
- Build `IngestionResult` with `started_at`, `completed_at`, pipeline ID, list of `DocumentIngestionResult` items, aggregated stats.
- Provide ability to stop after N failures (configurable) to avoid cascading errors.
- Add optional `dry_run` flag (maybe future) but mention in docs.
- Tests: use fake documents and stub services; assert aggregator data.

### Task 14: CLI Entry Point Specifics
- Use `argparse` to define options: `--source-dir` (multiple), `--force-reingest`, `--pipeline-id`, `--glob`, `--config-file` (optional), `--output-format json|text`.
- Validate directories exist before running; show friendly error if not.
- Provide summary output including totals, success/failure counts, pipeline ID, start/end timestamps.
- For JSON format, print serialized `IngestionResult` using `.model_dump()`.
- Exit codes: `0` success, `1` if any documents failed, `2` for config errors.
- Add `--version` flag showing git commit if available.
- Logging: print info-level logs plus final summary to stdout.
- Provide `main()` function for easier testing; `if __name__ == "__main__": main()`.
- Tests: use `pytest` `capsys` or `CliRunner` to simulate CLI invocations.

### Task 15: Ingestion Skill Schemas Details
- `IngestionSkillRequest` fields: `directories`, `glob_patterns`, `force_reingest`, `pipeline_id`, `notes` (for Archon context), `requested_by`, `correlation_id`.
- Validate directories list not empty; allow `None` to default to config.
- `IngestionSkillResponse` includes `result: IngestionResult`, plus `warnings`, `next_actions`, `log_reference`.
- Provide `.summary()` method returning short string for agent LM to cite.
- Document sample JSON for Archon knowledge base.

### Task 16: Skill Service Details
- Expose function `execute_ingestion_skill(request: IngestionSkillRequest, *, logger: LoggerProtocol | None = None) -> IngestionSkillResponse`.
- Steps: log `ingestion_skill_invoked`, load config, merge overrides, call pipeline, catch exceptions, return structured response with failure details.
- In case of failure, set `warnings` with actionable guidance, keep `result` maybe partial (or `None`).
- Add instrumentation for total duration.
- Provide ability to supply mock pipeline for testing.
- Tests: ensure logs emitted (use `caplog`), success/failure path coverage.

### Task 17: Tool Registration Details
- Add `tool.py` with `@agent.tool` decorated function `ingestion_skill_tool` (or similar) referencing service.
- Provide docstring per `tool_guide`: summary, “Use This When”, “Do NOT Use”, `Args`, `Returns`, `Performance Notes`, `Examples`.
- Register tool in agent initialization (maybe aggregator file). Update `src/agent/agent.py` to include new tool list or plugin registry.
- Ensure tool is discoverable by LLM; mention environment requirements in docstring (Docling, DB, etc.).
- Provide tests verifying tool metadata string contains required sections.

### Task 18: Expanded Config/Schema Tests
- Add table-driven tests for `_parse_directories`, `_parse_extensions`, `_get_bool` invalid strings, etc.
- Cover `RagIngestionConfig.require_sources()` raising `FileNotFoundError` for missing directories.
- Test `IngestionRequest.document_glob_patterns` default, duplicates removal, custom list.
- Validate `IngestionResult.duration_seconds` for sub-second durations.
- Cover `DocumentMetadata` equality/immutability.

### Task 19: Local Discovery Tests Details
- Use `tmp_path` to create nested directories and sample files.
- Write binary and text files; ensure only supported extensions discovered.
- Validate `content_hash` matches actual SHA-256 (precompute expected using `hashlib`).
- Ensure missing directories log warning but do not throw.
- Test `glob_patterns` filtering functionality when provided to `discover_documents`.

### Task 20: Docling Chunking Tests Details
- Mock `_DoclingBackend` to raise error to exercise fallback path.
- Provide sample text with paragraphs to ensure chunk indices increment correctly.
- Test `enforce_character_bounds` merging small segments and splitting large ones with newline boundaries.
- Validate metadata duplication (page numbers, headings) when splitting.
- Cover `chunk_min_chars >= chunk_max_chars` raising `ValueError`.
- Use property-based test (optional) to ensure total characters preserved.

### Task 21: Embedding Client Tests Details
- Use `pytest.mark.parametrize` for success/failure scenarios.
- Mock HTTP client to return sample embedding vectors; ensure output normalized to floats.
- Simulate HTTP 500 -> expect retry once, then raise `EmbeddingError` with context.
- Test empty input list returns empty result quickly (no HTTP call).
- Validate `batch_size` splits input list into correct batches.

### Task 22: Persistence Layer Tests Details
- Mock DB client capturing executed SQL strings and parameters to assert order (source upsert then chunk delete then insert).
- Simulate DB exception to ensure transaction rolled back and `mark_source_status` called with failure.
- Provide data fixtures for chunk records verifying `metadata` JSON stored correctly.
- For `get_source_by_location`, ensure `None` when not found.
- Cover `replace_chunks_for_source` verifying chunk_index uniqueness constraint is resolved via `ON CONFLICT` or manual delete.

### Task 23: Integration Test Details
- Use `pytest` marker `@pytest.mark.integration`.
- Provide fixture launching ephemeral Postgres via docker-compose or `testcontainers`. Skip if not available.
- Insert sample docs into temp directory, run pipeline, query DB to assert rows inserted with correct metadata.
- Use stub embedding client returning deterministic vectors (e.g., `[index] * dimension`).
- Ensure ingestion run logs summary and `IngestionResult` matches DB contents.

### Task 24: Skill Service Test Details
- Mock pipeline to return sample `IngestionResult`.
- Ensure failures raise `SkillExecutionError` or return response with warnings.
- Validate logging via `caplog` includes `ingestion_skill_invoked` and `ingestion_skill_completed` events.
- Test request overriding directories/pipeline ID flows through to pipeline call.

### Task 25: Agent Integration Test Details
- Use `TestClient` to call `/chat` with prompt instructing agent to reindex docs; assert tool invocation stub called.
- For unit-level test, instantiate agent with fake tool registry, call `agent.tools['ingestion_skill'](...)` verifying behaviour.
- Document manual steps for verifying tool in actual Archon environment.

### Task 26: Performance Testing Details
- Add optional script measuring ingestion throughput with synthetic corpus (create random text files of varying sizes).
- Record metrics: docs/min, chunks/min, average chunk size, embedding latency.
- Provide CLI flag `--profile` to log more detailed metrics (optional future).
- Document results in `docs/rag_pipeline_ingestion.md` for baseline comparisons.

### Task 27: Documentation Tasks Details
- Expand docs with sections: “Quick Start”, “CLI Usage Examples”, “Troubleshooting”, “Skill Invocation Walkthrough”, “Archon Task Workflow”.
- Provide sample commands for ingestion skill via agent prompt.
- Document environment variable defaults and recommended overrides for prod/staging.
- Add architecture diagram showing entire data flow and dependencies.
- Include table mapping Archon tasks to code modules for easier auditing.

### Task 28: Final Review & Validation Details
- Run `uv run ruff check src/` and `uv run mypy src/`; capture output for handoff.
- Execute `uv run pytest tests/ -v`; re-run with `-m integration` if environment supports Postgres.
- Launch validator agent per execute-plan instructions to auto-generate targeted tests.
- Prepare change summary referencing files touched, tests run, open issues.
- Update Archon tasks statuses: `review` -> `done` only after validations succeed; add notes for any deferred work.
- Provide final report to user summarizing metrics, known gaps, future recommendations.

## Risk Assessment and Mitigations
- **Dependency Availability**: Docling/transformers might not be installed. Mitigation: guard imports, fallback chunker, document optional dependencies.
- **Embedding API Limits**: Qwen API quotas may throttle ingestion. Mitigation: batch requests, expose rate limit errors clearly, allow manual throttling (sleep between batches if env var set).
- **Database Connectivity**: Supabase might drop connections; implement retry logic at DB layer or rely on driver connection pooling.
- **File System Changes During Run**: Files might change while ingestion running. Mitigation: compute `content_hash` just before reading, optionally re-open file for chunking to ensure consistency.
- **Large Files**: Very large PDFs may stress Docling. Mitigation: chunker already enforces char bounds; consider streaming conversion or memory limit config (document in runbook).
- **Testing Environment Limitations**: Without local Postgres, integration tests must be skipped gracefully. Provide clear instructions for enabling them.
- **Skill Token Usage**: Tool docstrings/responses should be concise to avoid unnecessary token burn. Provide `response_format` options in skill.

## Timeline Draft (assuming sequential execution)
1. Days 1-2: Implement embedding client + tests.
2. Days 3-4: Build persistence layer + tests.
3. Days 5-6: Pipeline (single doc + orchestrator) + CLI.
4. Days 7-8: Skill schemas/service/tool integration.
5. Days 9-10: Comprehensive unit tests for discovery, chunking, embeddings, persistence.
6. Days 11-12: Integration tests, performance benchmarks (optional), documentation updates.
7. Day 13: Validator agent + cleanup, Archon task finalization.

## Tooling and Automation Checklist
- [ ] Add `make ingest` target (optional) to run CLI with defaults.
- [ ] Add `pre-commit` hooks for formatting/linting (if not already).
- [ ] Provide sample `.env` file referencing new environment variables.
- [ ] Add GitHub Actions workflow step for ingestion tests (if repository uses CI).
- [ ] Document how to run ingestion skill via CLI for manual verification (`uv run python - <<'PY' ...`).

## Archon Task Mapping
- Task 10 ↔ Archon `43583a80-1711-4e35-a01c-a9a1e5be289d`.
- Task 11 ↔ `73742cb7-9a1b-46fa-9274-df0d5fe5b233`.
- Task 12 ↔ `586ee072-28ce-4d5c-bb6d-f27c387a2119`.
- Task 13 ↔ `931810af-6ab2-4de5-a89b-22fca6312796`.
- Task 14 ↔ `e27712b1-2157-46e3-9986-e33421085695`.
- Task 15 ↔ `071fb47d-65ca-4709-91a0-43276af7eebc`.
- Task 16 ↔ `070ecda6-647f-4449-a59d-da50c75db698`.
- Task 17 ↔ `be1f2d9d-a291-4e4e-8117-28520f60f138`.
- Task 18 ↔ `db36a1c3-a64c-4911-9c21-6ba7717aa7e5`.
- Task 19 ↔ `28bcb635-2c67-4b9c-ab3f-db38f6c55aa5`.
- Task 20 ↔ `84c4c564-8b6e-418c-8ef7-11c9f5dc8842`.
- Task 21 ↔ `7155ca23-a5ba-4f69-8a41-94cf141e8588`.
- Task 22 ↔ `cb5b88d3-77a7-4754-a22c-40da9cd43d2b`.
- Task 23 ↔ `41e372d6-3279-4197-92eb-72d2c9be174b`.
- Task 24 ↔ `395b7c57-9307-4f7b-807b-debed121e178`.
- Task 25 ↔ `673655b2-74ed-43d1-9401-c094d466d09a`.
- Task 26 ↔ `4532d714-e803-48ef-ba21-1ac858fd9e13`.
- Task 27 ↔ `56518f87-3a0f-4453-9919-b05e6dba200b`.
- Task 28 ↔ `7ae2dab2-b8f1-491a-bcdb-c458ea1466f2`.

## Additional Research Notes
- Investigate Qwen embedding service deployment options (local vs API). Document any prerequisites for local GPU inference.
- Review Supabase connection pooling best practices (pgbouncer) to avoid connection storms during ingestion.
- Evaluate doc chunk normalization strategies (strip control chars, unify whitespace) before embedding.
- Inspect `docs/hybrid_search.md` for scoring functions; align chunk metadata fields to support lexical/trigram search (e.g., store `section_heading`, `page_number`).
- Explore use of `SentencePiece` tokenization for token estimates if Qwen uses different tokenizer (Docling currently uses `all-MiniLM` as example; confirm compatibility).
- Confirm PGVector dimension (1024). Provide migration path if future models differ.
- Determine whether `match_chunks` function requires adjustments for hybrid weighting; plan future improvements.
- Document fallback strategy if Supabase offline (queue ingestion results locally?). Out of scope now but mention under considerations.

## Operational Checklist Prior to Deployment
1. Confirm environment variables set for DB URL, Embedding API key, Docling optional dependencies.
2. Seed `rag.sources` and `rag.chunks` tables by running ingestion on sample corpus to validate schema.
3. Validate CLI usage path for operations team (shell script or scheduled job).
4. Train support engineers on reading logs/metrics (structured logging fields, correlation IDs).
5. Provide runbook for triaging ingestion failures (embedding, Docling, DB categories).
6. Document backup strategy for `rag` schema (pg_dump) and retention policies.
7. Align with security requirements (limit service key usage, apply RLS rules if storing sensitive docs).
8. Create Archon knowledge base entry summarizing ingestion pipeline for future reference.

## Future Enhancements (Post-MVP)
- Add concurrency for ingestion (parallel embeddings) with rate limiting.
- Support additional document sources (Supabase Storage, S3) via new adapters implementing `DocumentSourceProtocol`.
- Implement incremental re-embedding job to migrate to fine-tuned models; track model versions per chunk.
- Integrate retrieval evaluation harness using labelled query/chunk pairs.
- Provide REST API for triggering ingestion runs programmatically.
- Expose metrics to Prometheus / Grafana dashboards.
- Add caching for Docling conversions to avoid reprocessing unchanged PDFs when only metadata changed.
- Explore streaming chunking to reduce memory usage on large PDFs.


## Per-Task Microsteps

### Task 10 Microsteps
1. Define `EmbeddingError` exception class with context fields (status_code, retry_count, batch_id).
2. Update `RagIngestionConfig` to include `embedding_timeout_seconds`, `embedding_retry_backoff_seconds`, `embedding_dimension` if missing.
3. Implement HTTP session creation with configurable base URL.
4. Add helper `_build_payload(texts: list[str]) -> dict[str, Any]` aligning with Qwen API contract.
5. Add `_parse_response` to convert JSON into list of float vectors.
6. Implement `_log_batch_start` and `_log_batch_end` functions for consistent logging payloads.
7. Add retry wrapper using `time.sleep(backoff)` once; log `retry_attempt` event.
8. Ensure method raises `EmbeddingError` with truncated text sample when failing.
9. Write unit tests using `pytest` + `monkeypatch` to simulate HTTP responses.
10. Document usage inside module docstring referencing env vars.

### Task 11 Microsteps
1. Define `DatabaseClientProtocol` and `TransactionContext` protocols.
2. Implement `PsycopgDatabaseClient` with connection reuse and context manager.
3. Write SQL constants for source/chunk operations referencing schema file.
4. Provide helper `_serialize_chunk_metadata` to convert dataclass to JSONB.
5. Implement `SupabaseStore.upsert_source` returning DB row ID for subsequent chunk operations.
6. Add `SupabaseStore.mark_source_status` supporting statuses + error message.
7. Implement `SupabaseStore.replace_chunks_for_source` with transaction: delete, insert via `executemany`.
8. Provide `SupabaseStore.fetch_source_by_location` returning `SourceRecord | None`.
9. Add logging for each DB operation with durations.
10. Create tests mocking DB client verifying SQL order and parameters.

### Task 12 Microsteps
1. Add `PipelineServices` dataclass bundling dependencies.
2. Implement helper `_should_reingest(existing_source, document, force_flag)`.
3. Create timer context manager to measure durations.
4. On ingestion start, log `document_ingestion_started` with metadata.
5. Call chunker, check for empty result -> raise `ChunkingError`.
6. Pass chunk texts into embedding client, capturing vectors.
7. Format `ChunkRecord` entries combining metadata + embedding model info.
8. Call persistence store to upsert source + replace chunks within transaction.
9. Mark source status `ingested` or `partially_ingested` (if some chunks failed) or `failed` (if exception).
10. Assemble `DocumentIngestionResult` with chunk count, duration, error message if any.

### Task 13 Microsteps
1. Accept CLI overrides via `IngestionRequest` and merge with config.
2. Invoke `discover_documents` for each directory/glob pattern; gather results list.
3. Fetch existing sources (either lazily per doc or pre-batch) to compare hashes.
4. Build queue of documents requiring ingestion and of skipped ones for logging.
5. Loop through queue sequentially; after each ingestion, update aggregated stats.
6. Keep track of first error to display at CLI (without halting unless fatal).
7. Support optional `max_documents` limit for testing (env-driven) to avoid huge runs.
8. After loop, build `IngestionResult` with `stats` and `documents` lists.
9. Log `ingestion_job_completed` with totals and durations.
10. Return `IngestionResult` to caller (CLI or skill service).

### Task 14 Microsteps
1. Build `argparse.ArgumentParser` with description referencing docs.
2. Define `--source-dir`, `--glob`, `--force-reingest`, `--pipeline-id`, `--output json|text` options.
3. Parse args, instantiate `IngestionRequest` accordingly.
4. Call `run_ingestion_job` and capture result; handle exceptions with friendly message.
5. Format output based on `--output`: text summary vs JSON.
6. Print per-document results when `--verbose` flag set.
7. Set exit code >0 if `result.stats.documents_failed > 0`.
8. Provide `--dry-run` placeholder (maybe not implemented but mention).
9. Wrap `main()` for import-safety.
10. Add CLI tests verifying output and exit codes using `pytest`.

### Task 15 Microsteps
1. Define Pydantic models with alias support for compatibility with Archon (snake_case fields).
2. Add validators ensuring directories/glob patterns are sensible.
3. Provide `.to_ingestion_request()` method bridging to core pipeline schema.
4. Include `SkillRequestMetadata` submodel capturing `requested_by`, `notes`, etc.
5. Document sample JSON in module docstring.
6. Add tests verifying validation errors for invalid directories.
7. Ensure models are type-annotated with `list[str]` etc.
8. Provide helper for summarizing results for chat responses.
9. Keep module-level constant referencing skill name.
10. Document interplay with config env variables.

### Task 16 Microsteps
1. Implement service entrypoint accepting `IngestionSkillRequest`.
2. Log start event with directories, pipeline ID, correlation ID.
3. Call config loader, merge overrides, instantiate pipeline services.
4. Run pipeline inside try/except; on exception, log `ingestion_skill_failed` and construct response with warnings.
5. On success, build `IngestionSkillResponse` referencing `IngestionResult`.
6. Provide optional callback hook for notifying Archon (future), placeholder for now.
7. Add tests mocking pipeline to return deterministic result.
8. Ensure service is synchronous for compatibility (async wrapper optional later).
9. Document how service integrates with tool.
10. Provide metrics (duration) in logs.

### Task 17 Microsteps
1. Read `PRPs/ai_docs/tool_guide.md` to ensure docstring format compliance.
2. Implement tool function referencing service; accept agent context + schema parameters.
3. Provide docstring sections: summary, “Use this when”, “Do not use”, Args, Returns, Performance Notes, Examples.
4. Register tool with agent (update agent initialization to include ingestion skill in tool list).
5. Provide tests ensuring docstring contains required keywords (Use this when, Do NOT).
6. Ensure tool returns string summarizing ingestion result (maybe `response.summary()`), but also attaches structured data to context.
7. Add ability to limit directories/timeouts via tool args.
8. Document known prerequisites (Docling optional, Postgres connection) so agent can reason when not to call.
9. Provide sample usage snippet for docs.
10. Validate that tool respects type safety (Pydantic parsing before calling pipeline).

### Task 18 Microsteps
1. Expand config tests to cover `_get_bool` invalid values raising ValueError.
2. Add tests ensuring `_parse_extensions` adds leading dot when not provided.
3. Test `iter_supported_extensions` returns lower-case entries.
4. Validate `DocumentIngestionResult` accepts optional durations and errors.
5. Add `pytest.raises` checks for `RagIngestionConfig.require_sources` when directories missing.
6. Ensure `IngestionResult.duration_seconds` handles same timestamps (0 seconds) gracefully.
7. Cover new schema fields from ingestion skill.
8. Document tests with descriptive docstrings referencing requirements.

### Task 19 Microsteps
1. Create temp directory tree with nested subfolders and mix of file types.
2. Write helper to compute expected SHA-256 for sample file to assert equality.
3. Use `monkeypatch` to override `logger` capturing warnings when directories missing.
4. Validate `glob_patterns` filtering works (only files matching pattern discovered).
5. Ensure `discover_documents` yields `DocumentInput` with correct metadata types.
6. Add test verifying unsupported extensions ignored silently.
7. Include case where file read fails (simulate permission error) to ensure warning logged and ingestion continues.

### Task 20 Microsteps
1. Use sample text string > chunk_max_chars to trigger splitting logic.
2. For merging, pass two small segments to ensure they combine when below min.
3. Test `ChunkMetadata.extra` preserved when merging/splitting.
4. Simulate `_DoclingBackend` chunk output by monkeypatching `DoclingChunker._docling_backend` with fake object returning deterministic chunks.
5. Assert fallback path triggered when backend raises `ChunkingError`.
6. Ensure chunk indices re-labeled sequentially after normalization.
7. Document tests referencing `docs/docling.md` rationale.

### Task 21 Microsteps
1. Mock HTTP responses with `requests_mock` or manual stub to return sample vectors.
2. Test `embedding_batch_size` splitting logic by passing e.g., 13 texts with batch size 5.
3. Simulate HTTP timeout to ensure client handles exception and retries once.
4. Confirm jitter/backoff invoked (monkeypatch `time.sleep`).
5. Validate that when API returns partial embeddings count mismatch, client raises error.
6. Ensure floats converted to Python `float` even if API returns Decimal/strings.
7. Add test verifying API key header included when configured.

### Task 22 Microsteps
1. Provide SQL fixtures for verifying `upsert_source` uses `ON CONFLICT (location)`.
2. Mock DB to raise exception during chunk insert; assert transaction rolled back and error logged.
3. Validate `replace_chunks_for_source` deletes rows before inserts to avoid duplicates.
4. Ensure metadata JSON saved as expected; tests can check parameters passed to DB client.
5. Cover scenario where `get_source_by_location` returns `None` for unknown document.
6. Add tests verifying `mark_source_status` sets error message when provided.

### Task 23 Microsteps
1. Create `pytest` fixture launching Postgres container via `testcontainers` (if allowed) or instruct manual run.
2. Apply schema from `PRPs/examples/rag_pipeline_docling_supabase.sql` before tests run.
3. Use stub embedding client to avoid hitting real Qwen.
4. Run pipeline on sample docs, query DB to confirm rows inserted and statuses correct.
5. Clean up DB tables after tests to avoid cross-run contamination.

### Task 24 Microsteps
1. Mock pipeline returning success to ensure service passes through result.
2. Mock pipeline raising exception; ensure response includes warning and logs error.
3. Validate request metadata (directories, pipeline_id) forwarded correctly.
4. Confirm `IngestionSkillResponse.summary()` returns concise text for agent.

### Task 25 Microsteps
1. Extend agent tests to ensure tool registry includes ingestion skill.
2. Simulate user query triggering ingestion; stub ingestion service to respond quickly.
3. Assert agent returns statement referencing ingestion run summary.
4. Provide manual validation instructions for human testers (call skill via CLI or Postman).

### Task 26 Microsteps
1. Develop script generating synthetic docs of various sizes to stress pipeline.
2. Measure doc throughput and log to file for comparison.
3. Provide guidance on adjusting `embedding_batch_size` and concurrency to improve performance.
4. Document baseline metrics (target docs/min) in runbook.

### Task 27 Microsteps
1. Add `Quick Start` section to docs with prerequisites and first ingestion commands.
2. Provide `Troubleshooting` table covering Docling missing, DB connection errors, embedding API failures.
3. Include `FAQ` (e.g., “How do I re-ingest a single document?”).
4. Embed ASCII architecture diagram illustrating pipeline.
5. Update `README.md` snippet referencing ingestion CLI.

### Task 28 Microsteps
1. Run full lint/type/test suite; capture logs.
2. Execute validator agent to auto-generate targeted tests and record results.
3. Review code for adherence to KISS/YAGNI; remove dead prototypes.
4. Update Archon tasks statuses to `done` with notes summarizing work.
5. Prepare final summary for user.

## Testing Matrix
- **Unit**: config, schemas, discovery, chunking, embeddings, persistence, pipeline orchestrator, CLI, skill service, tool.
- **Integration**: pipeline with Postgres, CLI invocation, ingestion skill end-to-end (agent calling tool with mocked pipeline).
- **Performance**: ingest 50+ documents, record throughput.
- **Validator**: run validator agent to auto-generate test cases ensuring CLI + pipeline behaviour.

## Logging Events Reference
- `ingestion_job_started` – includes pipeline_id, directories, force flag.
- `ingestion_job_completed` – includes duration_ms, documents_ingested, documents_failed.
- `document_ingestion_started` – includes file path, size_bytes, hash.
- `document_ingestion_completed` – includes chunk_count, duration_ms, status.
- `docling_chunking_failed` – includes error, fallback_used.
- `embedding_batch_started` / `embedding_batch_completed` / `embedding_batch_failed` – includes batch size, duration.
- `db_query_started` / `db_query_completed` / `db_query_failed` – includes query name and duration.
- `ingestion_skill_invoked` / `ingestion_skill_completed` – includes directories, pipeline_id, result summary.

## Validation Checklist
1. CLI run with sample data; verify DB rows.
2. Ingestion skill invoked via agent; confirm response surfaced to `/chat` response.
3. Lint/type/test commands succeed.
4. Validator agent report captured and shared.
5. Documentation updated and reviewed.
6. Archon tasks statuses updated accordingly.


## Detailed Testing Scenarios by Module

### Config Module
- Scenario C1: No env vars set → expect defaults.
- Scenario C2: Invalid integer env var (non-numeric) → ValueError.
- Scenario C3: Boolean env var values `TRUE`, `false`, `1`, `0`, `on`, `off` all parsed correctly.
- Scenario C4: Missing directories → `require_sources` raises `FileNotFoundError`.
- Scenario C5: Custom supported extensions string `pdf,md` → normalized tuple.

### Schemas Module
- Scenario S1: `IngestionRequest` with custom globs; verify `document_glob_patterns` order preserved.
- Scenario S2: `IngestionResult.failed_documents()` returns only failed entries.
- Scenario S3: `DocumentIngestionResult` optional error field serializes to JSON.
- Scenario S4: `ChunkRecord` metadata ensures `embedding_model` stored.
- Scenario S5: `SourceIngestionStatus` conversions to/from string remain stable (Enum tests).

### Discovery Module
- Scenario D1: Mixed-case extension (".PDF") still discovered.
- Scenario D2: File read permission error -> logged warning, file skipped.
- Scenario D3: Very large file hashed without loading entirely (streaming read test via mock).
- Scenario D4: `glob_patterns` filtering to specific subdirectory.
- Scenario D5: Duplicate file names in different dirs handled separately due to absolute paths.

### Chunking Module
- Scenario H1: Docling backend available -> `_docling_backend` used.
- Scenario H2: Docling backend missing -> fallback path triggered.
- Scenario H3: Input chunk shorter than min chars and not mergeable -> remains single chunk.
- Scenario H4: Large chunk split near whitespace boundary rather than midword.
- Scenario H5: Metadata `extra` dictionary cloned rather than shared references (mutability test).

### Embedding Module
- Scenario E1: Batch of N texts processed with configured batch size.
- Scenario E2: HTTP non-200 response triggers retry.
- Scenario E3: API returns mismatched vector count -> raises error.
- Scenario E4: Timeout -> retry once, then fail with descriptive message.
- Scenario E5: API key missing -> fail fast with configuration error message.

### Persistence Module
- Scenario P1: Upsert new source returns generated ID.
- Scenario P2: Upsert same source with same hash does not create duplicate; maybe updates status.
- Scenario P3: Replace chunks for source uses transaction (mock ensures `BEGIN` called before operations).
- Scenario P4: Database operation raises exception -> ensure rollback invoked.
- Scenario P5: DB connection failure surfaces as `PersistenceError` with context.

### Pipeline Module
- Scenario L1: Document skipped when hash matches and force flag false.
- Scenario L2: Force reingest true -> ingestion runs even if hash matches.
- Scenario L3: Embedding failure -> mark source failed and continue to next doc.
- Scenario L4: After ingestion run, CLI summary matches stats from `IngestionResult`.
- Scenario L5: Pipeline gracefully handles zero documents discovered (no errors, stats zero).

### CLI Module
- Scenario CLI1: No args -> uses config directories.
- Scenario CLI2: `--source-dir` repeated -> aggregated list.
- Scenario CLI3: `--output json` prints valid JSON.
- Scenario CLI4: `--force-reingest` flag recognized.
- Scenario CLI5: Invalid directory path -> exit code 2 with message.

### Skill Module
- Scenario SK1: Request with directories overriding config.
- Scenario SK2: Pipeline raises exception -> response warnings populated.
- Scenario SK3: Response summary string includes counts and pipeline ID.
- Scenario SK4: Logger receives `ingestion_skill_invoked` event with metadata.
- Scenario SK5: Tool docstring accessible and includes required sections.

## Expanded Documentation Topics
1. **Environment Variable Reference Table** – include descriptions, defaults, example values, and where they apply (CLI vs Skill vs Pipeline).
2. **Supabase Setup Steps** – enabling PGVector, running schema SQL, verifying indexes, granting permissions.
3. **Docling Installation Guide** – optional dependency instructions, GPU/CPU notes, fallback behaviour if not installed.
4. **Embedding Client Configuration** – setting API keys, base URLs, batch sizes, timeouts, retry strategy.
5. **CLI Cookbook** – sample commands for nightly ingestion, ad-hoc reingest, and debugging runs.
6. **Skill Usage Guide** – how to instruct the agent (“Reindex the finance folder”), expected response shape, troubleshooting skill errors.
7. **Troubleshooting** – categorize by discovery, chunking, embedding, persistence, skill invocation.
8. **Monitoring** – how to tail logs, use structured log fields (`event`, `pipeline_id`, `document`), future metrics roadmap.
9. **Archon Workflow** – remind developers to keep tasks updated (todo → doing → review → done) and document statuses.
10. **Validator Agent Process** – describe when/how to invoke, what results to expect, and how to address failures.


## Final Reminders
- Keep Archon connectivity active; log every status transition with timestamps for audit trail.
- Revisit plan periodically to ensure scope remains aligned with KISS/YAGNI; trim optional items if timelines tighten.
- Store this plan in Archon knowledge base for future reference before executing `/execute-plan`.

