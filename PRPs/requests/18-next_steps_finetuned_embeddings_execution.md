# Implementation Plan: Complete Fine-Tuned Embeddings Rollout

## Overview
Finish the fine-tuned embeddings rollout by implementing the training/evaluation pipeline, integrating the tuned model into ingestion/retrieval with observability, and documenting/validating the workflow. Keeps baseline fallback and strict typing.

## Requirements Summary
- Implement training loop for `Qwen/Qwen3-Embedding-0.6B` using prepared query–document pairs.
- Persist artifacts with manifest/fingerprint; expose config to select tuned vs baseline embeddings.
- Add evaluation harness comparing recall@k vs baseline; keep runs opt-in.
- Wire ingestion/retrieval to load tuned model when enabled; log fingerprints to Langfuse/logs.
- Update user-facing docs and validation snapshots.

## Research Findings
### Best Practices
- Use MultipleNegativesRankingLoss with in-batch negatives; monitor embedding norms.
- Keep dataset fingerprints and manifest (hyperparams + commit + dataset hash) alongside artifacts.
- Provide config switch and safe fallback to baseline embeddings.
- Surface model version/fingerprint and dataset hash in logs/traces for debuggability.

### Reference Implementations
- `PRPs/ai_docs/fine-tuned-embeddings.md` and `PRPs/examples/fine_tuned_embeddings.py` for training loop guidance.
- Config patterns in `src/shared/config.py` and `src/rag_pipeline/config.py`.
- Tracing/logging patterns in `src/shared/tracing.py` and `src/shared/logging.py`.

### Technology Decisions
- SentenceTransformers training with `Qwen/Qwen3-Embedding-0.6B`.
- Artifacts stored under `models/fine_tuned/<version>/` with manifest JSON.
- Optional eval dependencies only if not already present; keep KISS/YAGNI.

## Implementation Tasks

### Phase 1: Training & Artifacts
1. **Training loop**
   - Description: Implement fine-tune entrypoint (MultipleNegativesRankingLoss) loading JSONL pairs; save model under `models/fine_tuned/<version>/`.
   - Files: `src/rag_pipeline/embeddings/train.py`, `src/rag_pipeline/embeddings/__init__.py`.
   - Dependencies: data_prep helpers.
   - Estimated effort: 1.0h

2. **Manifest & fingerprint**
   - Description: Write manifest capturing model base, dataset fingerprint, hyperparams, timestamp, commit hash; loader helper.
   - Files: `src/rag_pipeline/embeddings/manifest.py`; tests in `tests/rag_pipeline/embeddings/test_manifest.py`.
   - Dependencies: Task 1.
   - Estimated effort: 0.6h

### Phase 2: Evaluation
3. **Recall regression harness**
   - Description: Compare base vs tuned embeddings on held-out pairs; emit recall@k JSON/log; small fixture for tests.
   - Files: `src/rag_pipeline/embeddings/eval.py`; tests in `tests/rag_pipeline/embeddings/test_eval.py`.
   - Dependencies: Task 2.
   - Estimated effort: 1.0h

4. **Eval runner (opt-in)**
   - Description: Script/CLI to run eval, gated by env flag to avoid default heavy runs; document usage.
   - Files: `scripts/run_embedding_eval.py`; docs in `docs/rag_pipeline_ingestion.md`.
   - Dependencies: Task 3.
   - Estimated effort: 0.4h

### Phase 3: Integration & Observability
5. **Config toggles**
   - Description: Add `USE_FINE_TUNED_EMBEDDINGS` and `EMBEDDING_MODEL_FINE_TUNED_PATH` to shared/rag configs with defaults and tests.
   - Files: `src/shared/config.py`, `src/rag_pipeline/config.py`, tests in `tests/shared/test_config.py`, `tests/rag_pipeline/test_config.py`.
   - Dependencies: Task 2.
   - Estimated effort: 0.6h

6. **Embedding client wiring**
   - Description: Load tuned SentenceTransformer when enabled; log model/dataset fingerprint; maintain baseline path.
   - Files: `src/rag_pipeline/embeddings/qwen_client.py` (or new loader), `src/rag_pipeline/pipeline.py`, tests in `tests/rag_pipeline/test_embeddings_qwen_client.py` (mock).
   - Dependencies: Task 5.
   - Estimated effort: 0.8h

