# Implementation Plan: Grounded Chat Validation, Frontend, and Hardening

## Overview
This plan assumes that the initial wiring for retrieval + LLM integration is
implemented in the backend and covered by unit/API tests, as captured in
`rag_retrieval_llm_integration_plan.md`. The focus now shifts to:

- Validating `/chat` behaviour end-to-end against a real Postgres/PGVector
  instance and live (or stubbed) LLM endpoint.
- Tightening observability for retrieval and generation so regressions are
  debuggable via logs and Archon.
- Aligning the React/Vite frontend example with grounded `/chat` responses,
  including citation display and error handling.
- Hardening docs, checklists, and validator-agent workflows so developers can
  reliably stand up and evolve grounded chat.

This document is intended for use with `.codex/commands/execute-plan.md`:
each implementation item should have a corresponding Archon task in the
“End-to-End Developer & User Experience” project and be driven through
`todo → in_progress → review → done` with validator-agent checkpoints.

## Assumptions
- `src/agent/agent.py` now calls a retriever + `LLMClient` and returns
  structured citations.
- `src/rag_pipeline/persistence/supabase_store.py` exposes a retrieval helper
  over `rag.match_chunks` and ingestion is already populating the database.
- `src/shared/config.py` includes environment-based settings for
  `DATABASE_URL`, `RAG_DATABASE_URL`, embedding/LLM models, and retrieval
  tuning (`RETRIEVAL_TOP_K`, `RETRIEVAL_MIN_SCORE`).
- Tests under `tests/agent`, `tests/test_main.py`, and
  `tests/rag_pipeline/test_retrieval.py` exist and pass once dependencies are
  installed (`pytest`, `psycopg`, etc.).
- Archon is running at `http://localhost:8181` and already has a project
  representing this work:
  `End-to-End Developer & User Experience`
  (`project_id=fbe94a2b-1226-4e38-b094-f3a66cdedbb2`).

If any of these assumptions are not met, adjust the sequencing or create
bridge tasks in Archon before proceeding.

## Phase 1: End-to-End Backend Validation

1. **Spin Up Test Database and Run Smoke Ingestion**
   - Description: Provision a local Postgres/PGVector instance (or Supabase
     project), apply `PRPs/examples/rag_pipeline_docling_supabase.sql`, and run
     the ingestion CLI against a small fixture corpus (5–10 short docs) to
     confirm chunks populate `rag.sources` / `rag.chunks`.
   - Files to use/modify:
     - `PRPs/examples/rag_pipeline_docling_supabase.sql`
     - `src/rag_pipeline/cli.py`
     - `docs/rag_pipeline_ingestion.md` (to note any deviations)
   - Validation:
     - Manual: `select count(*) from rag.chunks;` > 0.
     - Log review: ingestion logs show successful completion.
   - Archon:
     - Create task “Run smoke ingestion with fixture corpus” and track DB
       connection issues, missing extensions, or schema drift.

2. **Exercise `/chat` Against Real Data**
   - Description: With ingestion complete, hit `/chat` using curl or
     `httpie` for several queries that should match the fixture corpus. Verify
     that answers reference ingested content and include citations.
   - Files to use/modify:
     - `src/main.py`
     - `src/agent/agent.py`
     - `docs/post_ingestion_validation.md` (capture example requests/responses)
   - Validation:
     - Responses mention document names / sources present in the corpus.
     - Citations list is non-empty when relevant context exists.
   - Archon:
     - Create task “Run `/chat` E2E smoke tests” and attach request/response
       samples as task comments.

3. **Confirm Retrieval Tuning Knobs Work**
   - Description: Vary `RETRIEVAL_TOP_K` and `RETRIEVAL_MIN_SCORE` in
     `.env` and confirm that the number of retrieved chunks and citation
     density in answers change as expected.
   - Files to use/modify:
     - `.env` / `.env.example`
     - `src/shared/config.py`
   - Validation:
     - With low `TOP_K` and higher `MIN_SCORE`, answers reference fewer,
       higher-scoring sources.
     - With higher `TOP_K`, more citations appear, or retrieval logs show
       increased `results_count`.
   - Archon:
     - Create task “Validate retrieval tuning via env vars”.

