# Post-Ingestion Validation Summary — 2025-11-21

This note captures the latest validation evidence after aligning documentation
and enabling retrieval-backed chat. All commands were run from the repo root
using the project virtualenv binaries.

## Validation Commands

| Command | Result | Notes |
| --- | --- | --- |
| `.venv/bin/ruff check src tests` | ✅ Pass | Includes new embedding client/protocol modules. |
| `.venv/bin/mypy src` | ✅ Pass | Strict mode clean. |
| `.venv/bin/python -m pytest tests/rag_pipeline/embeddings -v` | ✅ 12 passed | Covers data prep, manifest, train/eval harness, factory selectors, and local client. |
| `.venv/bin/python -m pytest tests/shared/test_config.py tests/rag_pipeline/test_config.py -v` | ✅ 11 passed | Confirms new fine-tuned flags and ingestion config parsing. |
| `.venv/bin/pytest tests -v` | ✅ 48 passed, 1 skipped | Performance benchmark marked `@pytest.mark.performance` remains skipped; GPU1 capability warning still emitted by PyTorch. |
| Fine-tuned ingestion smoke | ✅ Pass | Using `RAG_DATABASE_URL=postgresql://postgres:temp123@127.0.0.1:5439/postgres`, `RAG_SUPABASE_SCHEMA=rag`, `RAG_EMBEDDING_DIMENSION=384`, `RAG_FORCE_REINGEST=true`, and `USE_FINE_TUNED_EMBEDDINGS=true` with model path `models/fine_tuned/demo`; ingested 3 fixture docs (6 chunks) with `dataset_fingerprint=smoke-fp`, `artifact_version=demo-smoke`. |
| `RUN_PERFORMANCE=1 .venv/bin/pytest tests/performance -m performance` | ⚠️ Skipped | Set `RUN_PERFORMANCE=1` to enable the throughput benchmark; left skipped on this pass. |

## Tooling & Environment

- Python 3.12.3, ruff 0.14.5, mypy 1.18.2, pytest 9.0.1 (virtualenv binaries).
- Tests run with the full suite; `tests/performance/test_ingestion_performance.py::test_ingestion_performance_baseline` is marked `@pytest.mark.performance` and skips by default.

## Code Adjustments

- Correlation IDs now propagate through `/chat` → retrieval → LLM and embedding logs, enabling end-to-end traceability.
- FastAPI `/chat` endpoint logs include `correlation_id` alongside payload metrics.

## Known Follow-Ups

- Performance benchmark suite (`tests/performance`) remains deselected; set `RUN_PERFORMANCE=1` to run it on suitable hardware.
- If retrieval/LLM configuration changes, re-run the toolchain and update this note to keep dates/results fresh.
- Fixture-only ingestion runs are acceptable for smoke tests; set `RAG_SOURCE_DIRS=documents/fixtures` when you only need to validate the pipeline wiring.
- PyTorch warns that GPU1 (GTX 1060, sm_61) is unsupported for the current build; pin to `CUDA_VISIBLE_DEVICES=0` to keep work on the RTX 3080.

## Retrieval and LLM Log Fields

- `retrieval_started`: `query_length`, `top_k`, `min_score`, `correlation_id`
- `retrieval_completed`: `results_count`, `duration_ms`, `correlation_id`
- `retrieval_failed`: `error`, `correlation_id`
- `llm_call_completed`: `duration_ms`, `retry_count`, `correlation_id`
- `llm_call_failed`: `attempt`, `error`, `correlation_id`
- Embedding batches log `embedding_batch_started` / `embedding_batch_succeeded` / `embedding_batch_failed` with `correlation_id` when provided by callers. When the fine-tuned local client is enabled, logs include `embedding_model`, `embedding_dataset_fingerprint`, and `artifact_version`; tracer spans carry the same attributes.

## Fine-tuned ingestion notes

- Demo smoke used `models/fine_tuned/demo` (MiniLM 384-dim) and required setting `RAG_EMBEDDING_DIMENSION=384` plus altering `rag.chunks.embedding` to `vector(384)` to match the tuned model. If you swap models, align both the env dimension and table type.
- Pinned `CUDA_VISIBLE_DEVICES=0` during the run to avoid unsupported GPU warnings. PyTorch still logs warnings for older GPUs; safe to ignore for CPU/primary GPU-only runs.
- Langfuse tracing is available when `LANGFUSE_ENABLED=true` with host `http://127.0.0.1:3000` (worker `http://127.0.0.1:3030`); install the optional `langfuse` package and supply `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` (placeholders live in `.env.example`). Tracing is a no-op when disabled or keys are absent.

## GPU Selection Checklist

- Export `CUDA_VISIBLE_DEVICES=0` to prefer the primary GPU (3080).
- Ensure `GPU_DEVICE=cuda:0` (default) so logs reflect the intended device.
- Run a short workload and confirm `nvidia-smi` shows GPU 0 utilization; warnings are logged if CUDA is unavailable (fallback to CPU).

## Fixture Ingestion Checklist (Smoke Test)

- Environment variables: `RAG_DATABASE_URL` and `QWEN_API_KEY` exported; optionally `RAG_SOURCE_DIRS=documents/fixtures`.
- Command exits 0: `uv run python -m src.rag_pipeline.cli --output-format text`.
- CLI summary shows both fixture files (`sample-handbook.md`, `sample-runbook.txt`) with non-zero chunk counts.
- No embedding or database errors reported in the run log.
