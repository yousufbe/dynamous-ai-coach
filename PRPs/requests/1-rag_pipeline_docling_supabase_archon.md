# Implementation Plan: Docling-Based Hybrid RAG Pipeline with Supabase and Archon‑Style Ingestion Skill

## Overview

This plan describes a comprehensive design and implementation roadmap for a local hybrid-search RAG pipeline that ingests company documents, converts them into semantically meaningful chunks using Docling’s HybridChunker, embeds those chunks with Qwen3‑Embedding‑0.6B, and stores them in a Supabase/PostgreSQL database with PGVector and lexical indexes. The pipeline will be exposed as a reusable Python library plus:

- A batch/cron‑friendly CLI for scheduled ingestion.
- An Archon‑style “ingestion skill” module that the AI assistant can invoke on demand.

The solution aligns with the project’s global constraints:

- Python, type‑safe, fully annotated code with strict mypy.
- KISS and YAGNI: focus on the minimal feature set needed for reliable ingestion and retrieval.
- Local, Dockerised Supabase/Postgres with PGVector, text search, and trigram indexes.
- Docling‑based hybrid chunking tuned to min/max character lengths via environment variables.
- Qwen3‑Embedding‑0.6B for dense vectors and Qwen3‑VL‑8B‑Instruct as the primary LLM.
- Clear extensibility to add future data sources and a fine‑tuned embeddings strategy.

The plan emphasizes modularity, observability, and testability so that the RAG pipeline can evolve without compromising correctness or maintainability.

---

## Requirements Summary

- Build a **RAG ingestion pipeline** that:
  - Discovers documents from one or more configured local directories.
  - Converts those documents to a structured representation using Docling.
  - Applies **hybrid chunking** to produce semantically coherent chunks with token and character bounds.
  - Generates dense embeddings using **Qwen3‑Embedding‑0.6B**.
  - Stores chunks, embeddings, and metadata in a **Supabase/PostgreSQL** database.
  - Supports **hybrid search** via both vector and lexical/pattern indexes.
- Ensure **idempotent ingestion**:
  - Before processing a document, check the database to determine whether it has already been ingested.
  - Use a stable `content_hash` or equivalent metadata to detect changes and avoid duplicate processing.
  - Support `force_reingest` for explicit re‑processing when required.
- Implement **robust embedding error handling**:
  - If an embedding call fails, retry once with backoff for transient issues.
  - If embedding still fails, mark the document as failed/partially ingested and record a clear error.
- **Make it easy to add new data sources**:
  - Use a small set of typed interfaces for “document sources” that can be implemented by additional adapters later (e.g., Supabase Storage, S3, Google Drive).
  - Ensure core pipeline logic is independent of where documents originate.
- Capture rich **metadata** per chunk:
  - Document location (path/URI).
  - Document name (title or filename).
  - Document type (e.g., PDF, DOCX, Markdown).
  - Page number and chunk index.
  - Optional structural metadata (section headings, list/table indicators).
- Implement **hybrid chunking** using Docling:
  - Leverage `HybridChunker` to respect document structure.
  - Tune token limits for Qwen embeddings while also enforcing **min 400 chars** and **max 1000 chars** per chunk.
  - Load min/max character thresholds from environment variables.
- Integrate with the **AI assistant**:
  - Create an Archon‑style ingestion skill module that exposes a typed interface to the agent.
  - Avoid heavy prompts/metadata; follow the “skill” pattern described in `docs/skill_archon.md`.
- Integrate with the broader project architecture:
  - Follow the `src/` layout conventions and instructions in `AGENTS.md`.
  - Ensure all functions, methods, and variables have type annotations.
  - Use Google‑style docstrings.
  - Reuse the existing structured logging infrastructure in `src/shared/logging.py`.
- Support **hybrid search**:
  - Use PGVector for dense embeddings.
  - Use full‑text search (`tsvector`) for lexical retrieval.
  - Use trigram indexes (`pg_trgm`) for pattern and fuzzy matching.
  - Prepare for query‑time combination of vector, lexical, and pattern scores.
- Prepare for future **fine‑tuned embeddings**:
  - Store embedding model name/version per chunk.
  - Make it possible to re‑embed documents with new models and compare retrieval metrics.
- Testing and quality:
  - Add comprehensive unit tests under `tests/rag_pipeline/` and `tests/tools/ingestion_skill/`.
  - Add integration tests that run against a Supabase/Postgres instance (likely via Docker) where feasible.
  - Ensure `uv run ruff check src/ && uv run mypy src/` and `uv run pytest tests/` pass.

---

## Research Findings

### Best Practices

- **RAG ingest and storage**
  - Prefer a **chunk‑centric** storage model where each chunk is the primary unit of retrieval.
  - Store document‑level metadata in a separate `sources` table to decouple document identity and lifecycle from chunk content.
  - Use a **stable `content_hash`** (e.g., SHA‑256 of raw bytes) to detect document changes and avoid reprocessing unchanged files.
  - Group database operations by document inside transactions to avoid partially ingested states when errors occur.
  - Use `embedding_model_name` and `embedding_model_version` columns for each chunk to support re‑embedding and A/B testing of models.
  - For hybrid search, maintain **plain text content** in the chunk table so both dense and lexical queries operate on the same data.
