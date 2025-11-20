# Implementation Plan: Phase 4 Hardening, Observability, and Performance Validation

## Overview
This plan describes Phase 4 follow-up work after the post-ingestion validation pass.
It first makes the repository easy to adopt for new users by providing an end-to-end
README-driven quickstart (clone → configure → run) and a simple, production-viable
frontend chat UI for the RAG assistant. After those onboarding pieces are in place,
the plan focuses on hardening the ingestion pipeline, improving observability and
logging, polishing the ingestion CLI and developer ergonomics, and activating a
realistic performance validation loop.

The goal is that someone who clones the repo can:
- Follow the README to set up Python, connect to their database and LLM, ingest their
  own documents, and start chatting with the assistant via a browser UI.
- Benefit from a production-ready ingestion and RAG pipeline that is debuggable,
  reliable, and predictable under load while staying aligned with the AGENTS.md
  principles (KISS, YAGNI, strict typing, and Google-style documentation).

The work items here assume:
- Phase 1–3 tasks from `PRPs/requests/rag_pipeline_remaining_work.md` and
  `PRPs/requests/next_steps_validation_plan.md` have been implemented or are at
  least in review, and no new work in this plan is started before earlier phases
  are merged or explicitly signed off.
- The linting, typing, and non-performance test suites already pass (as captured in
  `docs/post_ingestion_validation.md`).
- The Docling backend is integrated and conditionally disabled after failures.
- The ingestion skill and pipeline wiring are functionally correct but can be further
  hardened through retries, observability, and CLI UX improvements.
- Performance tests exist but are currently deselected and must be run on appropriate
  hardware.

This plan is written so it can be executed incrementally. Each phase can be delivered
in smaller PRs that map cleanly to Archon tasks, with explicit success criteria and
test coverage added alongside the changes.

## Requirements Summary
- Turn the top-level `README.md` into a complete quickstart that shows new users how
  to install dependencies, configure environment variables (LLM and database), run
  the backend, ingest documents, and validate their setup with minimal friction.
- Provide a minimal but usable frontend chat UI (web page or SPA) that connects to
  the FastAPI `/chat` endpoint, handles streaming or batched responses, and can be
  configured easily in local development.
- Document how to configure and connect the RAG pipeline to a local PostgreSQL/
  Supabase database using `RAG_DATABASE_URL` and the provided SQL schema, including
  any required extensions and migrations.
- Add robust, configurable retry and backoff behavior around ingestion-critical
  operations (Supabase persistence, embeddings, Docling conversions, and external
  HTTP calls) with clear logging and metrics.
- Enhance structured logging and observability for ingestion jobs, ingestion tools,
  Docling fallbacks, and embedding batches, including correlation IDs and timing
  information that make debugging production issues straightforward.
- Polish the ingestion CLI and tool interfaces so they are self-documenting, include
  guardrails against misuse, and surface progress and error details clearly.
- Activate and stabilize the performance test suite (`tests/performance`) on
  representative hardware, capturing baseline metrics and ensuring the pipeline holds
  up under realistic load.
- Revisit the Docling backend disabling behavior and introduce a safe, configurable
  re-enable mechanism for mixed workloads (supported and unsupported formats) without
  sacrificing reliability.
- Keep all changes type-safe and fully annotated, with mypy and ruff remaining
  clean, while tests stay fast by default and performance tests stay opt-in.

## Research Findings

### Best Practices
- Prefer explicit, small, composable retry helpers over ad-hoc try/except blocks
  scattered across the codebase. Centralize retry behavior and make it configurable
  via settings or dependency injection.
- Use structured logging (key/value fields) for all ingestion job lifecycle events:
  job start, job end, per-document progress, retry attempts, fallbacks, and failures.
  Include `correlation_id`, `source`, and `duration_ms` consistently.
- Keep CLI interfaces predictable: clear positional vs. option arguments, idempotent
  operations where possible, and dry-run modes or confirmation prompts for destructive
  actions (large reingestion, deletion, or resets).
- Separate fast feedback tests (unit + small integration) from heavier performance
  or load tests using markers so local and CI runs stay fast and reliable.
- Ensure performance tests are reproducible: stable datasets, deterministic seed
  setups where reasonable, and explicit documentation on required hardware and
  environment configuration.
- For RAG pipelines, log enough retrieval and chunking metadata (top-k scores,
  chunk counts, fallback counts, data source identifiers) so regressions in
  relevance or performance can be investigated even after the fact.
- When introducing new behavior (e.g., retries, fallback logic), always accompany
  it with clear metrics (e.g., retry counts, success-after-retry) and tests that
  cover the happy path, failure path, and fallback behavior.

### Reference Implementations
- `docs/post_ingestion_validation.md` documents the current validation status and
  remaining follow-ups; use it to ensure Phase 4 tasks line up with known gaps.
- `PRPs/requests/next_steps_validation_plan.md` demonstrates how to structure large,
  multi-phase implementation plans in this repo; reuse its level of detail and
  approach for sequencing work.
- `PRPs/requests/rag_pipeline_remaining_work.md` defines earlier phases of the
  Docling hybrid RAG pipeline; treat this plan as Phase 4+ and avoid reordering or
  skipping remaining work from those phases.
- `PRPs/ai_docs/logging_guide.md` (to be consulted in detail) should guide naming,
  field selection, and logging patterns, including how to handle `correlation_id`
  and structured log fields across the pipeline.
- `PRPs/ai_docs/tool_guide.md` provides expectations for tools, schemas, and
  service slices; rely on it when updating ingestion-specific tools and their
  docstrings or schemas.
