# Implementation Plan: End-to-End Developer & User Experience

## Overview
This plan describes how to turn the current Local RAG AI Assistant foundation
into a cohesive, easy-to-run product experience for both developers and end
users. It focuses on:

- Making the repository truly “clone → configure → run” via a single, reliable
  quickstart flow.
- Providing a simple, modern frontend chat UI wired to the local FastAPI
  backend instead of a third-party hosted model.
- Fully connecting the ingestion pipeline, embeddings, and database to the
  agent so that chat responses are grounded in the user’s own documents.
- Ensuring configuration, logging, and tests remain type-safe and aligned with
  the AGENTS.md principles (KISS, YAGNI, strict mypy).

The plan assumes:

- Phases 1–3 of `PRPs/requests/rag_pipeline_remaining_work.md` and the
  `next_steps_validation_plan.md` have been implemented and validated, with
  tooling (ruff, mypy, pytest) passing as captured in
  `docs/post_ingestion_validation.md`.
- The current `/chat` endpoint and `RAGAgent` provide placeholder answers but
  are structurally ready to be wired into the RAG pipeline.
- A working frontend chat UI example exists in
  `PRPs/examples/Front_end_UI_example`, currently pointing at the Gemini API.

This document is written to be executable via `/execute-plan` and is organized
into phased tasks that can be delivered in small, reviewable PRs.

## Requirements Summary
- Provide a single, opinionated quickstart path in `README.md` so that new
  users can:
  - Clone the repo.
  - Create a Python environment and install dependencies.
  - Configure the database, Qwen embedding API, and core environment variables.
  - Ingest their own documents.
  - Start the backend and send test queries via curl or a UI.
- Adapt the existing React/Vite UI in `PRPs/examples/Front_end_UI_example` to
  use the local FastAPI `/chat` endpoint rather than Gemini, with minimal
  configuration for backend URL and environment.
- Wire the RAG pipeline into `RAGAgent.chat` so chat responses use:
  - The ingestion pipeline’s chunk and embedding storage in PostgreSQL/PGVector.
  - A retrieval step that queries the database.
  - A generation step using the configured LLM model, with citations.
- Keep all changes type-safe with full annotations, obeying strict mypy and
  existing documentation/testing conventions.
- Preserve earlier plans’ sequencing: this work should build on, not replace,
  the ingestion, tooling, and validation tasks already defined.

## Research Findings

### Best Practices
- For a repository intended to be cloned by multiple developers, the top-level
  README should provide a complete, linear path from “git clone” to “first
  successful query,” including environment setup, configuration, and validation.
- Frontend integrations with backend AI APIs should:
  - Use a small client wrapper to centralize base URL and error handling.
  - Support local development (different ports/origins) via CORS and configurable
    environment variables.
  - Fail gracefully when the backend is unreachable or misconfigured.
- RAG agent implementations benefit from:
  - A thin `RAGAgent` façade that wires together retrieval and generation
    services, keeping configuration injection and logging centralized.
  - Explicit schema types (e.g., `ChatRequest`, `ChatResponse`, `Citation`) so
    frontend and backend stay in sync.
  - Clear separation between ingestion-time and query-time concerns.
- Configuration should be:
  - Centralized in small, typed modules (`src/shared/config.py`,
    `src/rag_pipeline/config.py`).
  - Driven by environment variables with sensible defaults for development.
  - Documented in README and cross-linked from deeper docs.
- Testing strategies for an end-to-end RAG system should include:
  - Fast unit tests for config, pipeline components, and the agent facade.
  - Integration tests that exercise ingestion + retrieval in a minimal setup.
  - Optional performance tests marked separately (already present in this repo).

### Reference Implementations
- `PRPs/requests/rag_pipeline_remaining_work.md`:
  - Defines the ingestion pipeline phases, embedding client, persistence, CLI,
    and Archon ingestion skill. This plan builds on those foundations instead of
    redefining them.
- `PRPs/requests/next_steps_validation_plan.md`:
  - Describes the validation and tooling readiness work that established the
    current “clean” state (ruff, mypy, pytest passing).
- `docs/post_ingestion_validation.md`:
  - Summarizes what has already been validated and notes remaining follow-ups,
    including performance tests and optional hardening.
