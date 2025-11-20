# Implementation Plan: Fixture Quickstart Crosslinks

## Overview
Surface the new fixture corpus in the architecture overview and provide a tiny validation checklist so contributors can smoke-test ingestion without real documents.

## Requirements Summary
- Keep changes KISS/YAGNI and documentation-only.
- Avoid touching user-provided documents; fixtures stay under `documents/fixtures/`.
- Reuse existing commands (`RAG_SOURCE_DIRS=documents/fixtures` + ingestion CLI).

## Research Findings
### Best Practices
- Place fixture references near quickstart/architecture guidance to reduce onboarding friction.
- Provide an expected-output checklist instead of screenshots to keep docs portable.

### Reference Implementations
- README ingestion section already mentions `RAG_SOURCE_DIRS=documents/fixtures`.
- docs/rag_pipeline_ingestion.md and docs/post_ingestion_validation.md mention fixture targeting.

### Technology Decisions
- Documentation updates only; no code or dependency changes.

## Implementation Tasks

### Phase 1: Crosslinking
1. **Add fixture mention to architecture quickstart path**
   - Description: Insert a brief note in `docs/architecture.md` pointing to `documents/fixtures/` and the `RAG_SOURCE_DIRS=documents/fixtures` command for first-run smoke tests.
   - Files to modify/create: `docs/architecture.md`
   - Dependencies: None
   - Estimated effort: 0.3h

### Phase 2: Validation Checklist
2. **Add expected-result checklist for fixture ingestion**
   - Description: Add a short checklist (env vars set, CLI exits 0, chunk counts shown) to `docs/post_ingestion_validation.md` or a new subsection so users know what “good” looks like for fixture runs.
   - Files to modify/create: `docs/post_ingestion_validation.md`
   - Dependencies: Task 1 (reuse the fixture reference)
   - Estimated effort: 0.2h

## Codebase Integration Points
### Files to Modify
- `docs/architecture.md` - quickstart crosslink to fixtures.
- `docs/post_ingestion_validation.md` - fixture ingestion expected-result checklist.

### Existing Patterns to Follow
- Keep prose concise and actionable; mirror existing doc tone and formatting.

## Technical Design
- Documentation-only adjustments; no architectural changes.

## Dependencies and Libraries
- None beyond existing project requirements.

## Testing Strategy
- Manual: ensure commands reference `documents/fixtures` and align with the current ingestion CLI.

## Success Criteria
- [ ] Architecture doc mentions fixture path for smoke tests.
- [ ] Validation doc lists the expected outputs/checks for fixture ingestion runs.

## Notes and Considerations
- Keep fixture guidance optional to avoid confusing production ingestion flows.
