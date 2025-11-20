# Implementation Plan: Fixture Corpus and Archon Tracking

## Overview
Prepare a minimal fixture corpus and companion instructions so the RAG ingestion pipeline can be exercised end-to-end without touching production data. Track the work in Archon to keep visibility on ingestion readiness tasks.

## Requirements Summary
- Follow AGENTS.md principles: keep changes simple (KISS/YAGNI) and avoid risky refactors; maintain type-safety expectations even though this work is documentation-focused.
- Use the default document root (`./documents`) and `RAG_SOURCE_DIRS` override noted in README.md.
- Provide actionable guidance to run `uv run python -m src.rag_pipeline.cli --output-format text` once `RAG_DATABASE_URL` and `QWEN_API_KEY` are set.
- Avoid disturbing existing user-provided documents under `documents/`.

## Research Findings
### Best Practices
- Keep fixture content lightweight and clearly scoped so ingestion runs quickly and does not pollute production corpora.
- Document the fixture location and required env vars alongside the ingestion command to reduce setup friction.

### Reference Implementations
- README.md: ingestion steps (use `./documents` by default and set `RAG_SOURCE_DIRS` when pointing to alternative folders).
- docs/rag_pipeline_ingestion.md: environment variables for chunking and embedding configuration.

### Technology Decisions
- Use plain Markdown/text fixtures; no code changes or new dependencies.
- Keep fixtures in a dedicated subfolder (`documents/fixtures/`) to separate them from user documents.

## Implementation Tasks

### Phase 1: Tracking and Setup
1. **Create Archon project and tasks for fixture ingestion work**
   - Description: Ensure Archon project exists and register all tasks from this plan with status `todo`.
   - Files to modify/create: None.
   - Dependencies: None.
   - Estimated effort: 0.5h.

### Phase 2: Fixture Corpus
2. **Add dedicated fixture folder with small sample documents**
   - Description: Create `documents/fixtures/` and add 2–3 concise Markdown/text files that describe synthetic company policies/processes for ingestion smoke tests.
   - Files to modify/create: `documents/fixtures/README.md`, `documents/fixtures/sample-handbook.md`, `documents/fixtures/sample-runbook.txt` (or similar).
   - Dependencies: Task 1 (tracking in Archon).
   - Estimated effort: 0.5h.

3. **Document ingestion instructions for the fixture corpus**
   - Description: Add a short README in the fixture folder with the exact command and env vars needed to ingest only the fixtures (using `RAG_SOURCE_DIRS=documents/fixtures`).
   - Files to modify/create: `documents/fixtures/README.md`.
   - Dependencies: Task 2 (fixture folder exists).
   - Estimated effort: 0.25h.

## Codebase Integration Points
### Files to Modify
- `documents/fixtures/README.md` - Describe fixture contents and ingestion command.
- `documents/fixtures/sample-handbook.md` - Sample policy content.
- `documents/fixtures/sample-runbook.txt` - Sample runbook/process notes.

### New Files to Create
- `documents/fixtures/README.md` - Usage and ingestion guidance for fixtures.
- `documents/fixtures/sample-handbook.md` - Synthetic handbook text for chunking.
- `documents/fixtures/sample-runbook.txt` - Synthetic runbook text for process/resolution steps.

### Existing Patterns to Follow
- Keep documentation concise and actionable, matching README.md guidance for ingestion commands and env vars.
- Avoid modifying existing user documents; keep fixtures isolated.

## Technical Design

### Architecture Diagram (if applicable)
Not applicable; this work adds fixture content and documentation only.

### Data Flow
- Fixture files live in `documents/fixtures/`.
- Ingestion runs with `RAG_SOURCE_DIRS=documents/fixtures` to feed chunks into the configured PGVector database.

### API Endpoints (if applicable)
Not applicable; no API changes.

## Dependencies and Libraries
- None beyond existing project requirements.

## Testing Strategy
- Manual: Run `RAG_SOURCE_DIRS=documents/fixtures uv run python -m src.rag_pipeline.cli --output-format text` (requires `RAG_DATABASE_URL` and `QWEN_API_KEY`).
- Verify the CLI reports successful chunk ingestion for the fixture files.
- Edge cases: Ensure command works when other documents exist in `documents/` and when `RAG_SOURCE_DIRS` is set to the fixture subfolder.

## Success Criteria
- [ ] Archon project created and tasks registered.
- [ ] Fixture files added under `documents/fixtures/` without altering existing documents.
- [ ] Fixture README documents ingestion steps and env vars.

## Notes and Considerations
- Keep fixture text small to avoid long ingestion runs and to make validation logs easy to read.
- If Archon is unavailable, log the failure and continue with local tracking, but retry Archon when possible.
