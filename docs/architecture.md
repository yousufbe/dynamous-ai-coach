# High‑Level Architecture & Setup

This document outlines the recommended architecture and setup steps for your
local RAG assistant.  It combines document ingestion, hybrid retrieval,
language model inference and modular skills into a cohesive system.

## Architectural overview

```
┌─────────────┐     ┌────────────────┐     ┌──────────────┐
│   User      │───▶│ RAG Assistant  │───▶│ PGVector DB   │
│ Interface   │    │ (Pydantic AI)  │    │ (PostgreSQL)  │
└─────────────┘     └────────────────┘     └──────────────┘
       │                         │
       │                         ▼
       │                 ┌──────────────┐
       └───────────────▶│ Embedding     │
                        │ Model (Qwen3) │
                        └──────────────┘
```

1. **User interface.**  Employees interact with the assistant via a CLI or
   web interface.  The interface sends natural language questions and
   receives streamed responses with citations.  A FastAPI backend is exposed
   under `src/main.py`, and a React/Vite‑based chat UI example lives in
   `PRPs/examples/Front_end_UI_example`.
2. **RAG assistant.**  The core agent coordinates retrieval and generation.
   It accepts a query, performs hybrid search over the PGVector database,
   assembles the most relevant chunks and feeds them into the Qwen3‑VL
   language model.  It returns the generated answer with references.
3. **PGVector database.**  Stores all document chunks with metadata and
   embeddings.  Additional indexes support lexical and pattern searches for
   hybrid retrieval【391127687261448†L549-L570】.【445922077582970†L49-L62】
4. **Embedding model.**  Generates dense vectors for document chunks and
   queries.  Use Qwen3‑Embedding‑0.6B to ensure multilingual and long
   context support【984059247734186†L65-L104】.
5. **Skills / Modules.**  Optional modules provide extended capabilities
   (e.g., logging, admin functions).  Follow the modular patterns described
   in `docs/skill_archon.md`【898591313443642†L80-L104】.

## End-to-end flow (clone → configure → query)

The diagram above maps directly to the Quickstart in `README.md`:

1. **Clone + environment.**  Copy the repository, create a Python (or `uv`)
   environment and install `requirements.txt`.
2. **Provision storage.**  Start PostgreSQL or Supabase with `vector` and
   `pg_trgm` enabled and apply
   `PRPs/examples/rag_pipeline_docling_supabase.sql`. Use the resulting
   connection string for both `DATABASE_URL` and `RAG_DATABASE_URL`.
3. **Configure models.**  Export `EMBEDDING_MODEL`, `LLM_MODEL`, and
   `QWEN_API_KEY`. `src/shared/config.py` documents the defaults, and
   `docs/rag_pipeline_ingestion.md` lists every ingestion toggle.
4. **Ingest documents.**  Point `RAG_SOURCE_DIRS` at your corpora and run the
   CLI (`uv run python -m src.rag_pipeline.cli`). Monitor chunk counts,
   retries and metrics using structured logs plus
   `docs/post_ingestion_validation.md`. For a smoke test without real data,
   set `RAG_SOURCE_DIRS=documents/fixtures` to ingest the bundled sample corpus.
5. **Start FastAPI.**  Launch `uv run uvicorn src.main:app --port 8030`,
   verify `/health`, and hit `/chat` to confirm the wiring. With
   `RAG_DATABASE_URL` and an LLM endpoint configured, `/chat` performs retrieval
   over ingested chunks and returns grounded answers with citations. If either
   dependency is missing, it falls back to a deterministic summary so you can
   still validate wiring and logs.
6. **Optional UI.**  Run the React/Vite example
   (`PRPs/examples/Front_end_UI_example`) with `npm run dev` if you want a
   browser chat surface while the local backend integration is underway.

## Required vs optional dependencies

To reach the “first question answered” milestone you only need:

- A Python 3.11+ environment with the packages from `requirements.txt`.
- PostgreSQL with PGVector (`vector`) and `pg_trgm`.
- A Qwen embedding endpoint plus `QWEN_API_KEY`.
- Network access to whichever LLM endpoint you plan to call.

Defer the following until you need them:

- Docling’s optional Whisper/OCR dependencies.
- The fine-tuned embeddings workflow (`PRPs/examples/fine_tuned_embeddings.py`).
- Frontend tooling (Node.js 18+, pnpm/npm) unless you plan to modify the UI.
- Performance benchmarks in `tests/performance/` and the Archon ingestion skill.


## Setup checklist

1. **Provision hardware.**  Ensure your server or workstation has enough
   resources to run an 8 B‑parameter model.  If not, use a smaller variant or
   offload inference to GPUs via vLLM or similar frameworks.  Reserve
   separate resources for the embedding model.