- `README.md`:
  - Now contains a Quickstart section that walks through environment creation,
    database setup, ingestion, and backend API usage.
- `docs/architecture.md`:
  - Provides a high-level architecture diagram and setup checklist, and now
    includes a “Frontend user interface” section that references the frontend
    example.
- `docs/rag_pipeline_ingestion.md`:
  - Documents ingestion configuration, environment variables, CLI usage, and
    Supabase/PostgreSQL setup; it now links back to the README Quickstart.
- `PRPs/examples/Front_end_UI_example`:
  - React/Vite app with a rich chat UI that currently calls a Gemini service.
    Its structure (App, ChatHistory, ChatArea, hooks, services) can be reused by
    swapping the network layer to the local `/chat` endpoint.
- `src/main.py`:
  - FastAPI app exposing `/health` and `/chat` and delegating to `RAGAgent`.
- `src/agent/agent.py`:
  - Defines `ChatRequest`, `ChatResponse`, `Citation`, and the `RAGAgent`
    facade, including tools (ingestion_skill) and placeholder `chat` logic.
- `src/rag_pipeline/config.py`, `src/rag_pipeline/pipeline.py`,
  `src/rag_pipeline/embeddings/qwen_client.py`,
  `src/rag_pipeline/persistence/supabase_store.py`:
  - Provide the ingestion configuration, orchestration, embedding client, and
    persistence layer that should back chat-time retrieval and grounding.
- `tests/test_main.py` and `tests/agent/test_agent.py`:
  - Show how the API and agent are currently exercised in tests.

### Technology Decisions
- Continue using FastAPI and Uvicorn for the backend API:
  - `/chat` remains the main endpoint for the UI and any programmatic clients.
- Use the existing React/Vite example as the base for the frontend:
  - Reduces setup friction for users familiar with modern frontend tooling.
  - Keeps HTML/JS bundling concerns isolated from the Python backend.
- Stay with Qwen-based models for embeddings and the LLM:
  - Leverage existing configuration and documentation.
  - Keep model IDs and API keys configured via environment variables.
- For retrieval:
  - Use PostgreSQL/PGVector and the schema defined in
    `PRPs/examples/rag_pipeline_docling_supabase.sql`.
  - Implement retrieval functions in the pipeline or a dedicated retrieval
    module that the agent can call at query time.
- Avoid introducing new major dependencies unless necessary:
  - Reuse existing libraries for HTTP, database, and configuration.
  - Maintain strict type checking and style (mypy, ruff).

## Implementation Tasks

### Phase 1: Solidify the Quickstart & Documentation

1. **Align Quickstart with Current Code Paths**
   - Description: Review the updated Quickstart in `README.md` and ensure the
     steps exactly match how the code is meant to be run today (env creation,
     `requirements.txt`, RAG_DATABASE_URL, Qwen API keys, CLI and backend).
   - Files to modify/create: `README.md`.
   - Dependencies: Existing Quickstart written; code paths stable.
   - Estimated effort: 1–2h.

2. **Clarify Required vs. Optional Dependencies**
   - Description: Explicitly mark which dependencies are required to reach the
     “first question answered” milestone (PostgreSQL, PGVector, Qwen embedding
     API key) vs. optional (Docling, fine-tuned embeddings, performance tests).
   - Files to modify/create: `README.md`, `docs/architecture.md`.
   - Dependencies: Task 1.
   - Estimated effort: 1–2h.

3. **Document End-to-End Flow in Architecture Doc**
   - Description: Add a concise sequence to `docs/architecture.md` that mirrors
     the Quickstart: clone → configure → ingest → query via `/chat` and,
     optionally, via the frontend example.
   - Files to modify/create: `docs/architecture.md`.
   - Dependencies: Quickstart finalized.
   - Estimated effort: 1–2h.

4. **Cross-Link Ingestion and Agent Docs**
   - Description: Ensure `docs/rag_pipeline_ingestion.md` links to the Quickstart
     for initial setup, and add a pointer from the agent/architecture docs back
     to the ingestion guide so users can navigate between them naturally.
   - Files to modify/create: `docs/rag_pipeline_ingestion.md`,
     `docs/architecture.md`.
   - Dependencies: Tasks 1–3.
   - Estimated effort: 1–2h.