- `PRPs/ai_docs/testing_guide.md` should be used as the source of truth for test
  structure, naming, and marker usage, including separation between unit,
  integration, and performance tests.
- `PRPs/examples/Front_end_UI_example` contains a working React/Vite-based chat
  interface powered by the Gemini API; use its layout, session management, and
  component structure as a template for the RAG frontend while replacing the
  Gemini-specific service layer with calls to the local FastAPI `/chat` endpoint.
- `src/tools/ingestion_skill/tool.py` and `src/tools/ingestion_skill/service.py`
  show how ingestion tools are wired and how logging and configuration currently
  work in practice; use them as starting points for CLI and logging improvements.
- `src/rag_pipeline/pipeline.py` is the central orchestration for ingestion and
  retrieval; its logging and service wiring should be extended rather than
  bypassed when adding retries or metrics.
- `src/rag_pipeline/chunking/docling_chunker.py` contains the Docling backend
  integration and fallback behavior; this is the primary location for re-enable
  logic and improved error reporting.
- `src/rag_pipeline/embeddings/qwen_client.py` and related clients define how
  external embedding services are called; these are the natural places to hook in
  retry behavior and detailed logging.
- `src/rag_pipeline/persistence/supabase_store.py` encapsulates persistence
  operations; it is the right place to introduce retry-aware execution wrappers
  and to log query-level metrics.
- `src/shared/logging.py` hosts logging utilities and protocols; it should be
  extended (if needed) to support new structured fields and convenience helpers
  without breaking existing behavior.
- `tests/performance/` (once inspected) should host the performance suite; its
  structure will guide where to add new performance scenarios and fixtures.

### Technology Decisions
- Continue using the existing logging stack and `src/shared/logging.py` helpers;
  avoid introducing heavy new logging dependencies unless absolutely necessary.
- Implement retries using simple, well-typed helper functions or small utility
  classes (e.g., backoff loops) within the existing codebase rather than bringing
  in large third-party retry libraries, unless future requirements demand them.
- Keep configuration centralized in the existing configuration or settings
  mechanisms (likely under `src/utils` or similar) so retry counts, backoff
  timing, and feature flags can be adjusted without code changes.
- Maintain the current FastAPI/Starlette stack for any HTTP exposure of ingestion
  operations; avoid overhauling transport layers during this hardening phase.
- Keep mypy in strict mode and avoid `Any` where possible; when necessary,
  justify Any usage explicitly and isolate it in small, well-documented helpers.
- Use pytest markers (`@pytest.mark.performance`) to ensure performance tests
  remain opt-in and do not slow down standard CI or developer workflows.
- Prefer incremental changes over large refactors; improve one axis (logging,
  retries, CLI) per PR to make review and rollback easier.

## Implementation Tasks

### Phase 0: README Quickstart & Backend Setup

1. **Audit Existing README and Docs**
   - Description: Review `README.md`, `docs/architecture.md`, and
     `docs/rag_pipeline_ingestion.md` to identify gaps for a “clone → run”
     workflow, especially around environment creation, LLM credentials, database
     setup, and ingestion/validation steps.
   - Files to modify/create: `README.md`, `docs/architecture.md`,
     `docs/rag_pipeline_ingestion.md`.
   - Dependencies: None.
   - Estimated effort: 1–2h.

2. **Define the Canonical Quickstart Flow**
   - Description: Decide on the recommended path for new users (e.g., `uv` for
     environment, FastAPI backend at `uvicorn src.main:app`, ingestion via
     CLI or skill). Draft a concise sequence: clone repo → create env →
     install dependencies → configure env vars → run backend → ingest docs →
     run validation commands.
   - Files to modify/create: `README.md`.
   - Dependencies: Task 1.
   - Estimated effort: 1–2h.

3. **Document LLM and Embedding Configuration**
   - Description: Add a dedicated section explaining how to configure the primary
     assistant model and embedding model (Qwen3 variants and/or local models),
     including environment variables, default choices, and any optional switches
     (e.g., fine-tuned embeddings). Link to `PRPs/ai_docs/fine-tuned-embeddings.md`.
   - Files to modify/create: `README.md`, `docs/models.md`.
   - Dependencies: Task 2; model choices confirmed.
   - Estimated effort: 2–3h.

4. **Document Database and RAG Pipeline Connection**
   - Description: Provide step-by-step instructions to set up a local PostgreSQL or
     Supabase instance, apply `PRPs/examples/rag_pipeline_docling_supabase.sql`, and
     configure `RAG_DATABASE_URL` plus related env vars. Include example connection
     strings and notes on PGVector and `pg_trgm` extensions.
   - Files to modify/create: `README.md`, `docs/rag_pipeline_ingestion.md`.
   - Dependencies: Task 1; database assumptions finalised.
   - Estimated effort: 2–3h.

5. **Describe Document Ingestion Workflow**
   - Description: Summarize how to place documents in `./documents` (or custom
     directories), run the ingestion CLI or skill, and verify success via logs and
     simple queries. Include at least one concrete CLI invocation.
   - Files to modify/create: `README.md`, `docs/rag_pipeline_ingestion.md`.
   - Dependencies: Task 4.
   - Estimated effort: 1–2h.

6. **Add Validation & Troubleshooting Section**
   - Description: Add a section that shows how to run `ruff`, `mypy`, and `pytest`
     and how to interpret common failures (missing env vars, database unreachable,
     Docling not installed). Cross-link to `docs/post_ingestion_validation.md`.
   - Files to modify/create: `README.md`, `docs/post_ingestion_validation.md`.
   - Dependencies: Task 1.
   - Estimated effort: 1–2h.