- **Docling and hybrid chunking**
  - Use `DocumentConverter` to normalize various document formats into a DoclingDocument.
  - Use `HybridChunker` to:
    - Respect document structure and semantics.
    - Produce chunks that are token‑bounded for embedding models.
    - Preserve metadata and context (titles, headings, hierarchy).
  - After token‑based chunking, apply a second pass to enforce **character‑based min and max bounds** for better I/O predictability in the embedding model.
  - Store chunk‑level metadata including page number, section headings, and element types so context can be reconstructed and debugged.
- **Hybrid search (dense + lexical + pattern)**
  - As recommended in `docs/hybrid_search.md`, combine:
    - Dense embeddings for semantic similarity.
    - Lexical search (e.g., `tsvector`) for explainable word‑based matches.
    - Pattern search (e.g., `pg_trgm`) for partial matches and fuzzy codes.
  - Use **query analysis** to decide relative weights:
    - Identifier‑like queries (digits, hyphens, uppercase) → more weight on lexical + pattern.
    - Conceptual queries → more weight on dense embeddings.
  - Use a single `chunks` table with:
    - `embedding vector(1024)` (for Qwen3‑Embedding‑0.6B).
    - `text` column for chunk content.
    - `tsvector` and `pg_trgm` indexes over `text`.
  - Keep retrieval logic simple initially (e.g., vector search + text search + manual score combination) to avoid premature complexity.
- **Archon‑style skills**
  - Follow the pattern described in `docs/archon_SKILL.md`:
    - Keep skills modular and self‑contained.
    - Expose a minimal Pydantic schema describing inputs and outputs.
    - Make the skill invocable by the agent when relevant, rather than requiring manual user triggers.
    - Keep skill metadata/token overhead small; the skill should load heavy resources lazily when called.
  - For ingestion, an Archon‑style skill should:
    - Accept high‑level parameters (e.g., directories to ingest, force reingest).
    - Delegate all heavy work to a shared pipeline library.
    - Return structured results (documents processed, errors, etc.) that the agent can present.
- **Supabase/Postgres patterns**
  - Reuse `PRPs/examples/rag_agent_tables.sql` for conceptual guidance:
    - Use a `documents` table (or equivalent) with `content`, `metadata`, and `embedding vector(n)`.
    - Use a `match_documents` or `match_chunks` function to perform vector similarity search on server side.
  - For ingestion, add:
    - A `sources` table that tracks origin, `content_hash`, and status.
    - A `chunks` table that acts as the primary retrieval store.
  - Use row‑level security to protect ingestion tables if they are exposed through Supabase APIs, while the backend agent has privileged access.
- **Error handling and observability**
  - Log all ingestion operations in a structured format using the project’s `StructuredLogger`.
  - For each document, capture:
    - Start and end times.
    - Number of chunks generated.
    - Embedding success/failure counts.
    - Final status (`ingested`, `partial`, `failed`).
    - Embedding model identifier.
  - Ensure errors are raised and surfaced with context, not swallowed silently.
  - Expose enough metrics to support later performance tuning and debugging.
- **Fine‑tuned embeddings**
  - As described in `PRPs/ai_docs/fine-tuned-embeddings.md`, a fine‑tuned embeddings strategy requires:
    - Clear mapping between embeddings and model versions.
    - Reproducible training data and evaluation metrics (recall@k).
  - This plan focuses on baseline Qwen3 embeddings but will:
    - Store model name/version per chunk.
    - Avoid hard‑coding embedding dimension where possible.
    - Make it easy to drop in a fine‑tuned model later.

### Reference Implementations

- `PRPs/examples/docling_hybrid_chunking.py`
  - Demonstrates how to:
    - Use `DocumentConverter` to convert PDFs.
    - Initialize a tokenizer for sentence‑transformer models.
    - Configure and use `HybridChunker`.
    - Analyze and save chunks along with contextualized content.
  - Key takeaways:
    - The `HybridChunker` API to adopt in our pipeline.
    - Patterns for inspecting chunk sizes/tokens and metadata.
    - Example of error handling around conversion and chunking.
- `PRPs/examples/rag_agent.py`
  - Shows a CLI‑based RAG agent using:
    - PostgreSQL with a `match_chunks` function for vector search.
    - An embedding component via `ingestion.embedder`.
    - PydanticAI for structured tools.
  - Key takeaways:
    - How to structure database search functions.
    - How a RAG agent can integrate an embedding and retrieval tool.
    - Basic patterns for streaming responses.
- `PRPs/examples/backend_agent_api/*`
  - Provides examples of:
    - API server layout.
    - Database utilities.
    - Separation between agent logic and persistence.
  - Key takeaways:
    - How to structure services and clients.
    - Logging and configuration patterns.
- `PRPs/examples/rag_agent_tables.sql`
  - Contains a complete schema for:
    - `documents` and related tables.
    - PL/pgSQL search functions (e.g., `match_documents`).
    - Indexes and policies.
  - Key takeaways:
    - PGVector table definition and search function design.
    - Security (RLS) patterns for document tables.
- `docs/docling.md`
  - Clarifies:
    - Docling ingestion workflow (documents → Markdown → chunks → embeddings).
    - Relationship to PGVector and hybrid search.
  - Key takeaways:
    - Docling as a full ingestion pipeline inspiration.
    - Default token limits and how they relate to embedding models.
