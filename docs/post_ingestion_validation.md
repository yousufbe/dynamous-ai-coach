# Post-Ingestion Validation Summary — 2025-11-20

This note captures the latest validation evidence after aligning documentation
and enabling retrieval-backed chat. All commands were run from the repo root
using the project virtualenv binaries.

## Validation Commands

| Command | Result | Notes |
| --- | --- | --- |
| `.venv/bin/ruff check src tests` | ✅ Pass | No findings. |
| `.venv/bin/mypy src` | ✅ Pass | Strict mode clean. |
| `.venv/bin/pytest tests -m "not performance"` | ✅ 45 passed, 1 deselected | One performance suite deselected by marker. |

## Tooling & Environment

- Python 3.12.3, ruff 0.14.5, mypy 1.18.2, pytest 9.0.1 (virtualenv binaries).
- Tests run with `-m "not performance"` to keep performance benchmarks opt-in.

## Code Adjustments

- No code changes were required for this validation run; prior adjustments (Docling backend hardening, pipeline/config typing, Archon skill docstring) remain in place.

## Known Follow-Ups

- Performance benchmark suite (`tests/performance`) remains deselected; run manually on suitable hardware.
- If retrieval/LLM configuration changes, re-run the toolchain and update this note to keep dates/results fresh.
- Fixture-only ingestion runs are acceptable for smoke tests; set `RAG_SOURCE_DIRS=documents/fixtures` when you only need to validate the pipeline wiring.

## Fixture Ingestion Checklist (Smoke Test)

- Environment variables: `RAG_DATABASE_URL` and `QWEN_API_KEY` exported; optionally `RAG_SOURCE_DIRS=documents/fixtures`.
- Command exits 0: `uv run python -m src.rag_pipeline.cli --output-format text`.
- CLI summary shows both fixture files (`sample-handbook.md`, `sample-runbook.txt`) with non-zero chunk counts.
- No embedding or database errors reported in the run log.