5. **Add a “What You Get After Setup” Section**
   - Description: Briefly describe what a user can expect after following the
     Quickstart (health checks passing, ingestion logs, placeholder chat working,
     and the path to grounded answers once retrieval is wired).
   - Files to modify/create: `README.md`.
   - Dependencies: Tasks 1–4.
   - Estimated effort: 1–2h.

6. **Ensure Docs Reflect Placeholder vs. Fully Wired State**
   - Description: Clearly label which parts of the system are currently
     placeholders (e.g., `/chat` answer content) and which are fully functional
     (ingestion, logging, tests). This avoids confusing early adopters.
   - Files to modify/create: `README.md`, `docs/architecture.md`.
   - Dependencies: Tasks 1–5.
   - Estimated effort: 1–2h.

### Phase 2: Adapt the Frontend UI to the Local Backend

1. **Audit the Frontend Example**
   - Description: Inspect `PRPs/examples/Front_end_UI_example` to understand its
     component tree, hooks, and the `geminiService.ts` API layer. Identify the
     minimal set of changes needed to swap Gemini for the local `/chat` endpoint.
   - Files to review/modify: `PRPs/examples/Front_end_UI_example/App.tsx`,
     `PRPs/examples/Front_end_UI_example/index.tsx`,
     `PRPs/examples/Front_end_UI_example/services/geminiService.ts`,
     `PRPs/examples/Front_end_UI_example/hooks/*`.
   - Dependencies: Backend `/chat` endpoint available.
   - Estimated effort: 1–2h.

2. **Design a Backend-Agnostic Chat Service Interface**
   - Description: Introduce an interface or simple abstraction in the frontend
     for “send chat message and receive response” so that the implementation
     can be swapped between Gemini and the local FastAPI backend with minimal
     changes to components.
   - Files to modify/create: `PRPs/examples/Front_end_UI_example/services/*`,
     `PRPs/examples/Front_end_UI_example/types.ts` (if present).
   - Dependencies: Task 1.
   - Estimated effort: 2–3h.

3. **Implement a Local Backend Chat Service**
   - Description: Create a service function that calls `POST /chat` on the local
     FastAPI app, sending `{ "query": "..." }` and reading back the
     `ChatResponse` structure. Handle errors (network, non-200 responses) and
     translate them into user-visible messages.
   - Files to modify/create:
     - `PRPs/examples/Front_end_UI_example/services/localChatService.ts`
       (new) or equivalent.
     - Possibly update `geminiService.ts` to delegate to shared abstractions.
   - Dependencies: Task 2; knowledge of `ChatResponse` schema from
     `src/agent/agent.py`.
   - Estimated effort: 2–3h.

4. **Make Backend URL Configurable**
   - Description: Introduce a configuration mechanism for the frontend to know
     the backend base URL (e.g., `VITE_BACKEND_URL`), defaulting to
     `http://localhost:8030`. Document how to change this for different
     environments.
   - Files to modify/create: `PRPs/examples/Front_end_UI_example/vite.config.ts`,
     `PRPs/examples/Front_end_UI_example/.env.example` (new),
     `PRPs/examples/Front_end_UI_example/README.md`.
   - Dependencies: Task 3.
   - Estimated effort: 1–2h.

5. **Update Components to Use the Local Service**
   - Description: Wire `useChatManager` and related hooks/components to use the
     local chat service implementation for development by default, optionally
     retaining Gemini as an alternative mode if needed.
   - Files to modify/create:
     - `PRPs/examples/Front_end_UI_example/hooks/useChatManager.ts`,
     - `PRPs/examples/Front_end_UI_example/components/*` (if they directly
       reference the service).
   - Dependencies: Tasks 2–4.
   - Estimated effort: 2–3h.

6. **Handle Citation Display in the UI**
   - Description: Once `/chat` returns grounded answers with citations, update
     the frontend to display citations (sources, scores) alongside responses.
     For now, ensure the UI gracefully handles empty or placeholder citation
     lists.
   - Files to modify/create: `PRPs/examples/Front_end_UI_example/components/*`,
     `PRPs/examples/Front_end_UI_example/types.ts`.
   - Dependencies: Phase 3 (wiring retrieval) underway.
   - Estimated effort: 2–3h.

