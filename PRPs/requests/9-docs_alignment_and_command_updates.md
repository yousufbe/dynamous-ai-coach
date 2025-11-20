# Implementation Plan: Documentation Alignment & Command Guardrails

## Overview
Align project documentation with the current retrieval-enabled agent, clarify the ingestion CLI status, fix Archon skill path references, and add workflow guardrails so future changes explicitly update docs (README, AGENTS, key guides). This plan updates the numbered plans sequence (now entry 9) and enforces doc freshness in the `.codex/commands` tooling.

## Requirements Summary
- Refresh user-facing docs to match the current code: grounded chat flow, retrieval requirements, ingestion CLI availability.
- Fix incorrect path references in the Archon skill docs to point to `.codex/skills/archon`.
- Update validation notes to reflect that the last recorded run is dated and highlight the need for a refresh.
- Add command-level guardrails so plan/execution flows require documentation updates after code changes.
- Keep AGENTS.md principles (type safety, KISS/YAGNI, Google-style docstrings) in mind when editing.

## Research Findings
### Best Practices
- Keep README/architecture docs accurate to current behaviour; inaccuracies erode trust and onboarding speed.
- Command automation should include documentation update checkpoints to prevent drift.
- Validation logs should be dated and indicate when re-runs are needed to avoid misrepresenting test status.
- Path references in docs must match the actual repo layout to prevent broken instructions.

### Reference Implementations
- Current code paths: `src/agent/agent.py`, `src/agent/llm_client.py`, `src/rag_pipeline/cli.py` (retrieval + CLI implemented).
- Existing docs to realign: `README.md`, `docs/architecture.md`, `docs/rag_pipeline_ingestion.md`, `docs/archon_SKILL.md`, `docs/post_ingestion_validation.md`.
- Workflow commands to harden: `.codex/commands/create-plan.md`, `.codex/commands/execute-plan.md`.

## Implementation Tasks

### Phase 1: Documentation Alignment
1. **Update README to current chat behaviour**
   - Description: Replace placeholder-chat messaging with accurate retrieval/LLM behaviour, including fallback behaviour when DB/LLM endpoints are missing.
   - Files: `README.md`
   - Dependencies: Confirm behaviour from `src/agent/agent.py`, `src/agent/llm_client.py`.
   - Effort: 1h

2. **Refresh architecture doc status**
   - Description: Adjust “Current implementation status” to note retrieval-enabled chat and fallback behaviours; remove outdated placeholder language.
   - Files: `docs/architecture.md`
   - Effort: 0.5h

3. **Clarify ingestion CLI availability & references**
   - Description: Update `docs/rag_pipeline_ingestion.md` to state the CLI is implemented and remove “once implemented” phrasing; ensure guidance matches current CLI.
   - Files: `docs/rag_pipeline_ingestion.md`
   - Effort: 0.5h

4. **Fix Archon skill path references**
   - Description: Replace `.claude/skills/archon/...` with `.codex/skills/archon/...` in the skill doc to match the repo layout.
   - Files: `docs/archon_SKILL.md`
   - Effort: 0.25h

5. **Mark validation snapshot as historical**
   - Description: Update `docs/post_ingestion_validation.md` to clearly date the last run and note that a fresh validation is required post-retrieval wiring.
   - Files: `docs/post_ingestion_validation.md`
   - Effort: 0.25h

### Phase 2: Workflow Guardrails
6. **Enforce doc updates in plan command**
   - Description: Amend `.codex/commands/create-plan.md` to instruct authors to include documentation update tasks for README/AGENTS/key docs when plans change behaviour.
   - Files: `.codex/commands/create-plan.md`
   - Effort: 0.25h

7. **Enforce doc updates in execute command**
   - Description: Amend `.codex/commands/execute-plan.md` to require doc synchronization before marking tasks complete (README, AGENTS, relevant docs/PRPs).
   - Files: `.codex/commands/execute-plan.md`
   - Effort: 0.25h

### Phase 3: Validation & Archon Handoff
8. **Documentation pass sanity check**
   - Description: Spot-check updated docs for consistency (chat flow, CLI references, paths), ensuring no contradictory statements remain.
   - Files: Updated docs above
   - Effort: 0.25h
9. **Archon tracking (optional on availability)**
   - Description: If Archon is available, log this doc/command alignment as tasks and mark completion; otherwise record next steps in PR/notes.
   - Files: Archon tasks (no code changes)
   - Effort: 0.25h

## Codebase Integration Points
- `README.md`, `docs/architecture.md`, `docs/rag_pipeline_ingestion.md`, `docs/post_ingestion_validation.md`, `docs/archon_SKILL.md`
- `.codex/commands/create-plan.md`, `.codex/commands/execute-plan.md`

## Technical Design
- No code architecture changes; documentation text and command instructions only.
- Ensure descriptions of retrieval/LLM reflect actual fallback behaviour when endpoints/DB URLs are absent.

## Testing Strategy
- Manual doc review for consistency.
- (Optional) Run `uv run ruff check src/ && uv run mypy src/ && uv run pytest tests/` if environment is available to refresh `post_ingestion_validation.md`.

## Success Criteria
- Placeholder/incorrect statements removed; docs accurately describe retrieval-enabled chat and existing CLI.
- Archon skill doc paths corrected.
- Commands enforce documentation updates as part of planning/execution.
- Validation note clearly marked as historical with guidance to rerun.

---
*This plan is ready for execution with `/execute-plan PRPs/requests/9-docs_alignment_and_command_updates.md`.*
