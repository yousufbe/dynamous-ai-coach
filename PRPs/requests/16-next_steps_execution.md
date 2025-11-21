# Implementation Plan: Next Steps (Langfuse enablement, GPU hardening, performance shakeout, frontend readiness)

## Overview
Tighten observability (enable Langfuse with real keys), confirm GPU 0 remains the default with clear handling of the unsupported GPU 1, make the performance suite runnable/green, and line up frontend/backend readiness with current backend behaviour. Keep all changes type-safe, simple, and documented.

## Requirements Summary
- Enable Langfuse tracing end-to-end with real credentials and keep no-op fallback safe.
- Ensure GPU 0 (3080) is consistently used; document/mitigate GPU 1 (1060) incompatibility warnings.
- Unskip/address the performance benchmark so it can run (or is clearly opt-in with documented prerequisites).
- Align docs and Archon tracking with the above and keep validation current.
- Preserve KISS/YAGNI and strict typing; update user-facing docs (README.md, AGENTS.md, `docs/*.md`) when behaviour changes.

## Research Findings
### Best Practices
- Langfuse: keep tracing optional; fail open to logs only; propagate correlation_id into spans; expose env toggles.
- GPU selection: prefer `CUDA_VISIBLE_DEVICES=0` masking; explicit `cuda:0` config; log device and memory; fall back to CPU with a warning when unsupported GPUs are present.
- Performance runs: mark heavy tests with `@pytest.mark.performance`; gate execution with env flags; document hardware/DB/endpoint prerequisites.

### Reference Implementations
- Current tracing helper: `src/shared/tracing.py` (no-op + Langfuse wrapper).
- Device selection helper: `src/shared/device.py` (defaults to `cuda:0`).
- Performance marker: `tests/performance/test_ingestion_performance.py::test_ingestion_performance_baseline` (currently skipped).

### Technology Decisions
- Keep Langfuse optional; add it to runtime deps only if enabling by default, otherwise document venv install path.
- Stick with PyTorch defaults; mitigate GPU 1 via env masking and warnings rather than custom builds unless required.
- Keep performance suite opt-in but runnable with a clear checklist.

## Implementation Tasks

### Phase 1: Observability Enablement
1. **Plumb Langfuse credentials**
   - Description: Add `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` guidance to `.env.example`; optionally add `langfuse` to `requirements.txt` or a dedicated extras section if we want first-class support.
   - Files to modify/create: `.env.example`, README.md, docs/architecture.md, docs/post_ingestion_validation.md, AGENTS.md (if global guidance needed).
   - Dependencies: N/A
   - Estimated effort: 0.5h

2. **Smoked end-to-end with keys**
   - Description: Run `/chat` with Langfuse enabled and real keys to verify spans appear with correlation IDs; capture screenshots/notes in `PRPs/notes/`.
   - Files to modify/create: PRPs/notes/*.md (new note), Archon task update.
   - Dependencies: Task 1
   - Estimated effort: 0.7h

### Phase 2: GPU Hardening
3. **Mask unsupported GPU and document**
   - Description: Encourage/ensure `CUDA_VISIBLE_DEVICES=0` in local scripts; optionally add a startup warning if multiple GPUs and one is unsupported; add doc note on 1060 warning and Torch build expectations.
   - Files to modify/create: src/shared/device.py (warning), README.md, docs/post_ingestion_validation.md.
   - Dependencies: None
   - Estimated effort: 0.7h

### Phase 3: Performance Suite Readiness
4. **Make performance test runnable**
   - Description: Add prerequisites/env flags to run the performance marker; adjust markers/fixtures so it can execute with local resources (or clearly document why it stays skipped). Capture latest run results in validation note.
   - Files to modify/create: tests/performance/test_ingestion_performance.py, docs/post_ingestion_validation.md.
   - Dependencies: DB/embeddings available.
   - Estimated effort: 1.0h

### Phase 4: Frontend/Backend Alignment (lightweight readiness)
5. **Baseline frontend backend-config guidance**
   - Description: Document how to point the sample frontend at `http://localhost:8030` and note Archon host `http://localhost:8181`; ensure instructions reflect current backend contract (LLM fallback, tracing optional).
   - Files to modify/create: README.md, potentially `PRPs/examples/Front_end_UI_example` readme.
   - Dependencies: None
   - Estimated effort: 0.8h

### Phase 5: Validation & Tracking
6. **Validation sweep**
   - Description: Run `ruff`, `mypy`, `pytest -v` (and performance if enabled) and refresh `docs/post_ingestion_validation.md` with dates/results; note GPU warnings if any.
   - Files to modify/create: docs/post_ingestion_validation.md.
   - Dependencies: Tasks 1–4 as applicable.
   - Estimated effort: 0.7h

7. **Archon updates**
   - Description: Create/update Archon tasks for each phase; move to review/done after code + docs + validation are complete.
   - Files to modify/create: Archon task records.
   - Dependencies: All tasks above.
   - Estimated effort: 0.3h

## Codebase Integration Points
### Files to Modify
- `README.md` / `.env.example` / `AGENTS.md` / `docs/architecture.md` / `docs/post_ingestion_validation.md` — env guidance, observability, GPU notes, validation snapshots.
- `src/shared/device.py` — add warning/logging for unsupported GPUs.
- `tests/performance/test_ingestion_performance.py` — adjust markers/fixtures for runnable status.

### New Files to Create
- `PRPs/notes/<date>-langfuse-smoke.md` — record Langfuse trace verification.

### Existing Patterns to Follow
- Type hints everywhere; Google-style docstrings; structured logging with `correlation_id`.
- No-op fallbacks for optional integrations (Langfuse).
- KISS/YAGNI: avoid over-abstraction; keep device handling minimal.

## Technical Design

### Data Flow
- `/chat` → `RAGAgent` → retrieval/embeddings/LLM with correlation_id; when Langfuse is enabled, spans wrap these calls with IDs aligned to logs.
- Device selection: `GPU_DEVICE` + `CUDA_VISIBLE_DEVICES` influence torch device resolution; logs emit selected device and memory; fallback to CPU on mismatch/unsupported GPU.

### API Endpoints (unchanged)
- `POST /chat` — used for Langfuse smoke and performance checks.

## Dependencies and Libraries
- Optional: `langfuse` (already installed in venv); decide on adding to `requirements.txt` or extras.
- PyTorch CUDA runtime as currently installed; consider re-install only if GPU 1 must be supported.

## Testing Strategy
- Unit: device helper warning path; any changes to performance fixtures.
- Integration: Langfuse-enabled `/chat` smoke with real keys; GPU-pinned smoke (`CUDA_VISIBLE_DEVICES=0`).
- Validation: `ruff`, `mypy`, `pytest -v`; performance test run if enabled.

## Success Criteria
- [ ] Langfuse can emit traces with real keys; docs show setup and optional nature.
- [ ] GPU 0 is the default; unsupported GPU 1 is masked or clearly warned; docs tell how to pin.
- [ ] Performance suite is runnable (or explicitly documented as opt-in) with prerequisites spelled out.
- [ ] Frontend/backend guidance reflects current endpoints and Archon host.
- [ ] Validation docs updated with fresh dates/results.

## Notes and Considerations
- Keep performance runs opt-in to avoid noisy CI; document the exact env/DB/model requirements.
- If GPU 1 support is needed later, a Torch build matching sm_61 may be required; defer under YAGNI.
- Archon host is `http://localhost:8181`; keep tasks updated in that instance.

---
*This plan is ready for execution with `/execute-plan PRPs/requests/16-next_steps_execution.md`*