7. **Review README for New-User Clarity**
   - Description: Perform a readability pass on `README.md` to ensure a new user
     can follow the quickstart without reading any other files; adjust ordering,
     headings, and examples as needed.
   - Files to modify/create: `README.md`.
   - Dependencies: Tasks 2–6.
   - Estimated effort: 1–2h.

### Phase 1: Frontend Chat UI

1. **Choose Frontend Stack and Integration Mode**
   - Description: Decide on a minimal frontend approach that reuses as much as
     possible from the existing example in `PRPs/examples/Front_end_UI_example`
     (React + Vite). Adapt that structure so the app talks to the local FastAPI
     `/chat` endpoint instead of the Gemini API, keeping configuration simple for
     new users.
   - Files to modify/create: `docs/architecture.md` (frontend section),
     new `frontend/` directory (or reuse `PRPs/examples/Front_end_UI_example`
     as a starting point).
   - Dependencies: Phase 0 quickstart path defined.
   - Estimated effort: 1–2h.

2. **Scaffold Frontend Project**
   - Description: Create the frontend project structure, including build scripts
     (if needed), an entry HTML page, and minimal configuration for local dev
     (e.g., pointing to `http://localhost:8030` for the backend).
   - Files to modify/create: `frontend/` files (e.g., `index.html`,
     `src/main.tsx` or `main.js`), `README.md` (frontend section).
   - Dependencies: Task 1.
   - Estimated effort: 2–3h.

3. **Implement Chat UI Components**
   - Description: Build a simple chat interface with an input box, send button,
     and message history list. Include basic handling for loading state, errors,
     and scrolling. Start with non-streaming responses (simple JSON payloads).
   - Files to modify/create: `frontend/` components or scripts.
   - Dependencies: Task 2.
   - Estimated effort: 3–4h.

4. **Wire Frontend to `/chat` Backend Endpoint**
   - Description: Implement the network layer that sends user queries to
     `POST /chat` on the FastAPI app (`src/main.py`) and renders the returned
     `ChatResponse` (answer text and citations). Replace the Gemini-specific
     calls in `PRPs/examples/Front_end_UI_example/services/geminiService.ts`
     with a thin HTTP client targeting the local backend. Handle CORS if the
     frontend runs on a different origin.
   - Files to modify/create: `frontend/` API client code (or updated services
     in the adapted example), `src/main.py` (CORS, if needed),
     `README.md` (usage example).
   - Dependencies: Task 3; backend running locally.
   - Estimated effort: 2–3h.

5. **Add Basic Styling and Layout**
   - Description: Apply minimal styling (CSS or a small utility framework) to make
     the chat UI readable and usable; avoid heavy design systems. Ensure it works
     well on typical desktop browser sizes.
   - Files to modify/create: `frontend/` styles (CSS or similar).
   - Dependencies: Task 3.
   - Estimated effort: 2–3h.

6. **Frontend Configuration & Environment Docs**
   - Description: Document how to run the frontend in local development, how to
     configure the backend URL, and how to build and serve the assets in a
     production-like environment (e.g., via `uvicorn` + static files or a separate
     web server).
   - Files to modify/create: `README.md`, `docs/architecture.md`.
   - Dependencies: Tasks 2–5.
   - Estimated effort: 1–2h.

7. **Add Smoke Tests or Manual Checklist**
   - Description: Define a lightweight validation checklist (and/or frontend tests)
     to ensure the chat UI can send a query and display a response once the backend
     and database are configured correctly.
   - Files to modify/create: `README.md` (manual checklist),
     optional `frontend/tests/` or Cypress/Playwright config.
   - Dependencies: Tasks 3–4.
   - Estimated effort: 1–2h.

### Phase 2: Observability & Logging

1. **Inventory Current Ingestion Logging**
   - Description: Review existing logging for ingestion jobs, skills, and pipeline
     services to identify gaps in lifecycle coverage (start/end events, per-file
     progress, retries, and fallbacks).
   - Files to modify/create: `src/tools/ingestion_skill/service.py`,
     `src/rag_pipeline/pipeline.py`, `src/shared/logging.py`,
     `docs/post_ingestion_validation.md` (notes).
   - Dependencies: None; uses existing code and docs.
   - Estimated effort: 1–2h.

2. **Define Logging Fields and Conventions**
   - Description: Based on `PRPs/ai_docs/logging_guide.md`, define the core
     structured fields for ingestion events (e.g., `correlation_id`, `job_id`,
     `source`, `phase`, `duration_ms`, `attempt`, `backend`, `fallback_used`)
     and document them for reuse.
   - Files to modify/create: `src/shared/logging.py`,
     `docs/post_ingestion_validation.md`, `PRPs/ai_docs/logging_guide.md`
     (append notes if needed).
   - Dependencies: Task 1 completed; logging guide reviewed.
   - Estimated effort: 1–2h.

3. **Instrument Ingestion Skill Lifecycle Logs**
   - Description: Add structured logs around ingestion skill entry/exit, including
     input parameters, inferred context (e.g., target collection), and outcomes
     (success/failure, counts). Ensure logs respect privacy and do not leak
     sensitive data.
   - Files to modify/create: `src/tools/ingestion_skill/service.py`,
     `src/tools/ingestion_skill/tool.py`, `tests/tools/ingestion_skill/test_service.py`.
   - Dependencies: Task 2; existing tests passing.
   - Estimated effort: 2–3h.