7. **Document Frontend Setup in the Root README**
   - Description: Add a subsection to `README.md` explaining how to start the
     frontend example, how to configure its backend URL, and how it relates to
     the FastAPI `/chat` endpoint.
   - Files to modify/create: `README.md`,
     `PRPs/examples/Front_end_UI_example/README.md`.
   - Dependencies: Tasks 1–5.
   - Estimated effort: 1–2h.

### Phase 3: Wire RAG Retrieval into the Agent

1. **Define Agent-Level Retrieval Contract**
   - Description: Decide how `RAGAgent` should request retrieved context:
     either by calling a retrieval function in `src/rag_pipeline/pipeline.py`
     or by using a dedicated retrieval service module. Define the input (query)
     and output (chunks + metadata) types.
   - Files to modify/create:
     - `src/agent/agent.py`,
     - possibly new `src/rag_pipeline/retrieval.py`.
   - Dependencies: Ingestion pipeline working; database populated.
   - Estimated effort: 2–3h.

2. **Implement Retrieval Logic**
   - Description: Implement retrieval against PostgreSQL/PGVector using the
     schema defined in `PRPs/examples/rag_pipeline_docling_supabase.sql`. Use
     the same embedding model as ingestion for query vectors and perform
     similarity search plus any necessary lexical/pattern search, depending on
     what is already implemented.
   - Files to modify/create:
     - `src/rag_pipeline/persistence/supabase_store.py` (if extended),
     - `src/rag_pipeline/pipeline.py` or a new retrieval module,
     - tests under `tests/rag_pipeline/test_retrieval.py` (new).
   - Dependencies: Task 1; familiarity with the DB schema.
   - Estimated effort: 4–6h.

3. **Integrate Retrieval into `RAGAgent.chat`**
   - Description: Replace the placeholder echo logic in `RAGAgent.chat` with:
     - retrieval of relevant chunks for the incoming query,
     - construction of a prompt or message format for the LLM,
     - a call to the chosen LLM client (to be implemented or wired),
     - assembly of `ChatResponse` with answer and citations.
   - Files to modify/create: `src/agent/agent.py`,
     `src/agent/llm_client.py` (new, if created),
     tests under `tests/agent/test_agent.py`.
   - Dependencies: Task 2; LLM client available or stubbed.
   - Estimated effort: 4–6h.

4. **Introduce a Typed LLM Client Abstraction**
   - Description: Create a small, typed abstraction for calling the LLM model:
     either Qwen locally or via an API. Ensure it can be mocked in tests and
     configured via environment variables (`LLM_MODEL`, API key, base URL).
   - Files to modify/create:
     - `src/agent/llm_client.py`,
     - tests under `tests/agent/test_llm_client.py`.
   - Dependencies: Existing settings in `src/shared/config.py`.
   - Estimated effort: 3–4h.

5. **Propagate Settings and Logging Through the Agent**
   - Description: Ensure `RAGAgent` uses `Settings` from
     `src/shared/config.py` consistently for database URLs, embedding model,
     LLM model, and any retrieval/LLM endpoint configuration. Add structured
     logging around retrieval and generation steps.
   - Files to modify/create: `src/agent/agent.py`,
     `src/shared/logging.py`,
     tests under `tests/agent/test_agent.py`.
   - Dependencies: Tasks 2–4.
   - Estimated effort: 2–3h.

6. **Update API Tests for Grounded Responses**
   - Description: Extend `tests/test_main.py` and `tests/agent/test_agent.py`
     to assert that, when a small fixture corpus is ingested, `/chat` returns
     answers that reference the ingested content (or at least that retrieval
     and LLM are called).
   - Files to modify/create: `tests/test_main.py`,
     `tests/agent/test_agent.py`,
     fixtures in `tests/rag_pipeline` as needed.
   - Dependencies: Tasks 2–5; test corpus prepared.
   - Estimated effort: 3–4h.

### Phase 4: Developer Experience & Validation

1. **Add Example Configuration Files**
   - Description: Provide `.env.example` files or similar in the project root
     and frontend example, documenting required environment variables and
     providing sensible placeholders.
   - Files to modify/create: `.env.example` (root),
     `PRPs/examples/Front_end_UI_example/.env.example`.
   - Dependencies: Phases 1–3.
   - Estimated effort: 1–2h.