- `docs/hybrid_search.md`
  - Describes:
    - Hybrid search motivation.
    - Roles of dense, lexical, and pattern search.
    - Implementation guidelines for PGVector, `tsvector`, and `pg_trgm`.
  - Key takeaways:
    - The hybrid search strategy we will design around.
    - How to ensure product codes and identifiers are retrieved reliably.
- `docs/skill_archon.md`
  - Explains:
    - What “skills” are in the Archon pattern.
    - How skills are modular, model‑invoked, and token‑efficient.
  - Key takeaways:
    - How to design the ingestion skill’s API and metadata.
    - How to keep the skill minimal and composable.

### Technology Decisions

- **Language and frameworks**
  - Python 3.x with strict type hints and mypy.
  - Pydantic for data models and schemas (agent tools and skill interfaces).
  - The project’s existing logging and configuration utilities (`src/shared`).
- **LLM and embeddings**
  - Qwen3‑VL‑8B‑Instruct as the primary LLM for the agent.
  - Qwen3‑Embedding‑0.6B for dense chunk embeddings.
  - Embedding calls will be encapsulated behind a typed client (`qwen_client.py`) to support both local models and remote APIs.
- **Document processing**
  - Docling’s `DocumentConverter` as the universal document ingestion layer.
  - Docling’s `HybridChunker` for chunking, plus a custom post‑processing pass to enforce character bounds.
- **Database and search**
  - Supabase/PostgreSQL with PGVector for embeddings.
  - `chunks` table with:
    - `text` content.
    - `embedding vector(1024)` column for Qwen embeddings.
    - `metadata` JSONB for structural info.
  - `sources` table for document‑level tracking with `content_hash` and ingestion status.
  - `tsvector` index for full‑text search on chunk text.
  - `pg_trgm` index for fuzzy/pattern matching.
- **Architecture**
  - A dedicated `src/rag_pipeline/` package containing:
    - `config.py` (ingestion config).
    - `schemas.py` (Pydantic models and dataclasses).
    - `sources/local_files.py` (initial source adapter).
    - `chunking/docling_chunker.py` (Docling integration).
    - `embeddings/qwen_client.py` (embedding client).
    - `persistence/supabase_store.py` (DB access).
    - `pipeline.py` (orchestrator).
    - `cli.py` (batch/cron entrypoint).
  - A tool slice under `src/tools/ingestion_skill/` providing the Archon‑style ingestion skill:
    - `schemas.py` (skill request/response).
    - `service.py` (skill execution).
    - `tool.py` (agent integration metadata).
- **Execution and deployment**
  - The ingestion CLI will be run via `uv` (or plain Python) and orchestrated by:
    - Cron jobs.
    - Docker Compose schedules.
    - Manual runs for ad‑hoc ingestion.
  - The ingestion skill will be callable from the agent at runtime for on‑demand reindexing.

---

## Implementation Tasks

### Phase 1: Foundation

1. **Define RAG ingestion configuration**
   - Description: Introduce a `RagIngestionConfig` dataclass and `get_rag_ingestion_config()` function under `src/rag_pipeline/config.py` to load ingestion‑specific settings from environment variables (source directories, chunk size bounds, embedding retry counts, etc.).
   - Files to modify/create:
     - Create `src/rag_pipeline/config.py`.
     - Optionally reference or extend `src/shared/config.py` if reuse is appropriate.
   - Dependencies:
     - Existing `src/shared/config.py` patterns.
     - Environment variable definitions (to be documented).
   - Estimated effort: 1–2 hours.

2. **Define core ingestion and storage schemas**
   - Description: Create typed Pydantic models and dataclasses that represent documents, chunks, embeddings, and ingestion results. Include alias types for `SourceType` and `SourceIngestionStatus`.
   - Files to modify/create:
     - Create `src/rag_pipeline/schemas.py`.
   - Dependencies:
     - `src/shared/logging.LoggerProtocol` for type references where needed.
   - Estimated effort: 2–3 hours (including docstrings and mypy tuning).

3. **Design database schema for sources and chunks**
   - Description: Design SQL for `sources` and `chunks` tables congruent with the chunk‑centric model and hybrid search requirements, using Supabase/Postgres conventions and PGVector. Ensure compatibility with Qwen3 embedding dimensions (1024).
   - Files to modify/create:
     - Create or extend a SQL file, e.g., `PRPs/examples/rag_ingestion_tables.sql` or a new schema file such as `PRPs/examples/rag_pipeline_docling_supabase.sql`.
   - Dependencies:
     - `PRPs/examples/rag_agent_tables.sql` for reference patterns.
     - `docs/hybrid_search.md` for index requirements.
   - Estimated effort: 2–3 hours (design) + time to validate against Supabase instance.

4. **Document environment variables and operational requirements**
   - Description: Add or extend documentation (e.g., `docs/architecture.md` or a new `docs/rag_pipeline.md`) to specify environment variables used by the ingestion pipeline and skill, including defaults and recommended values.
   - Files to modify/create:
     - Modify `docs/architecture.md` or create `docs/rag_pipeline_ingestion.md`.
   - Dependencies:
     - `AGENTS.md` for style guidance.
     - `docs/docling.md` and `docs/hybrid_search.md` for cross‑references.
   - Estimated effort: 1–2 hours.