4. **Instrument Pipeline-Level Ingestion Logs**
   - Description: Add detailed structured logging at key pipeline stages: initial
     request receipt, chunking start/end, embedding start/end, persistence start/end,
     and final success/failure. Ensure correlation IDs and job IDs propagate
     through each stage.
   - Files to modify/create: `src/rag_pipeline/pipeline.py`,
     `tests/rag_pipeline/test_pipeline_integration.py`.
   - Dependencies: Task 2; knowledge of pipeline stages.
   - Estimated effort: 3–4h.

5. **Add Docling Backend and Fallback Logs**
   - Description: Ensure the Docling chunker logs both successful conversions and
     fallback activations with clear reasons (unsupported format, conversion error),
     number of chunks produced, and whether the backend is disabled for the rest of
     the process.
   - Files to modify/create: `src/rag_pipeline/chunking/docling_chunker.py`,
     `tests/rag_pipeline/test_docling_chunker.py` (new or extended),
     `docs/post_ingestion_validation.md`.
   - Dependencies: Task 1; existing Docling tests; exception model understood.
   - Estimated effort: 2–3h.

6. **Improve Embedding Batch Logging**
   - Description: Extend embedding client and pipeline logs to capture embedding
     batch sizes, timing, and error conditions, including retries (to be implemented
     in Phase 2). Ensure logs clearly indicate which model and configuration were used.
   - Files to modify/create: `src/rag_pipeline/embeddings/qwen_client.py`,
     other embedding clients (if present), `src/rag_pipeline/pipeline.py`,
     `tests/rag_pipeline/test_embeddings_logging.py` (new).
   - Dependencies: Tasks 2 and 4.
   - Estimated effort: 2–3h.

7. **Standardize Log Context Helpers**
   - Description: Add small helper functions or context managers in
     `src/shared/logging.py` to attach common ingestion-related context (e.g.,
     `with_ingestion_context(logger, correlation_id=..., job_id=...)`) and ensure
     they are used consistently across tools and pipeline steps.
   - Files to modify/create: `src/shared/logging.py`,
     `tests/shared/test_logging_context.py` (new).
   - Dependencies: Tasks 2–4.
   - Estimated effort: 2–3h.

8. **Update Documentation with Logging Expectations**
   - Description: Document the new logging behavior, including example log entries,
     in `docs/rag_pipeline_ingestion.md` (or a new logging-focused section) so
     support engineers know what to look for in production logs.
   - Files to modify/create: `docs/rag_pipeline_ingestion.md`,
     `docs/post_ingestion_validation.md`.
   - Dependencies: Tasks 3–7.
   - Estimated effort: 1–2h.

9. **Add Tests for Logging Presence and Fields**
   - Description: Write unit or integration tests that assert expected log fields are
     emitted for key ingestion flows (using caplog or similar mechanisms) while
     keeping tests fast and deterministic.
   - Files to modify/create: `tests/tools/ingestion_skill/test_logging.py` (new),
     `tests/rag_pipeline/test_pipeline_logging.py` (new).
   - Dependencies: Tasks 3–7; testing guide reviewed.
   - Estimated effort: 3–4h.

10. **Review Observability Coverage and Gaps**
    - Description: After instrumentation, perform a review pass to confirm that all
      critical ingestion paths now emit structured logs with consistent fields and
      that the logging volume remains reasonable.
    - Files to modify/create: `docs/post_ingestion_validation.md` (updated
      observability checklist).
    - Dependencies: Tasks 1–9.
    - Estimated effort: 1–2h.

### Phase 3: Reliability & Retries

1. **Define Retry Policy Requirements**
   - Description: Identify which operations require retries (Supabase persistence,
     embedding HTTP calls, Docling conversions, maybe certain file system or network
     operations) and define acceptable retry budgets and backoff strategies per
     operation type.
   - Files to modify/create: `docs/rag_pipeline_ingestion.md` (retry section),
     `PRPs/ai_docs/logging_guide.md` (retry log fields, if needed).
   - Dependencies: Phase 1 observability tasks; stakeholders aligned on SLAs.
   - Estimated effort: 1–2h.

2. **Introduce Typed Retry Helper Utilities**
   - Description: Implement typed retry helper functions or small classes (e.g.,
     `RetryConfig`, `run_with_retries`) that encapsulate backoff logic, maximum
     attempts, and logging integration, avoiding any use of `Any` and keeping the
     API simple and explicit.
   - Files to modify/create: `src/utils/retry.py` (new),
     `tests/utils/test_retry.py` (new).
   - Dependencies: Task 1; adherence to KISS/YAGNI.
   - Estimated effort: 3–4h.

3. **Wire Retries into Supabase Store**
   - Description: Use the new retry utilities to wrap Supabase write operations, with
     careful handling of idempotency and clear logging for each attempt and final
     outcome.
   - Files to modify/create: `src/rag_pipeline/persistence/supabase_store.py`,
     `tests/rag_pipeline/test_supabase_retries.py` (new).
   - Dependencies: Task 2; understanding of Supabase semantics.
   - Estimated effort: 3–4h.

4. **Wire Retries into Embedding Clients**
   - Description: Apply retry behavior to external embedding client calls (e.g.,
     Qwen), backing off on transient failures (timeouts, rate limits) and clearly
     logging retries, but failing fast on invalid input or configuration errors.
   - Files to modify/create: `src/rag_pipeline/embeddings/qwen_client.py`,
     other embedding clients, `tests/rag_pipeline/test_embeddings_retries.py`.
   - Dependencies: Task 2; network error taxonomy defined.
   - Estimated effort: 3–4h.

