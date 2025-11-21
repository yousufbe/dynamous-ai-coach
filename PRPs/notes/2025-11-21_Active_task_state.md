## Active Task State — 2025-11-21

- Completed steps: Opt-in Langfuse/no-op tracing with correlation IDs; validation docs refreshed (2025-11-21) and observability updates; Archon tasks/results registered; GPU priority plan implemented (GPU_DEVICE default cuda:0) with device logging and docs; validation clean (ruff/mypy/pytest), performance suite skipped by marker.
- Current step: Ready to run GPU-pinned workloads (use CUDA_VISIBLE_DEVICES=0) and optionally enable Langfuse; no blocking actions in flight.
- Lessons learned: Torch warns about GPU1 (1060) capability mismatch; pin CUDA_VISIBLE_DEVICES=0 to prefer 3080; tracing must remain no-op safe when disabled.
- Decisions affecting future steps: Default device is cuda:0 with CPU fallback logging; Archon host http://localhost:8181 is active; Langfuse endpoints http://127.0.0.1:3000 (web) / :3030 (worker).
- Remaining stages: (1) Enable Langfuse in prod-like runs if desired; (2) Run GPU-pinned smoke tests to confirm GPU0 utilization; (3) Refresh validation after config/model changes; (4) Optional: adjust torch build if 1060 warnings need suppression.
- Requirements/constraints: KISS/YAGNI; strict typing/mypy/ruff; Google-style docstrings; keep docs aligned; do not revert user changes; Archon tracking under project fbe94a2b-1226-4e38-b094-f3a66cdedbb2.
