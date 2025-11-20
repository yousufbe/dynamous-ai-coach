# Fixture Corpus for Ingestion Smoke Tests

Purpose:
- Provide a tiny, synthetic corpus for exercising the RAG ingestion pipeline without touching real documents.
- Keep ingestion runs fast and easy to validate.

Contents:
- `sample-handbook.md` — mission, data handling standards, and support channels.
- `sample-runbook.txt` — quick runbook for running the ingestion CLI with this fixture set.

Recommended ingestion command:

```bash
export RAG_SOURCE_DIRS=\"documents/fixtures\"  # isolates fixtures from other docs
export RAG_DATABASE_URL=\"postgresql://USER:PASSWORD@HOST:PORT/DBNAME\"
export QWEN_API_KEY=\"sk-...\"                # embedding service token
uv run python -m src.rag_pipeline.cli --output-format text
```

Notes:
- Leave `RAG_SOURCE_DIRS` unset to ingest all documents; set it as above to only process fixtures.
- Expect the CLI summary to show chunk counts for the two fixture files; use it as a quick health check.
- If ingestion fails, rerun after fixing credentials or connectivity; clean up partial rows for the fixture paths if needed.
