# Implementation Plan: Observability Boost (Langfuse) & Validation Refresh

## Overview
Add structured observability using the existing Langfuse stack (`http://127.0.0.1:3000` web, `http://127.0.0.1:3030` worker) and keep validation snapshots current. The goal is to enrich chat/retrieval tracing with correlation IDs and Langfuse spans, while ensuring lint/type/test suites (including performance marker) stay fresh.

## Requirements Summary
- Wire Langfuse tracing into `/chat` and retrieval/LLM paths, reusing existing correlation IDs.
- Keep logging KISS/YAGNI: minimal hooks, no heavy abstractions.
- Re-run validation (ruff, mypy, pytest unit/integration) and document results; note performance suite status.
- Update user-facing docs (README.md, `docs/post_ingestion_validation.md`, `docs/architecture.md`) to reflect observability flow and Langfuse endpoints.

## Research Findings
### Best Practices
- Keep tracing opt-in via config envs (e.g., `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`).
- Propagate correlation IDs into trace/span metadata to align with structured logs.
- Avoid span explosion; capture key steps: request start, retrieval, embedding, LLM call, response.
- Ensure tracing failures degrade gracefully (logs only, no user-facing errors).
### Reference Implementations
- Existing correlation_id additions in `src/main.py`, `src/agent/agent.py`, `src/rag_pipeline/retrieval.py`, `src/agent/llm_client.py`, `src/rag_pipeline/embeddings/qwen_client.py`.
- Langfuse Python SDK quickstart (spans, events, trace tree).

## Implementation Tasks
### Phase 1: Config & Hooks
1. **Add Langfuse settings**
   - Description: Add typed settings for `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_ENABLED` to `src/shared/config.py`.
   - Files: `src/shared/config.py`, docstrings.
   - Effort: 0.3h
2. **Tracing helper**
   - Description: Introduce a minimal tracing helper (factory + no-op) to create traces/spans with correlation_id metadata.
   - Files: `src/shared/tracing.py` (new), optional `__init__.py`.
   - Effort: 0.7h

### Phase 2: Instrument Chat Path
3. **FastAPI entry trace**
   - Description: Start a Langfuse trace in `/chat` using correlation_id; attach request metadata.
   - Files: `src/main.py`
   - Effort: 0.5h
4. **Agent spans**
   - Description: Wrap retrieval and LLM calls in spans; include timing, model names, top_k, results_count.
   - Files: `src/agent/agent.py`, `src/rag_pipeline/retrieval.py`, `src/agent/llm_client.py`
   - Effort: 1h
5. **Embedding spans**
   - Description: Capture embedding batches as spans with batch_id/item_count when enabled.
   - Files: `src/rag_pipeline/embeddings/qwen_client.py`
   - Effort: 0.5h

### Phase 3: Validation & Docs
6. **Re-run validation**
   - Description: `ruff`, `mypy`, `pytest -m "not performance"`, and note performance suite status (currently skipped) in `docs/post_ingestion_validation.md`.
   - Files: `docs/post_ingestion_validation.md`
   - Effort: 0.5h
7. **Doc updates**
   - Description: Document Langfuse setup/endpoints and tracing toggle in README.md and `docs/architecture.md` (observability section), plus validation snapshot refresh.
   - Files: README.md, `docs/architecture.md`, `docs/post_ingestion_validation.md`
   - Effort: 0.7h

### Phase 4: Guardrails
8. **Ensure no-op fallback**
   - Description: Confirm tracing is non-blocking when env vars are absent; add tests if feasible.
   - Files: `src/shared/tracing.py`, unit tests under `tests/shared/`.
   - Effort: 0.5h

## Codebase Integration Points
- `src/shared/config.py` – new Langfuse settings.
- `src/shared/tracing.py` – tracing helper/no-op.
- `src/main.py`, `src/agent/agent.py`, `src/rag_pipeline/retrieval.py`, `src/agent/llm_client.py`, `src/rag_pipeline/embeddings/qwen_client.py` – span hooks.
- Docs: README.md, `docs/architecture.md`, `docs/post_ingestion_validation.md`.

## Testing Strategy
- Unit: tracing helper no-op vs configured modes; ensure spans don’t raise when disabled.
+- Integration: run `/chat` with tracing disabled (default) to confirm unchanged behaviour; optional smoke with Langfuse creds if available.
- Validation: ruff, mypy, pytest (unit/integration); note performance marker status.

## Success Criteria
- [ ] Langfuse config/envs added with safe defaults and type hints.
- [ ] Correlation_id appears in logs and Langfuse traces/spans when enabled.
- [ ] Validation doc refreshed with latest runs and performance suite status.
- [ ] README/architecture describe observability setup and endpoints (`http://127.0.0.1:3000`, `:3030`).
- [ ] Tracing disabled by default; failures degrade gracefully.
