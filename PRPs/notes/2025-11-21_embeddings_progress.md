# Fine-tuned embeddings progress (2025-11-21)

## What changed
- Added fine-tuned embedding slice: training (`train.py`), manifest (`manifest.py`), evaluation (`eval.py`), local client, factory selector, and runner script (`scripts/run_embedding_eval.py`).
- Introduced embedding client protocol + model metadata to pipeline, retrieval, and agent; ingestion/retrieval now log `embedding_model` and dataset fingerprint when available.
- Config toggles added: `USE_FINE_TUNED_EMBEDDINGS` and `EMBEDDING_MODEL_FINE_TUNED_PATH` (RAG overrides supported). Docs updated in `README.md` and `docs/rag_pipeline_ingestion.md`.
- Tests created for manifest/train/eval/local client/factory plus config tests; embeddings data prep remains from prior phase.

## Validation
- `.venv/bin/ruff check src tests`
- `.venv/bin/mypy src`
- `.venv/bin/python -m pytest tests/rag_pipeline/embeddings -v`
- `.venv/bin/python -m pytest tests/shared/test_config.py tests/rag_pipeline/test_config.py -v`
- Fine-tuned ingestion smoke (demo model, dim=384): ran `RAG_FORCE_REINGEST=true` against `documents/fixtures` with Postgres `postgresql://postgres:temp123@127.0.0.1:5439/postgres`, schema `rag`, tables `sources/chunks`, and env `RAG_EMBEDDING_DIMENSION=384`; ingestion succeeded (3 docs, 6 chunks) using the local model with `dataset_fingerprint=smoke-fp`, `artifact_version=demo-smoke`. Pinned `CUDA_VISIBLE_DEVICES=0`.

## Notes
- Factory will prefer fine-tuned model when `use_fine_tuned_embeddings` is true and a model path is provided; otherwise falls back to Qwen HTTP client.
- Manifest metadata (dataset_fingerprint, artifact_version) emitted in logs/spans when present.