5. **Consider Limited Retries for Docling Conversions**
   - Description: Evaluate whether Docling conversions benefit from a small number
     of retries (for transient environment issues) or whether failures are usually
     deterministic. If helpful, implement cautious retries with tight bounds and
     maintain the existing disable-on-failure behavior as the terminal fallback.
   - Files to modify/create: `src/rag_pipeline/chunking/docling_chunker.py`,
     `tests/rag_pipeline/test_docling_retries.py` (new).
   - Dependencies: Task 2; Docling failure modes understood.
   - Estimated effort: 2–3h.

6. **Add Configuration for Retry Policies**
   - Description: Expose retry settings (max attempts, backoff durations, enabled
     flags) through the existing configuration system (e.g., environment variables
     or config objects) and document the default values and tuning trade-offs.
   - Files to modify/create: `src/utils/config.py` or similar,
     `docs/rag_pipeline_ingestion.md`,
     `tests/utils/test_retry_config.py` (new).
   - Dependencies: Tasks 2–5; configuration patterns understood.
   - Estimated effort: 2–3h.

7. **Ensure Type-Safe Error Handling**
   - Description: Tighten type annotations for exceptions and error returns in retry
     paths, ensuring mypy remains happy and no implicit `Any` leaks are introduced by
     new utilities.
   - Files to modify/create: `src/utils/retry.py`,
     `src/rag_pipeline/persistence/supabase_store.py`,
     `src/rag_pipeline/embeddings/qwen_client.py`,
     `src/rag_pipeline/chunking/docling_chunker.py`.
   - Dependencies: Tasks 2–5; mypy config known.
   - Estimated effort: 1–2h.

8. **Update Tests for Reliability Behaviors**
   - Description: Extend unit and integration tests to cover retry scenarios,
     including success-after-retry, final failure after exhausting attempts, and
     logging expectations; ensure performance tests remain separate.
   - Files to modify/create: `tests/rag_pipeline/test_supabase_retries.py`,
     `tests/rag_pipeline/test_embeddings_retries.py`,
     `tests/rag_pipeline/test_docling_retries.py`.
   - Dependencies: Tasks 3–5; testing guide followed.
   - Estimated effort: 3–4h.

9. **Document Reliability Behavior and Runbooks**
   - Description: Document how retries behave in different pipeline components and
     create simple runbook notes for operators (e.g., what to check when retries
     spike, how to adjust configuration, when to disable features).
   - Files to modify/create: `docs/rag_pipeline_ingestion.md`,
     `docs/post_ingestion_validation.md`.
   - Dependencies: Tasks 1–8.
   - Estimated effort: 2–3h.

10. **Review Reliability Changes for KISS/YAGNI Compliance**
    - Description: Perform a final review to ensure retry logic remains simple,
      does not overcomplicate control flow, and covers only operations that benefit
      from retries; trim any overengineered pieces.
    - Files to modify/create: `docs/post_ingestion_validation.md` (updated risks
      and mitigation notes).
    - Dependencies: Tasks 1–9.
    - Estimated effort: 1–2h.

### Phase 4: CLI & Developer UX

1. **Review Current Ingestion CLI UX**
   - Description: Run the ingestion CLI and tool entrypoints to understand current
     ergonomics, argument structure, and error messages; collect concrete examples
     of confusing or missing feedback.
   - Files to modify/create: `src/tools/ingestion_skill/tool.py`,
     `docs/rag_pipeline_ingestion.md`.
   - Dependencies: Environment ready to run CLI.
   - Estimated effort: 1–2h.

2. **Clarify CLI Argument Semantics**
   - Description: Ensure CLI arguments are clearly typed and documented (e.g.,
     explicit flags for dry-run, target collections, batch sizes, overrides), and
     that invalid combinations fail fast with actionable messages.
   - Files to modify/create: `src/tools/ingestion_skill/tool.py`,
     `tests/tools/ingestion_skill/test_cli_args.py` (new).
   - Dependencies: Task 1; tool guide reviewed.
   - Estimated effort: 2–3h.

3. **Add Dry-Run and Safety Guards**
   - Description: Implement a dry-run mode (if not present) and/or confirmation
     prompts for operations that could trigger large-scale ingestion or destructive
     changes, ensuring behavior is testable and predictable.
   - Files to modify/create: `src/tools/ingestion_skill/tool.py`,
     `tests/tools/ingestion_skill/test_cli_safety.py` (new).
   - Dependencies: Task 2.
   - Estimated effort: 2–3h.

4. **Improve Progress and Summary Output**
   - Description: Enhance CLI output to provide incremental progress updates (e.g.,
     “processed N/M documents”, “created K chunks”, “fallback used X times”) and
     a final summary that aligns with structured logs.
   - Files to modify/create: `src/tools/ingestion_skill/service.py`,
     `src/tools/ingestion_skill/tool.py`,
     `tests/tools/ingestion_skill/test_cli_progress.py` (new).
   - Dependencies: Phase 1 logging tasks.
   - Estimated effort: 3–4h.

5. **Align CLI Help Text with Tool Guide**
   - Description: Ensure the CLI help text and Archon skill docstrings match the
     expectations in `PRPs/ai_docs/tool_guide.md`, including examples, performance
     notes, and guidance on when to use the tool.
   - Files to modify/create: `src/tools/ingestion_skill/tool.py`,
     `docs/archon_SKILL.md` (if present),
     `tests/tools/ingestion_skill/test_help_text.py` (new).
   - Dependencies: Task 1; tool guide reviewed.
   - Estimated effort: 2–3h.