5. **Establish tests layout for RAG pipeline**
   - Description: Create test package structure for the ingestion pipeline and ingestion skill, with placeholder test modules and fixtures.
   - Files to modify/create:
     - Create `tests/rag_pipeline/test_config.py`.
     - Create `tests/rag_pipeline/test_schemas.py`.
     - Create `tests/tools/ingestion_skill/test_service.py`.
   - Dependencies:
     - `PRPs/ai_docs/testing_guide.md` to align testing style and patterns.
   - Estimated effort: 1–2 hours.

6. **Integrate logging conventions**
   - Description: Decide how ingestion modules will use the structured logging protocol so logs include pipeline‑specific context (pipeline_id, document counts, durations).
   - Files to modify/create:
     - Add logging usage in `src/rag_pipeline/*` modules as they are created.
   - Dependencies:
     - `src/shared/logging.py`.
     - `PRPs/ai_docs/logging_guide.md`.
   - Estimated effort: 1–2 hours (spread across later tasks).

### Phase 2: Core Implementation

7. **Implement local file discovery adapter**
   - Description: Implement `discover_documents()` in `src/rag_pipeline/sources/local_files.py` that scans configured directories, computes `content_hash` for each file, and returns a list of `DocumentInput` models. The adapter should be easily replaceable by future source adapters.
   - Files to modify/create:
     - Create `src/rag_pipeline/sources/__init__.py`.
     - Create `src/rag_pipeline/sources/local_files.py`.
   - Dependencies:
     - `RagIngestionConfig` for source directory settings.
     - `DocumentInput` model from `schemas.py`.
   - Estimated effort: 2–3 hours.

8. **Implement Docling‑based chunking module**
   - Description: Implement `chunk_document()` in `src/rag_pipeline/chunking/docling_chunker.py` using Docling `DocumentConverter` and `HybridChunker`. Incorporate basic error handling and metadata extraction (page numbers, headings, element types).
   - Files to modify/create:
     - Create `src/rag_pipeline/chunking/__init__.py`.
     - Create `src/rag_pipeline/chunking/docling_chunker.py`.
   - Dependencies:
     - Docling library.
     - `DocumentInput` and `ChunkData` schemas.
     - Reference: `PRPs/examples/docling_hybrid_chunking.py`.
   - Estimated effort: 3–4 hours (including experimentation).

9. **Implement character bounds enforcement for chunks**
   - Description: Implement `enforce_character_bounds()` that applies `chunk_min_chars` and `chunk_max_chars` from config, merging small chunks and splitting large ones while preserving structural metadata from Docling.
   - Files to modify/create:
     - Extend `src/rag_pipeline/chunking/docling_chunker.py` with character‑bound logic or create a separate helper module.
   - Dependencies:
     - `ChunkData` schema.
     - `RagIngestionConfig` for character limits.
   - Estimated effort: 2–3 hours.

10. **Implement Qwen3 embedding client with retry**
    - Description: Implement `embed_texts()` and `embed_texts_with_retry()` in `src/rag_pipeline/embeddings/qwen_client.py`, wrapping Qwen3‑Embedding‑0.6B. Respect batch sizes, perform a single retry on transient errors, and propagate meaningful exceptions for permanent failures.
    - Files to modify/create:
      - Create `src/rag_pipeline/embeddings/__init__.py`.
      - Create `src/rag_pipeline/embeddings/qwen_client.py`.
    - Dependencies:
      - Qwen embedding model (local or API).
      - `EmbeddingResult` schema.
      - `RagIngestionConfig` (model name/version, retry count).
    - Estimated effort: 3–4 hours (including integration tests with a running model).

11. **Implement Supabase/Postgres persistence layer**
    - Description: Implement `supabase_store.py` to provide typed operations for `sources` and `chunks` tables, including `get_source_by_location()`, `upsert_source()`, `upsert_chunks()`, and `mark_source_status()`. Ensure it works with the schema designed in Phase 1.
    - Files to modify/create:
      - Create `src/rag_pipeline/persistence/__init__.py`.
      - Create `src/rag_pipeline/persistence/supabase_store.py`.
    - Dependencies:
      - `SourceRecord` and `ChunkRecord` dataclasses.
      - Database schema file created earlier.
      - A Supabase/Postgres client (e.g., `asyncpg`, `psycopg2`, or Supabase Python client).
    - Estimated effort: 4–6 hours (including connection management and basic error handling).

12. **Implement document‑level ingestion (single document)**
    - Description: Implement ` ingest_single_document()` in `src/rag_pipeline/pipeline.py` that orchestrates:
      - Document discovery (input param is a `DocumentInput`).
      - Docling conversion and hybrid chunking.
      - Character bounds enforcement.
      - Embedding generation with retry.
      - Database upsert for source and chunks in a transaction.
      - Status updates for `sources` based on success or failure.
    - Files to modify/create:
      - Create `src/rag_pipeline/pipeline.py`.
    - Dependencies:
      - Schemas, chunking, embeddings, and persistence modules from earlier tasks.
      - `LoggerProtocol` for structured logging.
    - Estimated effort: 4–6 hours.

