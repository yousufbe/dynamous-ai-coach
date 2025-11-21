# Langfuse Smoke — 2025-11-21

Verified Langfuse ingestion end-to-end after fixing service env and credentials.

- Environment: `LANGFUSE_ENABLED=true`, `LANGFUSE_HOST=http://127.0.0.1:3000`, `LANGFUSE_PUBLIC_KEY=pk-lf-0lBMFVNpEA-e-z3zPGPZ5g`, `LANGFUSE_SECRET_KEY=sk-lf-eaWk_ujfXWuUvNoW_EdH8dilPdLv1nvII0jLQznDU1g`.
- Fixes applied: `ENCRYPTION_KEY` set to a 64-char hex value in `~/local-ai-packaged/.env`, Redis/Valkey now requires `LOCALONLYREDIS` to match Langfuse defaults, and Langfuse project/user/key seeded via `LANGFUSE_INIT_*` envs.
- Smoke: `src/shared/tracing.build_tracer` with correlation_id `plan16-smoke` wrote spans to ClickHouse (`clickhouse-client: select id,name,metadata from traces ...` shows entries for `plan16-smoke` with metadata `{check: ok}` and `{check: redis}`).
- Credentials location: `~/local-ai-packaged/.env` (mirrored in `.env.example` placeholders). UI available at `http://127.0.0.1:3000`, worker at `http://127.0.0.1:3030`.
- Key usage: correlation IDs are hashed into valid Langfuse trace IDs via `create_trace_id(seed=correlation_id)` in the tracer; metadata is attached through Langfuse OTEL spans.

Status: ✅ Langfuse tracing live; use the keys above for `/chat` or local tracer smoke.