6. **Document Developer Workflow for Ingestion**
   - Description: Update or create a “developer workflow” section that explains how
     to run ingestion locally, how to debug typical issues, and how to interpret
     logs and performance metrics.
   - Files to modify/create: `docs/rag_pipeline_ingestion.md`,
     `docs/post_ingestion_validation.md`.
   - Dependencies: Tasks 1–5.
   - Estimated effort: 2–3h.

7. **Add Tests for CLI Error Handling**
   - Description: Write tests that cover typical user mistakes (missing arguments,
     invalid path formats, unsupported options) and assert that errors are clear,
     actionable, and consistent.
   - Files to modify/create: `tests/tools/ingestion_skill/test_cli_errors.py` (new).
   - Dependencies: Tasks 2–3.
   - Estimated effort: 2–3h.

8. **Ensure Type Safety in CLI Layers**
   - Description: Audit the ingestion CLI and its supporting layers for missing
     annotations or implicit `Any` use; tighten types and ensure mypy remains
     satisfied.
   - Files to modify/create: `src/tools/ingestion_skill/tool.py`,
     `src/tools/ingestion_skill/service.py`.
   - Dependencies: Tasks 2–4; mypy config known.
   - Estimated effort: 1–2h.

9. **Refine CLI Exit Codes and Automation Integration**
   - Description: Standardize exit codes and ensure they are meaningful for
     automation (e.g., CI, scheduled ingestion jobs), documenting what each code
     means and when it occurs.
   - Files to modify/create: `src/tools/ingestion_skill/tool.py`,
     `docs/rag_pipeline_ingestion.md`.
   - Dependencies: Tasks 2–4.
   - Estimated effort: 1–2h.

10. **Review CLI & UX for Simplicity**
    - Description: Perform a final review to ensure CLI changes improved clarity
      without adding unnecessary complexity; adjust or remove features that do not
      align with KISS/YAGNI.
    - Files to modify/create: `docs/post_ingestion_validation.md`
      (updated UX notes).
    - Dependencies: Tasks 1–9.
    - Estimated effort: 1–2h.

### Phase 5: Performance Validation

1. **Inventory Existing Performance Tests**
   - Description: Review `tests/performance` to understand current coverage,
     assumptions, and dataset usage; identify missing scenarios related to Docling,
     retries, and large-scale ingestion.
   - Files to modify/create: `tests/performance/` files,
     `docs/post_ingestion_validation.md`.
   - Dependencies: Performance tests present; testing guide reviewed.
   - Estimated effort: 1–2h.

2. **Define Performance Objectives and Metrics**
   - Description: Agree on key performance targets (e.g., documents per minute,
     latency per batch, acceptable failure rates under load) and define the metrics
     that performance tests must capture.
   - Files to modify/create: `docs/rag_pipeline_ingestion.md`,
     `docs/post_ingestion_validation.md`.
   - Dependencies: Task 1; stakeholder input.
   - Estimated effort: 2–3h.

3. **Create Stable Performance Test Dataset**
   - Description: Build or curate a representative dataset for performance tests
     (mix of supported/unsupported formats, varying sizes) and ensure it is stable,
     versioned, and documented.
   - Files to modify/create: `tests/performance/data/` (new or updated),
     `tests/performance/conftest.py`,
     `docs/rag_pipeline_ingestion.md` (dataset notes).
   - Dependencies: Task 2.
   - Estimated effort: 3–4h.

4. **Add Performance Scenarios for Ingestion**
   - Description: Implement performance test cases that exercise bulk ingestion
     flows, capturing throughput, latency, and error behavior; ensure tests remain
     opt-in via markers.
   - Files to modify/create: `tests/performance/test_ingestion_performance.py` (new),
     `tests/performance/conftest.py`.
   - Dependencies: Task 3; ingestion CLI and pipeline stable.
   - Estimated effort: 3–5h.

5. **Add Performance Scenarios for Docling & Fallback**
   - Description: Add performance tests that stress Docling conversions with a mix
     of supported and unsupported documents, verifying that fallback behavior and
     retry logic perform acceptably under load.
   - Files to modify/create: `tests/performance/test_docling_performance.py` (new),
     `tests/performance/data/`.
   - Dependencies: Task 3; Phase 2 retries implemented.
   - Estimated effort: 3–5h.

6. **Add Performance Scenarios for Embeddings & Persistence**
   - Description: Implement performance tests targeting embedding throughput and
     Supabase persistence, tracking batch sizes, latency, and error rates.
   - Files to modify/create: `tests/performance/test_embeddings_performance.py` (new),
     `tests/performance/test_persistence_performance.py` (new).
   - Dependencies: Task 3; Phase 2 retries integrated.
   - Estimated effort: 3–5h.

7. **Wire Performance Metrics into Logs**
   - Description: Ensure performance tests log key metrics in a consistent format
     so results can be compared over time and captured in validation notes.
   - Files to modify/create: `tests/performance` files,
     `docs/post_ingestion_validation.md`.
   - Dependencies: Phase 1 logging tasks.
   - Estimated effort: 2–3h.

8. **Document How to Run Performance Suite**
   - Description: Add clear instructions for running the performance suite,
     including hardware expectations, markers to use, and how to interpret results.
   - Files to modify/create: `PRPs/ai_docs/testing_guide.md`,
     `docs/rag_pipeline_ingestion.md`.
   - Dependencies: Tasks 4–7.
   - Estimated effort: 1–2h.