13. **Implement ingestion job orchestrator**
    - Description: Implement `run_ingestion_job()` in `src/rag_pipeline/pipeline.py` that:
      - Loads config.
      - Invokes `discover_documents()` for the configured directories.
      - Filters documents based on `content_hash` and `force_reingest`.
      - Calls `ingest_single_document()` for each document.
      - Aggregates per‑document results into an `IngestionResult`.
      - Logs high‑level metrics (document counts, chunk counts, durations).
    - Files to modify/create:
      - Extend `src/rag_pipeline/pipeline.py`.
    - Dependencies:
      - `RagIngestionConfig` and `IngestionRequest`.
      - `discover_documents()`.
      - `ingest_single_document()`.
    - Estimated effort: 3–4 hours.

14. **Implement batch/cron CLI entrypoint**
    - Description: Create a CLI entrypoint that parses command‑line arguments into an `IngestionRequest` and calls `run_ingestion_job()`. The CLI should print a concise summary and exit with non‑zero status on failures.
    - Files to modify/create:
      - Create `src/rag_pipeline/cli.py`.
      - Optionally add console entry points in project packaging configuration.
    - Dependencies:
      - `run_ingestion_job()` and `IngestionRequest`.
      - Logging setup.
    - Estimated effort: 2–3 hours.

15. **Implement Archon‑style ingestion skill schemas**
    - Description: Define `IngestionSkillRequest` and `IngestionSkillResponse` in `src/tools/ingestion_skill/schemas.py` as thin wrappers around `IngestionRequest` and `IngestionResult`, ensuring they are easily discoverable by the agent tooling.
    - Files to modify/create:
      - Create `src/tools/ingestion_skill/__init__.py`.
      - Create `src/tools/ingestion_skill/schemas.py`.
    - Dependencies:
      - `src/rag_pipeline/schemas.py`.
      - Agent tooling conventions in this codebase.
    - Estimated effort: 1–2 hours.

16. **Implement Archon‑style ingestion skill service**
    - Description: Implement `run_ingestion()` in `src/tools/ingestion_skill/service.py`, which:
      - Accepts `IngestionSkillRequest`.
      - Loads `RagIngestionConfig`.
      - Calls `run_ingestion_job()`.
      - Returns an `IngestionSkillResponse`.
      - Logs skill invocations with structured context.
    - Files to modify/create:
      - Create `src/tools/ingestion_skill/service.py`.
    - Dependencies:
      - `src/rag_pipeline/pipeline.py`.
      - `src/rag_pipeline/config.py`.
      - `LoggerProtocol`.
    - Estimated effort: 2–3 hours.

17. **Wire ingestion skill into agent tool registry**
    - Description: Create `tool.py` under `src/tools/ingestion_skill/` that defines metadata for the ingestion skill (name, description, input/output models) and integrates it into the agent’s tool registry so the LLM can invoke it contextually.
    - Files to modify/create:
      - Create `src/tools/ingestion_skill/tool.py`.
      - Modify agent/tool registration code (location depends on how tools are implemented; likely under `src/agent` or a tools registry module).
    - Dependencies:
      - Existing agent tooling integration patterns (consult `PRPs/ai_docs/tool_guide.md`).
    - Estimated effort: 2–3 hours.

### Phase 3: Integration & Testing

18. **Add unit tests for config and schemas**
    - Description: Add tests to ensure config values are correctly loaded from environment variables and that schemas enforce expected validation rules.
    - Files to modify/create:
      - `tests/rag_pipeline/test_config.py`.
      - `tests/rag_pipeline/test_schemas.py`.
    - Dependencies:
      - `RagIngestionConfig`, `DocumentInput`, `ChunkData`, `IngestionRequest`, `IngestionResult`.
    - Estimated effort: 2–3 hours.

19. **Add unit tests for local file discovery**
    - Description: Add tests for `discover_documents()` that verify:
      - Correct discovery of files in nested directories.
      - Correct `content_hash` computation.
      - Proper handling of ignored files or unsupported extensions.
    - Files to modify/create:
      - `tests/rag_pipeline/test_sources_local_files.py`.
    - Dependencies:
      - Temporary directory fixtures.
    - Estimated effort: 3–4 hours.

20. **Add unit tests for Docling chunking logic**
    - Description: Using small test documents, verify that `chunk_document()` and `enforce_character_bounds()` produce chunks with:
      - Correct page numbers and chunk indices.
      - Reasonable token/character distributions.
      - Preserved structural metadata.
    - Files to modify/create:
      - `tests/rag_pipeline/test_chunking_docling.py`.
    - Dependencies:
      - Docling test fixtures or small example documents.
    - Estimated effort: 4–6 hours (including test data setup).

21. **Add unit tests for Qwen embedding client**
    - Description: Use mocks/fakes to test `embed_texts()` and `embed_texts_with_retry()`, ensuring:
      - Correct handling of successful and failed calls.
      - Retry logic is triggered appropriately.
      - Exceptions contain helpful error messages.
    - Files to modify/create:
      - `tests/rag_pipeline/test_embeddings_qwen_client.py`.
    - Dependencies:
      - `unittest.mock` or similar.
    - Estimated effort: 3–4 hours.

22. **Add unit tests for Supabase persistence layer**
    - Description: Write tests for `supabase_store` that mock the DB client and verify:
      - `get_source_by_location()` queries the database correctly.
      - `upsert_source()` and `upsert_chunks()` handle insert/update scenarios.
      - `mark_source_status()` sets status and error message fields as expected.
    - Files to modify/create:
      - `tests/rag_pipeline/test_persistence_supabase_store.py`.
    - Dependencies:
      - Mocked DB connections or transaction objects.
    - Estimated effort: 4–6 hours.

