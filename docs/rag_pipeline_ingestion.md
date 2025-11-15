# Docling RAG Ingestion Pipeline

This document describes how to configure and operate the Docling-based hybrid
RAG ingestion pipeline. The pipeline scans local folders, converts documents
with Docling, generates Qwen embeddings and stores results in Supabase/
PostgreSQL with PGVector, `tsvector` and trigram indexes.

## Required Environment Variables

| Variable | Description | Default |
| --- | --- | --- |
| `RAG_SOURCE_DIRS` | Comma-separated directories to scan. | `./documents` |
| `RAG_SUPPORTED_EXTENSIONS` | Optional comma-separated list of file extensions. | `pdf,docx,doc,pptx,ppt,xlsx,xls,md,markdown,txt` |
| `RAG_CHUNK_MIN_CHARS` | Minimum characters per chunk before merging. | `400` |
| `RAG_CHUNK_MAX_CHARS` | Maximum characters per chunk before splitting. | `1000` |
| `RAG_CHUNK_OVERLAP_CHARS` | Desired overlap when slicing long chunks. | `60` |
| `RAG_DOCLING_TARGET_TOKENS` | Target token count for Docling HybridChunker. | `280` |
| `RAG_DOCLING_LANGUAGE` | Language hint used by Docling tokeniser. | `en` |
| `RAG_EMBEDDING_MODEL` | Embedding model identifier. | `Qwen/Qwen3-Embedding-0.6B` |
| `RAG_EMBEDDING_BATCH_SIZE` | Chunk batch size for embedding calls. | `8` |
| `RAG_EMBEDDING_RETRY_COUNT` | Number of automatic retries on failures. | `1` |
| `RAG_EMBEDDING_TIMEOUT_SECONDS` | Timeout per embedding request. | `60` |
| `RAG_EMBEDDING_RETRY_BACKOFF_SECONDS` | Base backoff between retries. | `2.0` |
| `RAG_EMBEDDING_DIMENSION` | Expected embedding dimension for validation. | `1024` |
| `RAG_DATABASE_URL` | Supabase/PostgreSQL connection string. | _empty (required for persistence)_ |
| `RAG_SUPABASE_SCHEMA` | Schema that holds `sources` and `chunks`. | `public` |
| `RAG_SOURCES_TABLE` | Name of the sources table. | `sources` |
| `RAG_CHUNKS_TABLE` | Name of the chunks table. | `chunks` |
| `RAG_FORCE_REINGEST` | Set to `true` to reprocess all documents. | `false` |
| `RAG_PIPELINE_ID` | Identifier for run logs/metrics. | `local-dev` |
| `QWEN_API_KEY` | API key used by the embedding client. | _empty_ |
| `QWEN_EMBEDDING_BASE_URL` | Override base URL for Qwen embeddings. | DashScope default |

All variables are consumed by `src/rag_pipeline/config.py`. When running in
Docker Compose, set them inside the ingestion service container so both the
CLI and the ingestion skill share the same configuration.

## CLI Usage

The CLI provides a batch-friendly entry point once `src/rag_pipeline/cli.py`
is implemented. Example invocation:

```bash
uv run python -m src.rag_pipeline.cli \
  --source-dir /data/docs --source-dir /data/manuals \
  --force-reingest=false \
  --pipeline-id nightly-docling
```

The CLI reads environment variables first and then applies command-line
overrides. It prints a JSON summary containing documents processed, failures,
and chunk statistics. A non-zero exit code indicates at least one document
failed to ingest.

### CLI Options

- `--source-dir /path`: Override directories defined by the config. Specify
  multiple times to ingest multiple roots.
- `--glob "*.md"`: Restrict discovery to particular glob patterns.
- `--force-reingest`: Ignore cached content hashes and reprocess everything.
- `--pipeline-id nightly` : Override the pipeline identifier for a single run.
- `--output-format json`: Emit structured JSON instead of human-readable text.

### Quick Start

1. Populate your document folders under `./documents` or override with
   `--source-dir`.
2. Set `RAG_DATABASE_URL` and `QWEN_API_KEY`.
3. Run `uv run python -m src.rag_pipeline.cli --output-format text`.
4. Inspect logs for `document_ingestion_completed` and confirm the summary.

### Skill Invocation

The ingestion skill can be triggered programmatically by constructing an
`IngestionSkillRequest` and calling `run_ingestion_skill`. The agent exposes an
`ingestion_skill` tool so multi-agent orchestrators can refresh documents on
demand. The tool docstring documents when to use it, when to avoid it (e.g.,
for querying knowledge), and what response formats are available.

## Supabase/PostgreSQL Setup

1. Enable required extensions: `vector`, `pg_trgm`.
2. Apply `PRPs/examples/rag_pipeline_docling_supabase.sql` to create the
   `rag.sources` and `rag.chunks` tables plus indexes and the `match_chunks`
   helper function.
3. Store the database URL (service role key when using Supabase) inside
   `RAG_DATABASE_URL`. Limit access to the ingestion service via row-level
   security rules if exposing through Supabase APIs.

## Observability

Every ingestion run logs:

- Pipeline identifier (`RAG_PIPELINE_ID` or CLI override)
- Document path, detected type, and content hash
- Number of generated chunks and embedding model version
- Embedding retry attempts and eventual error messages

Use these logs together with Archon task metadata to trace ingestion jobs and
debug failures quickly. Continuous runs should export metrics (document count,
chunk count, failure rate) to your preferred monitoring stack.

## Troubleshooting

| Symptom | Resolution |
| --- | --- |
| `discovery_directory_missing` | Verify the configured directories exist and that the CLI user has read permissions. |
| `Failed to reach Qwen embeddings endpoint` | Ensure `QWEN_API_KEY` is set and the base URL is reachable from your network. |
| Database errors | Confirm `RAG_DATABASE_URL` points to a reachable instance and that migrations from `PRPs/examples/rag_pipeline_docling_supabase.sql` have been applied. |
| Docling import errors | Install the `docling` optional dependency or rely on the fallback text chunker. |

## Benchmarking

A baseline performance fixture lives under `tests/performance/test_ingestion_performance.py`.
It is marked with `@pytest.mark.performance` and skipped by default. Run it manually
to gauge throughput on your hardware when experimenting with different chunk sizes
or embedding batch sizes.
