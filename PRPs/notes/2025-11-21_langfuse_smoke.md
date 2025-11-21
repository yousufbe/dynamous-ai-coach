# Langfuse Smoke — 2025-11-21

Attempted to verify Langfuse spans end-to-end.

- Environment: `LANGFUSE_ENABLED=true`, `LANGFUSE_HOST=http://127.0.0.1:3000`.
- No `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` present, so tracer logged `tracing_langfuse_missing_keys` and fell back to no-op.
- Action needed: provide valid Langfuse public/secret keys, then rerun `/chat` (or a small span via `src/shared/tracing`) to confirm traces land in Langfuse web at `http://127.0.0.1:3000` (worker `http://127.0.0.1:3030`).

Status: **blocked on credentials**; fallback is safe in the meantime.