23. **Add integration tests for end‑to‑end ingestion**
    - Description: With a test Supabase/Postgres (e.g., via Docker), test the full ingestion pipeline for one or more sample documents, from local filesystem discovery to populated `sources` and `chunks` tables.
    - Files to modify/create:
      - `tests/rag_pipeline/test_pipeline_integration.py`.
    - Dependencies:
      - Local Supabase/Postgres container with PGVector and required schema.
      - Test documents and environment configuration.
    - Estimated effort: 6–8 hours.

24. **Add unit tests for ingestion skill**
    - Description: Write tests for the ingestion skill service that:
      - Verify the request→config→pipeline→response flow.
      - Assert logging calls for success and failure scenarios.
      - Avoid hitting the real database by mocking `run_ingestion_job()`.
    - Files to modify/create:
      - `tests/tools/ingestion_skill/test_service.py`.
    - Dependencies:
      - `IngestionSkillRequest` and `IngestionSkillResponse`.
    - Estimated effort: 3–4 hours.

25. **Verify agent integration of ingestion skill**
    - Description: Add tests (or at least manual validation) that:
      - Confirm the agent can “see” the ingestion skill in its tools list.
      - Confirm the agent can call the ingestion skill when asked to reindex documents.
    - Files to modify/create:
      - `tests/agent/test_ingestion_skill_integration.py` (optional but recommended).
    - Dependencies:
      - Existing agent setup in `src/agent`.
    - Estimated effort: 3–5 hours.

26. **Performance and scalability testing**
    - Description: With sample corpora, test ingestion throughput and memory usage:
      - Measure ingestion time per document and per chunk.
      - Identify bottlenecks in Docling conversion, embedding calls, and DB writes.
      - Tune batch sizes and DB indexes where necessary.
    - Files to modify/create:
      - Optional benchmarks (e.g., `tests/performance/test_ingestion_performance.py`).
    - Dependencies:
      - Test corpora and a local Supabase/Postgres instance.
    - Estimated effort: 6–10 hours.

27. **Documentation and operational runbooks**
    - Description: Document how to:
      - Run the ingestion CLI locally and in Docker.
      - Configure environment variables and Supabase.
      - Run the ingestion skill from the agent.
    - Files to modify/create:
      - `docs/rag_pipeline_ingestion.md` (or similar).
    - Dependencies:
      - All previous implementation details.
    - Estimated effort: 3–5 hours.

28. **Review, refactor, and align with KISS/YAGNI**
    - Description: Perform a final pass to:
      - Remove unnecessary abstractions.
      - Consolidate repetitive patterns.
      - Confirm the solution is the simplest that meets requirements while remaining extensible.
    - Files to modify/create:
      - Various modules in `src/rag_pipeline/` and `src/tools/ingestion_skill/`.
    - Dependencies:
      - All core features implemented.
    - Estimated effort: 3–4 hours.

---

## Codebase Integration Points

### Files to Modify

- `src/shared/config.py`
  - Possibly reference ingestion‑specific settings or ensure no conflict between global and RAG‑specific config.
- `src/agent/agent.py`
  - Optionally integrate ingestion skill references if the agent needs to be aware of ingestion capabilities for prompt/tuning.
- `docs/architecture.md`
  - Extend architecture diagram and description to include the ingestion pipeline and its interaction with Supabase and the agent.
- `PRPs/examples/rag_agent_tables.sql`
  - Use as reference; optionally update or fork into a new schema file for this pipeline.

### New Files to Create

- `src/rag_pipeline/config.py`
  - Ingestion configuration dataclass and loader.
- `src/rag_pipeline/schemas.py`
  - Shared ingestion models and dataclasses.
- `src/rag_pipeline/sources/__init__.py`
  - Package init for source adapters.
- `src/rag_pipeline/sources/local_files.py`
  - Local filesystem document discovery adapter.
- `src/rag_pipeline/chunking/__init__.py`
  - Package init for chunking utilities.
- `src/rag_pipeline/chunking/docling_chunker.py`
  - Docling HybridChunker integration and character bounds enforcement.
- `src/rag_pipeline/embeddings/__init__.py`
  - Package init for embedding clients.
- `src/rag_pipeline/embeddings/qwen_client.py`
  - Qwen3 embedding client with retry.
- `src/rag_pipeline/persistence/__init__.py`
  - Package init for persistence.
- `src/rag_pipeline/persistence/supabase_store.py`
  - Supabase/Postgres persistence layer for sources and chunks.
- `src/rag_pipeline/pipeline.py`
  - Document‑level ingestion and ingestion job orchestration.
- `src/rag_pipeline/cli.py`
  - CLI entrypoint for batch/cron ingestion.
- `src/tools/ingestion_skill/__init__.py`
  - Package init for ingestion skill.
- `src/tools/ingestion_skill/schemas.py`
  - Skill request/response models.
- `src/tools/ingestion_skill/service.py`
  - Skill service implementation bridging agent to pipeline.
- `src/tools/ingestion_skill/tool.py`
  - Tool metadata and registration.
- Tests under `tests/rag_pipeline/` and `tests/tools/ingestion_skill/` as described in the tasks section.

### Existing Patterns to Follow

- `src/shared/logging.StructuredLogger`
  - For structured JSON logging of ingestion events.