7. **Runtime observability**
   - Description: Add embedding metadata (model, fingerprint, dataset hash) to logs and Langfuse spans during ingestion/retrieval.
   - Files: `src/shared/tracing.py`, `src/agent/agent.py`, `src/rag_pipeline/pipeline.py`.
   - Dependencies: Task 6.
   - Estimated effort: 0.4h

### Phase 4: Docs & Validation
8. **Docs updates**
   - Description: Document fine-tuned workflow, toggles, artifact paths, and eval steps in README.md, AGENTS.md, docs/architecture.md, docs/rag_pipeline_ingestion.md, docs/post_ingestion_validation.md.
   - Files: as listed.
   - Dependencies: Tasks 1–7.
   - Estimated effort: 0.8h

9. **Validation snapshot**
   - Description: Run ruff/mypy/pytest -v and optional eval harness; record results and fingerprints in `docs/post_ingestion_validation.md` and a note under `PRPs/notes/`.
   - Files: `docs/post_ingestion_validation.md`, `PRPs/notes/<date>_embedding_eval.md`.
   - Dependencies: Task 8.
   - Estimated effort: 0.5h

### Phase 5: Archon Tracking
10. **Archon status sync**
    - Description: Keep Archon tasks (Plan17) updated (todo→doing→review/done) after code/docs/validation; ensure docs are refreshed before review/done.
    - Files: Archon records.
    - Dependencies: All above.
    - Estimated effort: 0.3h

## Codebase Integration Points
### Files to Modify
- `src/shared/config.py`, `src/rag_pipeline/config.py` — embed toggles.
- `src/rag_pipeline/embeddings/qwen_client.py` (or loader) — tuned model path & logs.
- `src/rag_pipeline/pipeline.py`, `src/agent/agent.py` — propagate embedding metadata.
- `src/shared/tracing.py` — span attributes for embeddings.
- Docs: README.md, AGENTS.md, docs/architecture.md, docs/rag_pipeline_ingestion.md, docs/post_ingestion_validation.md.

### New Files to Create
- `src/rag_pipeline/embeddings/train.py`, `manifest.py`, `eval.py`.
- `scripts/run_embedding_eval.py`.
- Tests under `tests/rag_pipeline/embeddings/`.
- `PRPs/notes/<date>_embedding_eval.md`.

### Existing Patterns to Follow
- Config parsing and validation patterns in shared/rag configs.
- Structured logging with correlation_id.
- Optional dependency handling as in tracing/logging helpers.
- Test style from existing rag_pipeline embedding/client tests.

## Technical Design
### Data Flow
- JSONL pairs (with fingerprint) → training → artifact + manifest → eval harness compares base vs tuned → ingestion loads tuned model when enabled → logs/traces include embedding metadata.

### API Endpoints
- None added; reuse ingestion/agent flows.

## Dependencies and Libraries
- SentenceTransformers/torch (already present).
- Optional eval deps (e.g., sklearn) only if not already available; keep minimal.

## Testing Strategy
- Unit: manifest read/write, config toggles, eval metrics, loader selection.
- Integration: small eval run comparing base vs tuned on fixtures; ingestion with tuned model (mock).
- Regression: baseline fallback when tuned path missing; tracing logs include metadata.

## Success Criteria
- [ ] Training produces versioned artifact + manifest with dataset fingerprint.
- [ ] Eval harness reports recall@k on held-out pairs and compares vs baseline.
- [ ] Config toggles switch between tuned and baseline safely.
- [ ] Ingestion/retrieval logs/traces include embedding metadata.
- [ ] Docs and validation notes updated.

## Notes and Considerations
- Keep heavy training/eval opt-in; document the env flags.
- Ensure GPU detection uses existing device helper; allow CPU fallback.
- Be mindful of logging PII; fingerprints should not expose raw text.

---
*This plan is ready for execution with `/execute-plan PRPs/requests/18-next_steps_finetuned_embeddings_execution.md`*