2. **Create a “First Run” Checklist**
   - Description: Add a short checklist that developers can follow to confirm
     their environment is correctly set up: tools installed, DB reachable,
     ingestion succeeds, `/chat` responds, frontend can connect.
   - Files to modify/create: `README.md`,
     `docs/post_ingestion_validation.md`.
   - Dependencies: Phases 1–3.
   - Estimated effort: 1–2h.

3. **Document Common Error Scenarios End-to-End**
   - Description: Extend troubleshooting sections to include frontend/backend
     connectivity errors, missing environment variables, and typical DB issues.
   - Files to modify/create: `docs/rag_pipeline_ingestion.md`,
     `README.md`.
   - Dependencies: Phases 2–3; empirical experience running the system.
   - Estimated effort: 2–3h.

4. **Verify Validation Commands Across Platforms**
   - Description: Run and document `ruff`, `mypy`, and `pytest` execution in
     typical environments (Linux, WSL, possibly macOS) and record any
     platform-specific caveats.
   - Files to modify/create: `docs/post_ingestion_validation.md`,
     `README.md`.
   - Dependencies: Tooling installed.
   - Estimated effort: 2–4h.

5. **Ensure Plans and Reality Stay in Sync**
   - Description: Update `PRPs/requests/rag_pipeline_remaining_work.md`,
     `PRPs/requests/next_steps_validation_plan.md`, and
     `PRPs/requests/phase4_hardening_and_performance_plan.md` as work is
     completed so they reflect the current state of the codebase and remaining
     tasks.
   - Files to modify/create: those three plan files.
   - Dependencies: Phases 1–3 progress.
   - Estimated effort: 2–3h.

## Codebase Integration Points

### Files to Modify
- `README.md` – Finalize and maintain the Quickstart, frontend instructions,
  and “what you get after setup” description.
- `docs/architecture.md` – Include end-to-end flow and frontend references.
- `docs/rag_pipeline_ingestion.md` – Cross-link to Quickstart, clarify
  ingestion configuration, and document end-to-end troubleshooting.
- `docs/post_ingestion_validation.md` – Capture validation runs and first-run
  checklist details.
- `PRPs/examples/Front_end_UI_example/*` – Adapt React/Vite example to use
  the local `/chat` endpoint via a configurable backend URL.
- `src/agent/agent.py` – Wire retrieval and LLM calls into `RAGAgent.chat`,
  add structured logging, and keep types consistent.
- `src/shared/config.py` – Ensure any new environment variables (e.g., LLM
  endpoint) are captured and documented.
- `src/shared/logging.py` – Support new logging fields for retrieval and
  generation, if needed.
- `src/rag_pipeline/pipeline.py` and/or new retrieval modules – Implement
  query-time retrieval using the existing ingestion schema and embeddings.
- `src/rag_pipeline/persistence/supabase_store.py` – Expose retrieval methods
  if appropriate.
- `tests/test_main.py`, `tests/agent/test_agent.py`,
  `tests/rag_pipeline/*` – Extend tests to cover grounded chat responses and
  retrieval behavior.

### New Files to Create
- `PRPs/examples/Front_end_UI_example/localChatService.ts` (or similar) – Frontend
  service for calling the FastAPI `/chat` endpoint.
- `PRPs/examples/Front_end_UI_example/.env.example` – Example frontend env file
  documenting the backend URL.
- `src/agent/llm_client.py` – Typed abstraction for calling the LLM.
- `tests/agent/test_llm_client.py` – Unit tests for the LLM client abstraction.
- `tests/rag_pipeline/test_retrieval.py` – Tests for new retrieval logic.
- `.env.example` (project root) – Example environment variables for backend
  and ingestion.

### Existing Patterns to Follow
- Type safety and docstring style from `src/shared/config.py`,
  `src/agent/agent.py`, and the rest of the `src/` tree (no `Any` without
  justification, Google-style docstrings).
- Logging conventions from `src/shared/logging.py` and ingestion/logging
  guidance in `PRPs/ai_docs/logging_guide.md`.
- Tool and schema conventions from `PRPs/ai_docs/tool_guide.md` and
  `src/tools/ingestion_skill`.
- Testing layout and patterns from `PRPs/ai_docs/testing_guide.md` and the
  existing `tests/` modules.

## Technical Design