2. **Install dependencies.**  Create a Python environment (e.g., via
   `venv` or `conda`).  Install the following:
   - `transformers` (>=4.57) for Qwen3‑VL support【230556131312387†L121-L144】.
   - `sentence-transformers` and `qwen3` packages for embeddings【984059247734186†L147-L160】.
   - `docling` for document parsing, chunking and ingestion【391127687261448†L490-L605】.
   - `pgvector`, `psycopg2` for PostgreSQL integration.
   - `pg_trgm` extension for pattern search (enable in PostgreSQL).
3. **Configure environment variables.**  Use a `.env` file to store
   sensitive settings:
   - `DATABASE_URL` – PostgreSQL connection string【391127687261448†L532-L537】.
   - `EMBEDDING_MODEL` – set to `Qwen/Qwen3-Embedding-0.6B` (optionally
     include custom embedding dimension).
   - `LLM_MODEL` – path or identifier for your Qwen3‑VL‑8B‑Instruct weights.
   - Additional settings such as chunk size or ingestion batch size.
4. **Set up the database.**  Enable the PGVector extension and run the
   schema to create the `documents` and `chunks` tables and the
   `match_chunks()` function【391127687261448†L549-L570】.  Create additional
   `tsvector` and `pg_trgm` indexes for lexical and pattern search.
5. **Ingest documents.**  Place files into your ingestion folder and run
   the docling ingestion script.  Adjust chunk size and embedding model
   parameters to suit your use case【391127687261448†L592-L593】.
   See `docs/rag_pipeline_ingestion.md` for the full configuration table and
   CLI flags once you are ready to customise runs.
6. **Develop the agent.**  Implement the RAG assistant using the
   Pydantic AI patterns.  The agent should:
   - Accept user queries.
   - Use the query analyser to decide retrieval weights.
   - Perform dense, lexical and pattern searches and combine results.
   - Assemble a prompt with selected chunks and call the Qwen3‑VL model.
   - Stream the answer back to the user with citations.
7. **Test and iterate.**  Begin with a small corpus and refine retrieval
   heuristics.  Monitor response quality and performance.  Add skills as
   needed for logging or analytics.

## Frontend user interface

The initial implementation focuses on the backend API and ingestion pipeline.
A working frontend example is included under
`PRPs/examples/Front_end_UI_example`, built with React and Vite.  This example
currently targets the Gemini API via a small service helper, but its layout,
session management and chat components are representative of the desired UX
for the local RAG assistant.

Phase‑4 hardening work will adapt that example to call the local FastAPI
`/chat` endpoint instead of the Gemini backend, so that a fully local browser
UI can be used with the same RAG pipeline.  The top‑level `README.md` contains
the current quickstart instructions for running the backend API and, optionally,
the example frontend in development mode.

## Current implementation status

- **Ingestion + retrieval wired.** The Docling ingestion CLI and skill are in place,
  storing chunks in Postgres/PGVector via `SupabaseStore`. `/chat` routes through
  `RAGAgent` using `DatabaseRetriever` plus the configured LLM client; when the DB
  or LLM endpoint is missing it falls back to a deterministic summary so wiring can
  still be validated.
- **Observability.** Correlation IDs thread through retrieval, embeddings, and LLM
  calls. Install the optional `langfuse` dependency (e.g., `pip install langfuse`)
  and enable tracing by setting `LANGFUSE_ENABLED=true` with host
  `http://127.0.0.1:3000` (worker at `http://127.0.0.1:3030`) and providing
  `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` (placeholders in `.env.example`).
  Tracing is no-op when disabled.
- **GPU selection.** Prefer your primary GPU by exporting `CUDA_VISIBLE_DEVICES=0`
  and using `GPU_DEVICE=cuda:0` (default). Logs report the resolved device; if CUDA
  is unavailable the system falls back to CPU. If secondary GPUs are unsupported
  (e.g., GTX 1060 sm_61), PyTorch will warn; pin to `CUDA_VISIBLE_DEVICES=0` to
  keep work on the RTX 3080.
- **Frontend integration pending.** The React/Vite example defaults to the FastAPI
  `/chat` endpoint with a Gemini fallback; further UX polish remains in later plans.

## Ingestion Skill

The ingestion skill wraps the pipeline so that Archon-managed agents can
trigger document refreshes without manual CLI access. It exposes a tool named
`ingestion_skill` with structured docstrings describing when to use it
(reindexing or validation runs), when to avoid it (serving user questions),
and how to control verbosity via the `response_format` flag. Internally it
builds the same services as the CLI, invokes `run_ingestion_job`, and returns
an `IngestionSkillResponse` containing both a human-readable summary and the
raw `IngestionResult` for downstream automation.

Following this architecture will help you build a reliable, extensible and
privacy‑preserving RAG assistant tailored to your organisation’s needs.
