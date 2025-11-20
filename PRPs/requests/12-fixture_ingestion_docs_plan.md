# Implementation Plan: Surface Fixture Ingestion Path

## Overview
Document the new fixture corpus (`documents/fixtures/`) so contributors can ingest a small, synthetic dataset without touching user documents. Add concise instructions to the README and ingestion docs, and note the fixture option in validation guidance.

## Requirements Summary
- Follow AGENTS.md: keep changes simple, typed code untouched, and lean on documentation updates.
- Do not modify existing user documents under `documents/`; keep fixtures isolated.
- Highlight `RAG_SOURCE_DIRS` usage to target fixtures.
- Keep additions concise and actionable.

## Research Findings
### Best Practices
- Provide a one-liner to set `RAG_SOURCE_DIRS` before running the ingestion CLI.
- Keep fixture instructions close to existing ingestion steps to reduce friction.

### Reference Implementations
- README.md already outlines ingestion commands and env vars.
- docs/rag_pipeline_ingestion.md documents ingestion env vars.
- docs/post_ingestion_validation.md logs validation runs and notes on data inputs.

### Technology Decisions
- Documentation-only; no code or dependency changes.
- Use existing CLI command: `uv run python -m src.rag_pipeline.cli --output-format text`.

## Implementation Tasks

### Phase 1: Documentation Updates
1. **Add fixture option to README ingestion steps**
   - Description: Mention `documents/fixtures/` as a ready-to-use corpus and show `RAG_SOURCE_DIRS=documents/fixtures` with the ingestion command.
   - Files to modify/create: `README.md`
   - Dependencies: None
   - Estimated effort: 0.3h

2. **Update ingestion guide with fixture targeting**
   - Description: Add a short note in `docs/rag_pipeline_ingestion.md` that shows using `RAG_SOURCE_DIRS=documents/fixtures` to limit ingestion to fixtures.
   - Files to modify/create: `docs/rag_pipeline_ingestion.md`
   - Dependencies: Task 1 (keep terminology consistent)
   - Estimated effort: 0.2h

3. **Add validation note pointing to fixtures**
   - Description: In `docs/post_ingestion_validation.md`, add a brief reminder that fixture-only runs are acceptable for smoke tests.
   - Files to modify/create: `docs/post_ingestion_validation.md`
   - Dependencies: Task 2 (reuse language)
   - Estimated effort: 0.2h

## Codebase Integration Points
### Files to Modify
- `README.md` - add fixture ingestion example.
- `docs/rag_pipeline_ingestion.md` - highlight fixture-targeted ingestion via `RAG_SOURCE_DIRS`.
- `docs/post_ingestion_validation.md` - note fixture usage for validation smoke tests.

### Existing Patterns to Follow
- Keep documentation concise and actionable; align with existing ingestion command formatting.
- Maintain Google-style doc clarity where applicable to code (not touched here).

## Technical Design
- No code changes; documentation only.

## Dependencies and Libraries
- None beyond existing project requirements.

## Testing Strategy
- Manual validation: ensure the added commands reference `documents/fixtures/` and match the existing CLI invocation.
- No automated tests required for documentation updates.

## Success Criteria
- [ ] README shows fixture-targeted ingestion command.
- [ ] Ingestion guide mentions fixture targeting.
- [ ] Validation doc notes fixture-friendly runs for smoke tests.

## Notes and Considerations
- Keep fixture instructions optional and clearly marked to avoid confusion with production ingestion.