### Architecture Diagram (End-to-End)
```
Browser UI (React/Vite) ----> FastAPI Backend (/chat)
           |                         |
           v                         v
   Frontend Chat Service       RAGAgent.chat()
                                      |
                                      v
                             Retrieval (Postgres/PGVector)
                                      |
                                      v
                              LLM Client (Qwen)
                                      |
                                      v
                          Answer + Citations to Frontend

Ingestion CLI/Skill ----> Docling + Embeddings + PGVector
```

### Data Flow
- Ingestion:
  - Documents are placed into configured source directories.
  - The ingestion CLI or ingestion skill runs, using Docling for conversion,
    Qwen embeddings for vectors, and Supabase/PostgreSQL for storage.
  - Ingestion logs structured metadata about sources, chunks, and embedding
    batches, as captured in `docs/post_ingestion_validation.md`.
- Query:
  - The frontend (or any HTTP client) sends a `ChatRequest` with a `query`
    string to the `/chat` endpoint on the FastAPI backend.
  - `RAGAgent.chat` receives the request, logs the event, and calls the
    retrieval layer to find relevant document chunks from the database.
  - Retrieved chunks are assembled into a prompt or message format and passed
    to the LLM client, which calls the configured model.
  - The LLM’s answer is packaged into a `ChatResponse` with citations pointing
    back to the source documents.
  - The backend returns this response, and the frontend renders the answer and
    citations for the user.

### API Endpoints
- `GET /health` – Health check endpoint used by tests and deployment scripts
  to verify that the backend is running.
- `POST /chat` – Main chat endpoint:
  - Request body: `ChatRequest` with a `query: str`.
  - Response body: `ChatResponse` with `answer: str` and `citations: list`.
  - This endpoint will be extended to use real retrieval and generation.

## Dependencies and Libraries
- Backend:
  - FastAPI, Uvicorn – HTTP API layer and ASGI server.
  - PostgreSQL with PGVector and `pg_trgm` – Document and chunk storage.
  - Qwen embedding and LLM clients – For embeddings and generation.
  - Docling – For document ingestion and chunking.
  - Requests (or similar) – For HTTP calls to embedding/LLM services.
- Frontend:
  - React, Vite – UI framework and bundler.
  - TypeScript – Type safety for frontend code.
- Tooling:
  - Ruff – Linting.
  - Mypy – Type checking.
  - Pytest – Testing, including performance markers.

## Testing Strategy
- Backend unit tests:
  - Continue to cover configuration, pipeline components, and agent methods.
  - Add tests for new retrieval and LLM client behavior.
- Backend integration tests:
  - Use a minimal fixture corpus and Postgres instance (or mocks) to test
    ingestion + retrieval + chat in a single flow.
- Frontend tests:
  - At minimum, maintain a manual validation checklist for the React/Vite app
    (send a message, see response, handle errors).
  - Optionally add automated tests (e.g., React Testing Library or Cypress).
- Performance tests:
  - Keep `pytest` performance tests opt-in and document how to run them when
    benchmarking end-to-end throughput.

## Success Criteria
- [ ] A new user can follow `README.md` and:
      - Clone the repo, set up Python, configure the database, and run ingestion.
      - Start the FastAPI backend and send a `/chat` request successfully.
- [ ] The React/Vite frontend example can be configured to call the local
      `/chat` endpoint and render responses and (eventually) citations.
- [ ] `RAGAgent.chat` is wired to real retrieval and LLM calls, returning
      grounded answers using ingested documents.
- [ ] All new code passes `ruff`, `mypy`, and `pytest` (non-performance) with
      no regressions.
- [ ] Documentation clearly differentiates between placeholder behavior and
      fully wired RAG functionality.
- [ ] Plans in `PRPs/requests` remain in sync with the actual state of the
      codebase and describe only work that remains to be done.

## Notes and Considerations
- This plan assumes the ingestion pipeline and its tests remain stable; any
  changes to ingestion should be reflected in both the retrieval layer and
  documentation.
- Frontend work should remain minimal and focused: the goal is a practical chat
  UI, not a full design system.
- When wiring retrieval and the LLM, start with small, deterministic fixtures
  to keep tests reliable.
- Keep KISS and YAGNI in mind: avoid over-abstracting retrieval and LLM calls
  until real-world use cases demonstrate the need.

---
*This plan is ready for execution with `/execute-plan`*

