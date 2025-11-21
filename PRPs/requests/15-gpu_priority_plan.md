# Implementation Plan: Prioritize Primary GPU (GPU 0) Over Backup GPU (GPU 1)

## Overview
Ensure the main GPU (GPU 0, RTX 3080 10GB) is used preferentially for inference/embeddings before falling back to the backup GPU (GPU 1, GTX 1060 6GB). Add configuration knobs, detection, and validation steps so GPU affinity is explicit and debuggable without code churn.

## Requirements Summary
- Default all GPU-bound workloads to GPU 0 unless explicitly overridden.
- Provide a single, documented way to pin CUDA_VISIBLE_DEVICES for the stack (LLM, embeddings, Docling extras if applicable).
- Add lightweight diagnostics to confirm which GPU is selected at runtime.
- Keep changes simple (KISS/YAGNI) and type-safe; avoid speculative features.

## Research Findings
### Best Practices
- Use `CUDA_VISIBLE_DEVICES=0` to mask other GPUs for most libraries (PyTorch, transformers, vLLM, Docling extras); document this as the primary knob.
- When device selection is coded, prefer explicit device IDs (e.g., `cuda:0`) sourced from config/env rather than implicit defaults.
- Add a short runtime check to log the chosen device name and total memory for observability.
- Avoid hardcoding per-model logic; rely on a shared helper for device selection if needed.

### Reference Points in Repo
- Settings plumbed via `src/shared/config.py` and used by `RAGAgent`, embeddings, retrieval, and CLI entrypoints.
- Logging is already structured; correlation IDs exist and can carry device info.
- Doc guidance lives in README.md and `docs/architecture.md`; validation notes in `docs/post_ingestion_validation.md`.

## Implementation Tasks

### Phase 1: Configuration & Defaults
1. **Add GPU device setting**
   - Description: Add `GPU_DEVICE` (default `cuda:0`) and `CUDA_VISIBLE_DEVICES` guidance to `src/shared/config.py` and `.env.example`/docs.
   - Files: `src/shared/config.py`, `.env.example`, README.md.
   - Effort: 0.3h

2. **Document environment knob**
   - Description: In README and `docs/architecture.md`, document `CUDA_VISIBLE_DEVICES=0` as the primary control; note fallback to CPU if GPU unavailable.
   - Files: README.md, `docs/architecture.md`.
   - Effort: 0.2h

### Phase 2: Enforcement in Core Runtime
3. **Inject device selection into model/embedding clients (config-driven)**
   - Description: Ensure embedding/LLM clients respect a configured device string (pass through to underlying libraries where applicable). Keep behavior unchanged when unset.
   - Files: `src/agent/llm_client.py`, `src/rag_pipeline/embeddings/qwen_client.py` (only if device is used), any model loaders if present.
   - Effort: 0.8h

4. **CLI and server entrypoints honor GPU pinning**
   - Description: Propagate device setting into CLI/runtime services; validate no overrides are hardcoded.
   - Files: `src/main.py`, `src/rag_pipeline/runtime.py`, `src/rag_pipeline/cli.py`.
   - Effort: 0.5h

### Phase 3: Diagnostics & Validation
5. **Runtime device log**
   - Description: On startup and first model/embedding call, log chosen device name, index, and total memory; include correlation_id when available.
   - Files: `src/shared/logging.py` (helper if needed), call sites in `RAGAgent` or clients.
   - Effort: 0.5h

6. **Smoke validation**
   - Description: Add a short checklist to `docs/post_ingestion_validation.md` for GPU selection (nvidia-smi snapshot showing GPU 0 load, `CUDA_VISIBLE_DEVICES=0` export).
   - Files: `docs/post_ingestion_validation.md`.
   - Effort: 0.3h

### Phase 4: Guardrails
7. **Graceful fallback**
   - Description: If GPU 0 is unavailable, log and fall back to CPU or next GPU with a clear warning; do not silently pick GPU 1 without a log.
   - Files: Clients/runtime where device is chosen.
   - Effort: 0.5h

8. **Tests/Lint**
   - Description: Add/adjust unit tests for the new config fields and any device-selection helpers; rerun ruff/mypy/pytest.
   - Files: `tests/shared/`, relevant client tests.
   - Effort: 0.5h

## Codebase Integration Points
- `src/shared/config.py` for new GPU device config.
- Model/embedding clients for honoring device strings.
- Entry points (`src/main.py`, `src/rag_pipeline/cli.py`, `src/rag_pipeline/runtime.py`) for environment propagation.
- Documentation (README.md, `docs/architecture.md`, `docs/post_ingestion_validation.md`) for user guidance.

## Testing Strategy
- Unit: config field parsing, device helper behavior with/without envs.
- Manual: run `CUDA_VISIBLE_DEVICES=0` and observe `nvidia-smi` showing GPU 0 load; verify logs show device selection and no GPU 1 usage unless forced.
- Regression: ruff, mypy, pytest (unit/integration); performance suite optional.

## Success Criteria
- [ ] GPU selection defaults to GPU 0 and is configurable via env.
- [ ] Clear logs show the chosen device and memory; fallback is explicit when GPU 0 unavailable.
- [ ] Docs include a simple GPU pinning checklist and validation step.
- [ ] Lint/type/test suites remain clean.