4. **Harden Error Handling for Missing/Bad Configuration**
   - Description: Intentionally misconfigure the database URL and LLM
     endpoint (e.g., invalid host, missing API key) and confirm that:
     - `/chat` degrades gracefully (clear error or fallback message).
     - Logs contain structured events describing the failure cause.
   - Files to modify:
     - `src/agent/agent.py` (if additional guards or user-facing messages
       are needed).
     - `src/agent/llm_client.py` (for clearer fallback text).
     - `docs/rag_pipeline_ingestion.md` and `README.md` (troubleshooting).
   - Validation:
     - No uncaught exceptions bubble to FastAPI stack traces for
       configuration issues.
   - Archon:
     - Create task “Harden config error handling for `/chat`”.

## Phase 2: Observability and Log Schema

1. **Define Retrieval and LLM Log Schema**
   - Description: Catalogue the structured log events emitted during
     retrieval and LLM calls (e.g., `retrieval_started`, `retrieval_completed`,
     `llm_call_completed`, `llm_call_failed`) and define a small schema table
     documenting mandatory fields and example values.
   - Files to modify:
     - `docs/post_ingestion_validation.md` (add log schema table).
     - `PRPs/ai_docs/logging_guide.md` (extend with retrieval/LLM events).
   - Validation:
     - Run `/chat` and confirm emitted logs adhere to the documented schema.
   - Archon:
     - Link this work to any existing “log schema” tasks, or create a new one.

2. **Propagate Correlation IDs Through Chat Flow**
   - Description: Ensure that when a request enters `/chat`, a
     `correlation_id` is generated (or reused) and passed through to
     retrieval/LLM logs so engineers can trace a single user query end-to-end.
   - Files to modify:
     - `src/main.py` (generate/propagate correlation ID into the agent call).
     - `src/agent/agent.py` (include correlation ID in log fields).
     - Optionally `src/shared/logging.py` (helpers for per-request context).
   - Validation:
     - Log inspection shows the same `correlation_id` in `chat_started`,
       `retrieval_*`, and `llm_*` events for a single HTTP request.
   - Archon:
     - Create task “Add correlation_id propagation for `/chat`”.

3. **Document Log-Based Troubleshooting Scenarios**
   - Description: Extend existing documentation with examples of how to use
     logs to debug common issues:
     - No chunks returned for a query.
     - LLM timeouts or repeated retries.
     - DB failures or slow queries in `match_chunks`.
   - Files to modify:
     - `docs/rag_pipeline_ingestion.md`
     - `README.md` (short troubleshooting section that links deeper docs).
   - Validation:
     - Walk through at least one simulated failure and verify the doc steps
       match actual logs.
   - Archon:
     - Create task “Document log-based troubleshooting for grounded chat”.

## Phase 3: Frontend Integration and UX

1. **Align Frontend Chat Types with Backend Schemas**
   - Description: Ensure the frontend example’s TypeScript types for chat
     requests/responses match `ChatRequest` / `ChatResponse` / `Citation` in
     `src/agent/agent.py`. This avoids drift as the backend evolves.
   - Files to modify:
     - `PRPs/examples/Front_end_UI_example/types.ts` (or equivalent).
     - `PRPs/examples/Front_end_UI_example/services/*`.
   - Validation:
     - Type-checking in the frontend passes, and the network layer matches
       the backend JSON shape.
   - Archon:
     - Use or create the “Align frontend chat contract” task.

2. **Display Citations in the Chat UI**
   - Description: Update message rendering components so each assistant
     message can show linked citations (source name + optional score). When no
     citations are present, the UI should still render gracefully.
   - Files to modify:
     - `PRPs/examples/Front_end_UI_example/components/*` (chat bubble / message
       components).
     - `PRPs/examples/Front_end_UI_example/hooks/useChatManager.ts`.
   - Validation:
     - After sending a query that triggers retrieval, the UI displays
       citations matching the backend response.
   - Archon:
     - Tie into the existing “Handle citation display in UI” task
       (`f8d9c6d4-8b5f-4e3a-8869-244d6e82cc65`) if present.

3. **Frontend Error and Loading States for `/chat`**
   - Description: Ensure the frontend surfaces network errors, timeouts, and
     backend fallback messages in a user-friendly way (e.g., “Backend
     unreachable” vs. “LLM temporarily unavailable”), and shows a clear loading
     state while waiting for responses.
   - Files to modify:
     - `PRPs/examples/Front_end_UI_example/services/localChatService.ts`
       (or equivalent).
     - `PRPs/examples/Front_end_UI_example/components/*` (status banners / toasts).
   - Validation:
     - Simulate backend offline and verify the UI error state.
     - Simulate slow responses and verify loading indicators display.
   - Archon:
     - Create or update “Frontend UX polish for chat interactions”.