- `src/shared/config.Settings` and `get_settings()`
  - For patterns on configuration loading and dataclass usage.
- `PRPs/examples/docling_hybrid_chunking.py`
  - For Docling HybridChunker usage and chunk analysis.
- `PRPs/examples/rag_agent.py`
  - For vector search patterns and agent tool integration.
- `PRPs/examples/backend_agent_api/*`
  - For separation of concerns between services, clients, and API layers.

---

## Technical Design

### Architecture Diagram (Textual)

```
          +-------------------+         +-----------------------------+
          |  Local Documents  |         |      Other Future Sources   |
          |  (PDF, DOCX, MD)  |         |   (S3, GDrive, APIs, etc.) |
          +---------+---------+         +--------------+--------------+
                    |                                   |
                    |  (1) Discover via adapters        |
                    v                                   v
          +-------------------------+         +-------------------------+
          |  DocumentInput objects  |  ...   |  DocumentInput objects  |
          +-------------------------+         +-------------------------+
                    |                                   |
                    +---------------+-------------------+
                                    |
                        (2) Docling Conversion
                                    |
                                    v
                   +-----------------------------+
                   | Docling DocumentConverter   |
                   +-----------------------------+
                                    |
                        (3) Hybrid Chunking
                                    |
                                    v
                   +-----------------------------+
                   |   HybridChunker (Docling)   |
                   +-----------------------------+
                                    |
                       (4) Character Bounds
                                    |
                                    v
                    +----------------------------+
                    |   ChunkData objects        |
                    +----------------------------+
                                    |
                        (5) Qwen Embeddings
                                    |
                                    v
            +---------------------------------------------+
            |  Qwen3-Embedding-0.6B (qwen_client)        |
            +---------------------------------------------+
                                    |
                        (6) Persistence Layer
                                    |
                                    v
        +----------------------------------------------------+
        | Supabase/Postgres: sources, chunks, indexes        |
        |  - PGVector (embedding column)                     |
        |  - text (chunk content)                            |
        |  - tsvector + pg_trgm for hybrid search            |
        +----------------------------------------------------+
                                    ^
                                    |
                 (7) Retrieval (future RAG agent integration)
                                    |
                                    v
        +-----------------------------------------------------+
        |  RAG Agent (Qwen3-VL-8B-Instruct)                   |
        |  - Uses retrieval APIs to fetch chunks by hybrid    |
        |    search                                           |
        |  - Can invoke ingestion_skill to reindex content    |
        +-----------------------------------------------------+
```

### Data Flow

- **Ingestion path**:
  1. The ingestion CLI or ingestion skill calls `run_ingestion_job()`.
  2. The pipeline loads `RagIngestionConfig` from environment.
  3. `discover_documents()` scans configured directories and yields `DocumentInput` objects with `content_hash`.
  4. The pipeline compares each document against `sources`:
     - If no row exists or `content_hash` differs, mark as needing ingestion.
     - If a row exists with matching `content_hash` and `force_reingest` is `False`, skip.
  5. For each document to ingest:
     - `ingest_single_document()` converts it via Docling `DocumentConverter`.
     - `chunk_document()` chunks it using `HybridChunker`.
     - `enforce_character_bounds()` adjusts chunk sizes as needed.
     - `embed_texts_with_retry()` generates embeddings for each chunk.
     - `upsert_source()` inserts/updates the document row; `upsert_chunks()` inserts/updates chunk rows and embeddings.
     - `mark_source_status()` sets status to `ingested` or `partially_ingested`/`failed`.
  6. `run_ingestion_job()` aggregates results and returns an `IngestionResult`.

- **Retrieval path (future step)**:
  1. The RAG agent receives a user query.
  2. A retrieval component:
     - Analyzes the query to determine if it is identifier‑like or conceptual.
     - Generates an embedding for the query using the same embedding model.
  3. The retrieval component runs:
     - A vector similarity query over `chunks.embedding` (e.g., via a `match_chunks` function).
     - A lexically weighted full‑text search over `chunks.text`.
     - A trigram/LIKE query for fuzzy code matches when needed.
  4. It combines scores from the three searches to obtain a hybrid ranking.
  5. The top K chunks are passed to Qwen3‑VL‑8B‑Instruct along with the question to generate an answer.

### API / Interface Surfaces

- **CLI interface**:
  - Command (example): `uv run python -m src.rag_pipeline.cli --source-dir /data/docs --force-reingest=false`.
  - Options:
    - `--source-dir` (can be provided multiple times).
    - `--force-reingest` (flag).
    - `--pipeline-id` (optional override).
  - Output:
    - Summary: number of documents seen, ingested, skipped, failed; number of chunks created/updated.
    - Exit code:
      - `0` on success (no failures).
      - Non‑zero if any document ingestion failed.

- **Ingestion skill interface**:
  - Request (`IngestionSkillRequest`):
    - A wrapped `IngestionRequest` with optional skill‑specific metadata.
  - Response (`IngestionSkillResponse`):
    - A wrapped `IngestionResult`.
  - Invocation:
    - Registered as a tool that the agent can call when it detects a user intention like “reindex the finance folder”.

---

## Dependencies and Libraries

- **Core Python libraries**
  - `dataclasses` for configuration and records.
  - `typing` (including `Literal`, `Protocol`, etc.) for strict typing.
  - `asyncio` (optional) if asynchronous DB/model calls are desired.

