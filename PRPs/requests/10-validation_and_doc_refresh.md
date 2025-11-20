# Implementation Plan: Validation Refresh & Documentation Accuracy

## Overview
Re-run the validation toolchain (ruff, mypy, pytest) against the current retrieval-enabled codebase, refresh `docs/post_ingestion_validation.md` with up-to-date results, and sanity-check user-facing docs (README/architecture/ingestion) plus AGENTS.md assumptions for accuracy after recent changes. This continues the numbered plans as entry 10.

## Requirements Summary
- Execute and capture `ruff`, `mypy`, and `pytest` results on the current code.
- Update `docs/post_ingestion_validation.md` with the new run date, commands, pass/fail status, and notes.
- Spot-check README, `docs/architecture.md`, `docs/rag_pipeline_ingestion.md`, and AGENTS.md for any remaining inaccuracies after the retrieval/LLM integration and recent doc edits.
- Keep edits aligned with AGENTS.md principles (type safety, KISS/YAGNI, Google-style docstrings).

## Research Findings
- Prior validation snapshot (2025-11-15) is stale; retrieval wiring and docs have since changed.
- AGENTS.md already states toolchain commands; docs now describe grounded chat with fallbacks, so only deltas discovered during validation need updates.
- Commands (`create-plan`, `execute-plan`) now require doc updates; this validation should ensure the documented state matches actual results.

## Implementation Tasks

### Phase 1: Environment Check
1. **Verify tooling availability**
   - Description: Confirm `uv`/Python environment and binaries for ruff, mypy, pytest are present.
   - Commands: `python --version`, `uv --version` (if available), `ruff --version`, `mypy --version`, `pytest --version`.
   - Effort: 0.25h.

### Phase 2: Run Validation
2. **Run ruff**
   - Description: `uv run ruff check src/ tests/` (or `ruff check src tests` if uv not present). Capture output.
   - Effort: 0.5h.
3. **Run mypy**
   - Description: `uv run mypy src/` (or `mypy src`). Capture output and note any suppressions needed.
   - Effort: 0.75h.
4. **Run pytest**
   - Description: `uv run pytest tests/ -m "not performance"` (or `pytest tests -m "not performance"`). Capture summary.
   - Effort: 1h.

### Phase 3: Documentation Updates
5. **Refresh validation doc**
   - Description: Update `docs/post_ingestion_validation.md` with the new run date, commands, results, and any notes (e.g., skips, deselected suites).
   - Effort: 0.5h.
6. **Doc accuracy sweep**
   - Description: Re-read README, `docs/architecture.md`, `docs/rag_pipeline_ingestion.md`, and AGENTS.md to confirm they align with current behaviour; adjust if validation uncovered new notes (e.g., dependencies, fallbacks).
   - Effort: 0.5h.

### Phase 4: Wrap-Up
7. **Summarize outcomes**
   - Description: Note validation status and doc changes; if Archon is used, update or create a task with results and any follow-ups.
   - Effort: 0.25h.

## Codebase Integration Points
- `docs/post_ingestion_validation.md`
- README.md, `docs/architecture.md`, `docs/rag_pipeline_ingestion.md`, AGENTS.md (only if discrepancies are found during the sweep)

## Testing Strategy
- Primary: ruff, mypy, pytest (non-performance) runs.
- Secondary: manual doc review for consistency.

## Success Criteria
- Tooling commands executed and passing (or documented with actionable follow-ups).
- Validation doc updated with current date/results.
- Docs remain accurate with no lingering placeholder or stale guidance.

---
*This plan is ready for execution with `/execute-plan PRPs/requests/10-validation_and_doc_refresh.md`.*
