---
description: Audit plan assumptions and project direction using Archon task tracking
argument-hint: [optional-scope-or-focus-area]
---

# Audit Plan Assumptions & Delivery Direction

Use this command to verify that the documented assumptions in the numbered plans remain accurate, confirm foundational work is done in the right order, and publish the results as an Archon-tracked task with a summary in the task description. If an argument is provided, treat it as the specific focus area or milestone to emphasize during the audit.

## Step 0: Gather Context (mandatory)
- Read `AGENTS.md` for core principles (type safety, KISS/YAGNI, docstring style) and the fine-tuned embeddings strategy.
- Read `README.md` plus `docs/architecture.md`, `docs/rag_pipeline_ingestion.md`, `docs/hybrid_search.md`, and `docs/post_ingestion_validation.md` to align with the current architecture, ingestion flow, and validation status.
- Review all plans in `PRPs/requests/` **in ascending numeric order (1 → 8)** to respect chronology: ingestion foundations, remaining work, validation, hardening/performance, end-to-end UX, retrieval/LLM integration, grounded chat. Note every explicit assumption and prerequisite they state.
- Skim `PRPs/ai_docs/` guides (tool, logging, testing, fine-tuned embeddings) when those topics appear in the plans.

## Step 1: Map Reality vs. Assumptions
- Inspect the current code paths that the plans rely on (e.g., `src/rag_pipeline/*`, `src/agent/agent.py`, `src/main.py`, `src/tools/ingestion_skill/*`, tests under `tests/`).
- For each plan, list its assumptions and mark them as `true/right now`, `partially true`, or `outdated/missing`, citing file paths and evidence (code, tests, docs).
- Identify foundational gaps (ingestion completeness, retrieval wiring, frontend/backend contract, validation coverage) before later-phase work starts.

## Step 2: Direction & Priority Check
- Confirm that critical-path tasks (ingestion reliability → validation → retrieval/LLM wiring → frontend alignment → performance/hardening) are either done or scheduled before downstream tasks.
- Propose a short, ordered list of the next 3–5 actions that unblock the roadmap, respecting the plan chronology and KISS/YAGNI.
- Call out risks or dependencies (e.g., missing Postgres/PGVector setup, absent tests, doc drift from `docs/post_ingestion_validation.md`).

## Step 3: Archon Task Management (required)
- Follow `.codex/skills/archon/SKILL.md`: read `references/api_reference.md`, ask for the Archon host (default `http://localhost:8181`), and verify the connection.
- Check for an existing project reference in the plans (e.g., “End-to-End Developer & User Experience” with `project_id=fbe94a2b-1226-4e38-b094-f3a66cdedbb2` in `PRPs/requests/8-rag_grounded_chat_next_steps_plan.md`) or `AGENTS.md`. Reuse it if present; otherwise create a new project for the audit.
- Create a task named “Assumption & Direction Audit” (status `todo`), then move it to `in_progress` while working.
- When the audit is complete, update the task to `done` **and overwrite the task description with a concise summary** (assumptions validated/invalidated, key gaps, top actions). Example:
  ```python
  from scripts.archon_client import ArchonClient
  client = ArchonClient(base_url=archon_host)
  client.update_task(
      task_id="task-uuid",
      updates={
          "status": "done",
          "description": "Assumptions audit summary:\n- Plans 1–4 assumptions hold except ...\n- Gaps: ...\n- Next actions: 1) ..., 2) ..."
      }
  )
  ```
- Create follow-up Archon tasks for any gaps you find, preserving priority implied by the numbered plans.

## Step 4: Deliverables
- A written audit (can live in the Archon task description and/or a short note in `PRPs/requests/` if needed) that includes:
  - Assumption status per plan (1–8) with evidence.
  - Direction check (are foundations done first?) and the prioritized next 3–5 steps.
  - Risks, blockers, and any doc/code/test drift to fix.
- Report back with the Archon project/task IDs used, the final task description summary, and any new tasks created for gaps.