- **Project‑local utilities**
  - `src/shared/config` for patterns on configuration.
  - `src/shared/logging` for structured logging.

- **Third‑party libraries**
  - **Docling**:
    - For document conversion and HybridChunker.
    - Likely `docling` package or equivalent.
  - **Supabase/Postgres client**:
    - `asyncpg` or `psycopg2` or official Supabase Python client.
  - **PGVector**:
    - Postgres extension; Python side can treat the vector as list of floats or use a helper library.
  - **Qwen models**:
    - Qwen3‑Embedding‑0.6B: via Hugging Face `transformers` or official Qwen libraries.
    - Qwen3‑VL‑8B‑Instruct: used by the agent for generation.
  - **Pydantic**:
    - Already in use; continue using for schemas.
  - **Testing framework**:
    - `pytest` as already configured.

---

## Testing Strategy

- **Unit testing**
  - Validate config parsing and defaults.
  - Validate schema behaviour and default values.
  - Test file discovery against temporary directories with contrived structures.
  - Test chunking logic with small, synthetic documents to isolate Docling behaviour.
  - Test embedding client with mocks to verify retry behaviour.
  - Test persistence functions with mocked DB connections.
  - Test ingestion skill service logic without hitting real Supabase or Docling.

- **Integration testing**
  - Stand up a Supabase/Postgres instance via Docker (including PGVector, `tsvector`, and `pg_trgm`).
  - Run end‑to‑end ingestion on a small corpus (a handful of PDFs, DOCX, and Markdown documents).
  - After ingestion, query `sources` and `chunks` tables:
    - Check row counts.
    - Ensure metadata fields (page numbers, locations) are populated.
    - Validate that embeddings are non‑zero and correct dimension.
  - Optionally test retrieval queries (vector and lexical) with synthetic queries to validate hybrid search behaviour.

- **Performance testing**
  - Evaluate ingestion throughput for small and medium corpora.
  - Measure memory usage and CPU load during Docling conversion and embedding generation.
  - Use these metrics to tune:
    - Chunk sizes (character and token).
    - Embedding batch size.
    - DB transaction sizes.

- **Regression and future fine‑tuning**
  - As fine‑tuned embeddings are introduced:
    - Add tests that compare recall@k for baseline vs fine‑tuned models using a small labelled query set.
    - Use consistent `embedding_model_version` semantics to keep results traceable.

---

## Success Criteria

- [ ] The ingestion CLI can scan configured directories, detect new/changed documents, and ingest them without manual DB manipulation.
- [ ] Documents are processed via Docling and chunked using HybridChunker, with character bounds enforced as per environment configuration.
- [ ] Chunks are stored in a Supabase/Postgres `chunks` table with:
      - Text content.
      - Rich metadata (location, name, type, page, chunk index).
      - Embeddings of the correct dimension for Qwen3‑Embedding‑0.6B.
- [ ] The `sources` table accurately tracks document status (`pending`, `ingested`, `partially_ingested`, `failed`) and `content_hash`.
- [ ] Embedding failures trigger a single retry, and subsequent failures are captured and surfaced with clear error messages.
- [ ] The ingestion pipeline can be invoked both via CLI and via the Archon‑style ingestion skill.
- [ ] The ingestion skill is fully integrated into the agent’s toolset and can be invoked by the agent in response to user requests.
- [ ] Hybrid search indexes (vector, `tsvector`, `pg_trgm`) are in place and usable for retrieval.
- [ ] Unit and integration tests pass and provide meaningful coverage of ingestion paths and failure modes.
- [ ] The design remains aligned with KISS and YAGNI: minimal necessary abstractions, no unnecessary complexity.

---

## Notes and Considerations

- Carefully manage **idempotency**:
  - Ensure that re‑running the ingestion CLI without `force_reingest` does not create duplicate chunks.
  - Ensure that changing a document’s content causes appropriate re‑ingestion and cleanup of obsolete chunks.
- Plan for **re‑embedding and model upgrades**:
  - This plan stores embedding model metadata to support future fine‑tuned models as described in `PRPs/ai_docs/fine-tuned-embeddings.md`.
  - Later phases can introduce a background job for re‑embedding existing chunks with new models and updating retrieval evaluation metrics.
- Consider **access control**:
  - If multiple teams or environments share the database, consider adding a `tenant_id` or similar field to both `sources` and `chunks`.
  - Leverage row‑level security policies to restrict which rows can be accessed via Supabase APIs.
- Keep **observability** high:
  - Use correlation IDs or pipeline IDs in logs to trace ingestion runs end‑to‑end.
  - Log durations for Docling, chunking, embedding, and DB operations.
  - Capture representative errors in a central place where developers can inspect ingestion problems quickly.
- Be mindful of **resource consumption**:
  - Docling and Qwen models can be memory‑ and CPU‑intensive. Start with conservative batch sizes and adjust after observing real workloads.
  - For local development, allow configuration of smaller chunk sizes and partial ingestion for faster feedback loops.
- Align with **existing project structure**:
  - Keep the ingestion pipeline inside `src/rag_pipeline/`.
  - Keep tools (skills) inside `src/tools/`.
  - Use Pydantic schemas and structured logging consistently across new modules.

---

*This plan is ready for execution with `/execute-plan PRPs/requests/rag_pipeline_docling_supabase_archon.md`.*