4. **Document Frontend Setup and Expected Behaviour**
   - Description: Update both the root `README.md` and the frontend example
     README to describe:
     - How to configure `VITE_BACKEND_URL`.
     - How to switch between providers (local FastAPI vs. Gemini, if still
       supported).
     - What grounded behaviour / citations the UI should show when everything
       is working.
   - Files to modify:
     - `README.md`
     - `PRPs/examples/Front_end_UI_example/README.md`
   - Validation:
     - A new developer can follow the steps to start the UI and see grounded
       answers from `/chat`.
   - Archon:
     - Attach screenshots or short screencasts as task artifacts if helpful.

## Phase 4: Validator Agent and Regression Safety Nets

1. **Define Validator Agent Playbook for `/chat`**
   - Description: Write a short playbook for using the validator agent to
     sanity-check grounded responses after code changes (e.g., run a curated
     set of queries and assert that answers mention expected sources).
   - Files to modify:
     - `docs/post_ingestion_validation.md`
     - `PRPs/requests/next_steps_validation_plan.md` (cross-reference).
   - Validation:
     - The validator agent can be triggered from Archon with a description
       of recent changes and a list of queries, and it produces a clear
       pass/fail report.
   - Archon:
     - Create task “Define validator agent workflow for `/chat`”.

2. **Add Regression Queries for Key Scenarios**
   - Description: Capture a small set of canonical queries and expected
     qualitative behaviours (e.g., “doc-specific question”, “out-of-scope
     question”, “ambiguous query”) that can be reused in regression checks.
   - Files to add/modify:
     - `docs/chat_regression_scenarios.md` (new).
     - Optionally serialize JSON fixtures for automated checks.
   - Validation:
     - Manual runs show stable, grounded behaviour for these scenarios.
   - Archon:
     - Tie into “Update API tests for grounded responses”
       (`386aca74-e85d-41cd-97e8-8abc8924089c`) or create a follow-up task.

3. **Wire Regression Scenarios into Tests (Optional Stretch)**
   - Description: Where practical, encode a subset of regression scenarios as
     automated tests (e.g., using a local in-memory store or fixtures) that
     assert the shape of responses and presence of citations, without relying
     on external LLM endpoints.
   - Files to modify:
     - `tests/test_main.py`
     - `tests/agent/test_agent.py`
   - Validation:
     - `pytest -m "not performance"` passes and catches obvious regressions
       in response structure.
   - Archon:
     - Create stretch task “Automate grounded chat regression scenarios”.

## Phase 5: Performance and Fine-Tuned Embeddings (Optional)

1. **Collect Baseline Latency Metrics**
   - Description: Measure end-to-end latency for `/chat` across several
     queries and document the breakdown (retrieval vs. LLM time) using logs
     and simple timing scripts.
   - Files to modify:
     - `docs/performance/baseline_grounded_chat.md` (new).
     - `docs/post_ingestion_validation.md` (summary).
   - Validation:
     - Baseline numbers are recorded and can be compared after changes.
   - Archon:
     - Reference relevant performance tasks in `phase4_hardening_and_performance_plan.md`.

2. **Plan Fine-Tuned Embeddings Integration for Chat Retrieval**
   - Description: Based on `PRPs/ai_docs/fine-tuned-embeddings.md`, outline
     the minimal changes needed so the chat-time retriever can toggle between
     base and fine-tuned embedding models, including configuration flags and
     regression tests that compare recall@k.
   - Files to modify:
     - `PRPs/ai_docs/fine-tuned-embeddings.md` (if clarifications are needed).
     - `src/shared/config.py` (flags / model identifiers).
     - `docs/rag_pipeline_ingestion.md` (document toggles).
   - Validation:
     - Feature is still optional and behind configuration; default flow remains
       simple and type-safe.
   - Archon:
     - Align with existing fine-tuning tasks in the Docling pipeline project.

## Execution Notes for `/execute-plan`

- When running `.codex/commands/execute-plan.md` with this plan:
  - Use the existing Archon project
    `End-to-End Developer & User Experience` unless instructed otherwise.
  - Create a task for each numbered item under Phases 1–5 before starting
    implementation.
  - Maintain only one `in_progress` task at a time, moving tasks through
    `todo → in_progress → review → done` according to the command’s workflow.
  - After completing each phase, trigger the validator agent with a summary of
    modified files and behaviours; attach its output to the relevant Archon
    tasks.
- Keep this plan and `rag_retrieval_llm_integration_plan.md` in sync with
  actual code and documentation changes, updating them when tasks are completed
  or descoped.