9. **Capture Baseline Performance Results**
   - Description: Run the performance suite on representative hardware and record
     baseline metrics in `docs/post_ingestion_validation.md`, including any known
     bottlenecks and future optimization candidates.
   - Files to modify/create: `docs/post_ingestion_validation.md`.
   - Dependencies: Tasks 4–8; hardware access.
   - Estimated effort: 2–4h.

10. **Review Performance Outcomes and Next Steps**
    - Description: Evaluate whether performance meets the defined objectives; if
      not, capture concrete next steps (e.g., batching adjustments, parallelism,
      model or database tuning) as future work rather than implementing them all
      in this hardening phase.
    - Files to modify/create: `docs/post_ingestion_validation.md`,
      new PRP request file if needed (e.g., for deeper performance optimization).
    - Dependencies: Tasks 2–9.
    - Estimated effort: 1–2h.

## Codebase Integration Points

### Files to Modify
- `src/tools/ingestion_skill/tool.py` - Improve CLI UX, arguments, safety, help text,
  and type annotations; align docstrings with tool guide; add progress and error
  reporting.
- `src/tools/ingestion_skill/service.py` - Enhance structured logging for ingestion
  flows, progress reporting, and error handling; integrate with retry and context
  helpers.
- `src/rag_pipeline/pipeline.py` - Add pipeline-level logging, retries, and metrics;
  ensure correlation IDs and job IDs propagate; integrate with new retry utilities.
- `src/rag_pipeline/chunking/docling_chunker.py` - Refine Docling logging,
  retries (if adopted), and re-enable behavior for mixed workloads; maintain clear
  fallback semantics.
- `src/rag_pipeline/embeddings/qwen_client.py` - Introduce retries, structured
  logging, and configuration for embedding calls; ensure types remain strict.
- `src/rag_pipeline/persistence/supabase_store.py` - Add retry-aware persistence
  calls and logging; ensure type-safe interaction with Supabase APIs.
- `src/shared/logging.py` - Extend logging helpers to support ingestion context,
  structured fields, and convenience wrappers without breaking existing behavior.
- `src/utils/retry.py` (new) - Provide typed retry helpers and configurations for
  reuse across the pipeline.
- `src/utils/config.py` or equivalent config modules - Expose configuration for
  retry policies and possibly feature flags for Docling behavior.
- `docs/rag_pipeline_ingestion.md` - Update documentation for logging, retries,
  CLI usage, and performance testing.
- `docs/post_ingestion_validation.md` - Extend validation summary with Phase 4
  efforts, performance baselines, and remaining risks.
- `PRPs/ai_docs/logging_guide.md` - Clarify ingestion logging patterns and fields.
- `PRPs/ai_docs/testing_guide.md` - Document performance test usage and markers.

### New Files to Create
- `src/utils/retry.py` - Typed retry utility module encapsulating retry policies and
  backoff logic.
- `tests/utils/test_retry.py` - Unit tests for retry utilities to ensure correctness
  and type safety.
- `tests/shared/test_logging_context.py` - Tests for new logging context helpers.
- `tests/tools/ingestion_skill/test_service.py` - Tests for ingestion service logging
  and progress behavior (if not already present).
- `tests/tools/ingestion_skill/test_logging.py` - Tests verifying that logging fields
  are emitted for ingestion flows.
- `tests/tools/ingestion_skill/test_cli_args.py` - Tests for argument parsing and
  validation.
- `tests/tools/ingestion_skill/test_cli_safety.py` - Tests for dry-run and safety
  guard behavior.
- `tests/tools/ingestion_skill/test_cli_progress.py` - Tests for progress and summary
  output.
- `tests/tools/ingestion_skill/test_help_text.py` - Tests to keep help text aligned
  with expectations.
- `tests/tools/ingestion_skill/test_cli_errors.py` - Tests covering typical CLI
  error cases.
- `tests/rag_pipeline/test_pipeline_logging.py` - Integration tests asserting pipeline
  logging fields and event ordering.
- `tests/rag_pipeline/test_embeddings_logging.py` - Tests verifying embedding batch
  logging.
- `tests/rag_pipeline/test_supabase_retries.py` - Tests for Supabase retry behavior.
- `tests/rag_pipeline/test_embeddings_retries.py` - Tests for embedding retry
  behavior.
- `tests/rag_pipeline/test_docling_chunker.py` - Tests for Docling logging and
  disable behavior; extend or create as needed.
- `tests/rag_pipeline/test_docling_retries.py` - Tests for Docling retry behavior
  if retries are implemented.
- `tests/performance/conftest.py` - Shared fixtures and configuration for
  performance tests.
- `tests/performance/test_ingestion_performance.py` - Performance tests for ingestion
  throughput and latency.
- `tests/performance/test_docling_performance.py` - Performance tests for Docling
  and fallback behavior.
- `tests/performance/test_embeddings_performance.py` - Performance tests for
  embedding throughput.
- `tests/performance/test_persistence_performance.py` - Performance tests for
  persistence operations.
- `tests/performance/data/` - Directory holding stable, representative test data.

### Existing Patterns to Follow
- Reuse the vertical slice pattern (tool.py, schemas.py, service.py) seen in
  `src/tools/ingestion_skill` for any new tools or utilities related to ingestion
  and performance.
- Follow the structured logging patterns already present in `src/shared/logging.py`
  and extended in recent ingestion work; avoid inventing new logging styles.
- Mirror the testing style and fixtures in `tests/rag_pipeline/test_pipeline_integration.py`
  when adding new integration tests for retries and logging.
- Follow the unit test conventions in existing `tests/tools` modules for new
  ingestion CLI tests.
