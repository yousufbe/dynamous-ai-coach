# Implementation Plan: Fine-Tuned Embeddings Rollout & Retrieval Regression

## Overview
Roll out the fine-tuned embeddings workflow as the default retrieval path with reproducible data prep, training, evaluation, and integration. Provide config switches to fall back to baseline embeddings, add regression tests for recall@k, and update docs/observability so support can trace which model/version is serving.

## Requirements Summary
- Build/synthesize domain query–document pairs from existing corpora with reproducible metadata (source, version, doc ids).
- Fine-tune `Qwen/Qwen3-Embedding-0.6B` using MultipleNegativesRankingLoss; persist versioned artifact for ingestion.
- Add regression suite comparing fine-tuned vs base embeddings (recall@k) on held-out validation data.
- Integrate ingestion/retrieval to use the versioned fine-tuned model by default, with a flag to fall back to baseline.
- Log model fingerprint, training data snapshot, and retrieval performance in traces/logs (Langfuse + structured logs).
- Update user-facing docs (README.md, AGENTS.md, docs/architecture.md, docs/rag_pipeline_ingestion.md, docs/post_ingestion_validation.md) to reflect the new workflow and toggles.

## Research Findings
### Best Practices
- Keep data prep deterministic; store splits and metadata to reproduce training/eval.
- Use MultipleNegativesRankingLoss with in-batch negatives; monitor margin collapse and embedding norm drift.
- Version artifacts (`models/fine_tuned/<epoch>-<timestamp>/`) and log fingerprints in both training output and runtime logs.
- Gate rollout with recall@k regression vs baseline; keep a config flag to switch models without code changes.
- Surface model/version, training data snapshot, and correlation_id in Langfuse traces for debuggability.

### Reference Implementations
- `PRPs/ai_docs/fine-tuned-embeddings.md` — requirements and workflow guide.
- `PRPs/examples/fine_tuned_embeddings.py` — reference slice for training loop.
- `src/shared/tracing.py` — Langfuse integration for logging fingerprints.
- `src/rag_pipeline/config.py` / `src/shared/config.py` — config patterns for optional features.

### Technology Decisions
- Use SentenceTransformers with `Qwen/Qwen3-Embedding-0.6B` and MultipleNegativesRankingLoss.
- Store artifacts locally under `models/fine_tuned/<version>/`; path selectable via env/config.
- Keep default torch device resolution via existing `src/shared/device.py`; support CPU fallback.
- No new external services; reuse existing Langfuse for observability and Postgres/Supabase for persistence.

## Implementation Tasks

### Phase 1: Data Prep & Metadata
1. **Assemble training/validation corpora**
   - Description: Build scripts to extract/synthesize query–document pairs from `documents/` (including fixtures) with metadata (source, version, doc ids). Persist splits to `data/fine_tune/{train,valid}.jsonl`.
   - Files to modify/create: `src/rag_pipeline/embeddings/data_prep.py` (new), `data/fine_tune/README.md` (new).
   - Dependencies: None.
   - Estimated effort: 0.8h

2. **Add dataset versioning metadata**
   - Description: Include dataset version hash + doc ids in saved JSONL; expose helper to compute fingerprint for logging.
   - Files: `src/rag_pipeline/embeddings/data_prep.py`, tests in `tests/rag_pipeline/embeddings/test_data_prep.py`.
   - Dependencies: Task 1.
   - Estimated effort: 0.5h

### Phase 2: Training Pipeline
3. **Training loop implementation**
   - Description: Add a training entrypoint that loads the prepared pairs, fine-tunes `Qwen/Qwen3-Embedding-0.6B` with MultipleNegativesRankingLoss, logs metrics, and writes artifacts to `models/fine_tuned/<version>/`.
   - Files: `src/rag_pipeline/embeddings/train.py` (new), `src/rag_pipeline/embeddings/__init__.py`, tests in `tests/rag_pipeline/embeddings/test_train.py` (mocked).
   - Dependencies: Tasks 1–2.
   - Estimated effort: 1.2h

4. **Artifact manifest & fingerprinting**
   - Description: Write manifest (model name, dataset fingerprint, hyperparams, timestamp, commit hash) alongside the artifact; expose helper to load manifest at runtime.
   - Files: `src/rag_pipeline/embeddings/manifest.py` (new), tests in `tests/rag_pipeline/embeddings/test_manifest.py`.
   - Dependencies: Task 3.
   - Estimated effort: 0.6h

### Phase 3: Evaluation & Regression
5. **Recall@k regression harness**
   - Description: Implement evaluation comparing base vs fine-tuned embeddings on held-out validation pairs; report recall@k/mean rank and emit JSON + log.
   - Files: `src/rag_pipeline/embeddings/eval.py` (new), tests in `tests/rag_pipeline/embeddings/test_eval.py`.
   - Dependencies: Tasks 1–4.
   - Estimated effort: 1.0h

6. **Automation hook for CI/local**
   - Description: Add a `make`/script entrypoint (e.g., `scripts/run_embedding_eval.py`) gated by env to avoid heavy runs by default.
   - Files: `scripts/run_embedding_eval.py` (new), docs in `docs/rag_pipeline_ingestion.md`.
   - Dependencies: Task 5.
   - Estimated effort: 0.5h

### Phase 4: Ingestion/Retrieval Integration
7. **Config toggle for fine-tuned model**
   - Description: Add config/env keys (`EMBEDDING_MODEL_FINE_TUNED_PATH`, `USE_FINE_TUNED_EMBEDDINGS`) with fallback to baseline; surface in `src/shared/config.py` and `src/rag_pipeline/config.py`.
   - Files: `src/shared/config.py`, `src/rag_pipeline/config.py`, corresponding tests in `tests/shared/test_config.py`, `tests/rag_pipeline/test_config.py`.
   - Dependencies: Task 4.
   - Estimated effort: 0.8h

8. **Ingestion client wiring**
   - Description: Update embedding client selection to load the fine-tuned SentenceTransformer when enabled; log model fingerprint and dataset version; keep baseline path unchanged.
   - Files: `src/rag_pipeline/embeddings/qwen_client.py` (or new loader), `src/rag_pipeline/pipeline.py`, tests in `tests/rag_pipeline/test_embeddings_qwen_client.py`.
   - Dependencies: Task 7.
   - Estimated effort: 1.0h

9. **Runtime observability**
   - Description: Add logs and Langfuse attributes for `embedding_model`, `embedding_fingerprint`, `dataset_version`, and `correlation_id` on ingest/retrieval spans.
   - Files: `src/shared/tracing.py`, `src/rag_pipeline/pipeline.py`, `src/agent/agent.py`.
   - Dependencies: Task 8.
   - Estimated effort: 0.5h

### Phase 5: Docs & Validation
10. **Docs refresh**
    - Description: Update README.md, AGENTS.md, docs/architecture.md, docs/rag_pipeline_ingestion.md, docs/post_ingestion_validation.md with fine-tuned workflow, config flags, artifact paths, and evaluation instructions.
    - Files: as listed.
    - Dependencies: Tasks 1–9.
    - Estimated effort: 0.8h

11. **Validation snapshot**
    - Description: Run `ruff`, `mypy`, `pytest -v`, and (optionally) embedding eval harness; record results/date and model fingerprint in `docs/post_ingestion_validation.md`.
    - Files: `docs/post_ingestion_validation.md`, new note under `PRPs/notes/<date>_embedding_eval.md`.
    - Dependencies: Task 10.
    - Estimated effort: 0.6h

### Phase 6: Archon Tracking
12. **Archon task updates**
    - Description: Create/attach tasks for phases above in Archon (project `fbe94a2b-1226-4e38-b094-f3a66cdedbb2`), keep statuses synchronized, and ensure docs are updated before marking review/done.
    - Files: Archon records.
    - Dependencies: All tasks.
    - Estimated effort: 0.3h

## Codebase Integration Points
### Files to Modify
- `src/shared/config.py` — new embedding config toggles.
- `src/rag_pipeline/config.py` — ingestion-side toggles and paths.
- `src/rag_pipeline/embeddings/qwen_client.py` — load fine-tuned model option and logging.
- `src/rag_pipeline/pipeline.py` — pass embedding model info into pipeline services/logs.
- `src/shared/tracing.py` — add embedding metadata to spans.
- Docs: `README.md`, `AGENTS.md`, `docs/architecture.md`, `docs/rag_pipeline_ingestion.md`, `docs/post_ingestion_validation.md`.

### New Files to Create
- `src/rag_pipeline/embeddings/data_prep.py` — dataset build/fingerprint.
- `src/rag_pipeline/embeddings/train.py` — training entrypoint.
- `src/rag_pipeline/embeddings/manifest.py` — artifact manifest helpers.
- `src/rag_pipeline/embeddings/eval.py` — regression harness.
- `scripts/run_embedding_eval.py` — opt-in evaluation runner.
- `data/fine_tune/README.md` — dataset instructions.
- Tests under `tests/rag_pipeline/embeddings/`.

### Existing Patterns to Follow
- Config + env parsing patterns in `src/shared/config.py`.
- Structured logging with correlation_id as in `src/shared/logging.py`.
- No-op/optional dependency handling as in `src/shared/tracing.py`.
- Testing style from `tests/rag_pipeline/test_embeddings_qwen_client.py`.

## Technical Design
### Data Flow
- Data prep: corpus → JSONL pairs with metadata/fingerprint.
- Training: load pairs → SentenceTransformer fine-tune → artifact + manifest.
- Evaluation: base vs tuned embeddings → recall@k metrics → JSON + log/trace.
- Ingestion: config selects tuned artifact → embedding client loads model → chunk embeddings → DB.
- Runtime: traces/logs carry embedding fingerprints and dataset versions.

### API Endpoints
- No new HTTP endpoints; reuse existing ingestion/agent flows.

## Dependencies and Libraries
- `sentence-transformers`, `torch` (already present).
- Optional: `scikit-learn` for evaluation metrics (check existing deps before adding).

## Testing Strategy
- Unit: data prep fingerprinting, manifest read/write, config toggles, evaluation metrics, embedding client selection.
- Integration: eval harness comparing base vs tuned embeddings; ingestion with tuned model (short corpus).
- Regression: ensure baseline fallback works when fine-tuned path missing.
- Tracing/logging: assert embedding metadata appears in logs/traces when enabled.

## Success Criteria
- [ ] Dataset prep produces versioned JSONL with reproducible fingerprint.
- [ ] Fine-tuned artifact saved under versioned path with manifest.
- [ ] Regression harness reports improved or baseline recall@k with reproducible outputs.
- [ ] Ingestion/retrieval uses tuned embeddings by default, with a documented flag to revert to baseline.
- [ ] Traces/logs show embedding model + dataset fingerprint alongside correlation_id.
- [ ] Docs updated and validation snapshot refreshed.

## Notes and Considerations
- Keep runs opt-in to avoid heavy compute; guard training/eval behind explicit scripts/env flags.
- Verify GPU availability before training; fall back to CPU if needed.
- Rotate Langfuse keys as needed; ensure embedding metadata is safe to log.

---
*This plan is ready for execution with `/execute-plan PRPs/requests/17-finetuned_embeddings_rollout.md`*