- Maintain strict typing as in `src/rag_pipeline/persistence/supabase_store.py`
  and `src/rag_pipeline/embeddings/qwen_client.py`.

## Technical Design

### Architecture Diagram (Conceptual)
```
[CLI / Archon Skill]
        |
        v
[Ingestion Service] --(structured logs, correlation_id)--> [Logger]
        |
        v
[Pipeline Orchestrator]
        |
        +--> [Chunking (Docling + Fallback)]
        |          |
        |          +--(retries, logs)--> [Logger]
        |
        +--> [Embeddings Client]
        |          |
        |          +--(retries, logs, metrics)--> [Logger]
        |
        +--> [Persistence (Supabase Store)]
                   |
                   +--(retries, logs, metrics)--> [Logger]

[Performance Tests] exercise the full pipeline and record metrics.
```

### Data Flow
- Ingestion requests originate from the CLI or Archon skill, where arguments are
  parsed, validated, and logged with initial context.
- The ingestion service builds a `PipelineServices` configuration, wiring in
  logging, retry policies, and configuration objects, then passes control to the
  core pipeline.
- The pipeline orchestrates chunking, embedding, and persistence; each stage emits
  structured logs, including correlation IDs, job IDs, and duration metrics.
- The Docling chunker attempts conversions; on failures, it logs the error, may
  perform limited retries, and eventually triggers fallback behavior, which is also
  logged with counts and reasons.
- Embedding clients perform batched calls to external services, with retries on
  transient failures; each attempt is logged with batch size, timing, and error
  state.
- Persistence layers (Supabase store) write chunks and metadata, with retries and
  structured logging of queries and failures.
- Performance tests drive synthetic or recorded datasets through the pipeline,
  capturing metrics that are attached to documentation and used to guide future
  optimization work.

### API Endpoints (If Applicable)
- `POST /ingestion/jobs` - Kick off ingestion jobs with specified parameters
  (collections, filters, concurrency); logs job creation and returns a job ID.
- `GET /ingestion/jobs/{job_id}` - Retrieve the status and summary of ingestion
  jobs, including counts, durations, and error summaries.
- `POST /ingestion/jobs/{job_id}/retry` - Optional endpoint to trigger a retry or
  resume behavior for failed jobs, leveraging the same retry utilities.

If these endpoints are not yet implemented, they can be considered future work and
are not required for the core Phase 4 hardening effort.

## Dependencies and Libraries
- Existing logging infrastructure and `src/shared/logging.py` helpers for structured
  logs and logger factories.
- Pytest for unit, integration, and performance tests, with markers controlling
  which suites run by default.
- Mypy for type checking, ensuring that new utilities and pipeline changes remain
  fully annotated and type-safe.
- Ruff for linting, enforcing style and preventing unused imports or other common
  issues.
- Supabase Python client (or low-level HTTP layer in use) for persistence; retries
  will wrap this layer without changing its API.
- HTTP client(s) used by embedding clients; retries will wrap their calls.
- Docling and any PDF/Office parsing libraries already in use; hardening focuses on
  logging and fallback behavior rather than swapping parsers.

## Testing Strategy
- Unit tests:
  - Focus on retry helpers, logging context utilities, and CLI argument parsing.
  - Cover success, failure, and edge cases for each new helper function.
- Integration tests:
  - Validate end-to-end ingestion flows with retries enabled, ensuring that logs
    contain expected fields and that Docling fallback behavior is correct.
  - Cover embedding and persistence flows with simulated transient failures.
- Performance tests:
  - Run only with the performance marker on suitable hardware.
  - Use stable datasets and capture throughput and latency metrics for ingestion,
    Docling, embeddings, and persistence.
- Regression tests:
  - Capture bugfixes or edge cases uncovered during Phase 4 work as dedicated
    tests to prevent regressions.
- Static analysis:
  - Continue running `ruff check src tests`, `mypy src`, and `pytest tests -m "not performance"`
    as the default validation suite; add instructions for running performance tests
    explicitly.

## Success Criteria
- [ ] Ingestion logging clearly describes job lifecycle events with consistent
      structured fields (correlation_id, job_id, source, phase, duration_ms).
- [ ] Retries are implemented for the right operations (Supabase, embeddings,
      Docling where justified) using simple, well-typed utilities.
- [ ] CLI UX improvements make ingestion safer and more discoverable, with clear
      help text, progress output, and error messages.
- [ ] Performance tests run reliably on supported hardware and produce baseline
      metrics for ingestion, Docling, embeddings, and persistence.
- [ ] All new code passes ruff, mypy, and pytest (non-performance) with no
      regressions; performance tests remain opt-in.
- [ ] Documentation clearly explains logging fields, retry behavior, CLI usage,
      and performance testing procedures.
- [ ] Changes adhere to KISS and YAGNI, avoiding unnecessary abstraction or
      premature optimization.

## Notes and Considerations
- Some Phase 4 items (especially performance tuning and advanced retry strategies)
  may expose deeper bottlenecks or design questions; this plan focuses on making
  the system observable and robust enough to understand those issues rather than
  solving all performance problems immediately.
- Docling re-enable behavior should be introduced cautiously; it may be sufficient
  to provide configuration flags and monitoring before building more complex
  automatic re-enable logic.
- Retries must be implemented with careful attention to idempotency and side
  effects, especially around database writes and downstream systems.
- CLI and tool changes should be rolled out with clear documentation updates to
  avoid surprising existing users.
- Always keep test coverage close to new behavior; avoid adding features without
  accompanying tests and documentation.

---
*This plan is ready for execution with `/execute-plan`*
