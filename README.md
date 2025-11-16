# Local RAG AI Assistant – Foundation

Welcome to the **Local RAG AI Assistant** project.  This repository provides a
foundation for building an on‑premise retrieval‑augmented generation (RAG)
assistant for company employees.  The aim is to enable private, high‑quality
question answering over your organisation’s documents without sending data to
external services.  It combines state‑of‑the‑art open models, robust
document processing, a hybrid search pipeline and agent‑tracking skills.

## Why build a local RAG assistant?

Retrieval‑augmented generation systems answer questions by retrieving relevant
context from a collection of documents and passing that context into a
language model.  Many RAG pipelines rely solely on dense vector embeddings.
Dense vectors capture semantic meaning but struggle with exact values such as
product codes, serial numbers or small tokens hidden in messy PDFs【445922077582970†L28-L33】.  A
hybrid search approach combines dense, lexical and pattern matching methods
【445922077582970†L49-L57】, enabling the assistant to find both conceptual
information and exact identifiers reliably.  This foundation adopts a hybrid
retrieval strategy to ensure minor details are never missed.

## Key components

This project draws inspiration from the [otto­mator‑agents](https://github.com/coleam00/ottomator-agents)
and [context engineering template](https://github.com/coleam00/context-engineering-intro/tree/main/use-cases/pydantic-ai).
The following building blocks are provided:

| Component | Purpose | References |
|---|---|---|
| **Qwen3‑VL‑8B‑Instruct** | Multimodal instruction‑tuned LLM that supports
256K context length, enhanced visual and spatial reasoning, expanded OCR and
advanced multimodal understanding【230556131312387†L55-L90】.  Used as the primary
assistant model. | Qwen model card |
| **Qwen3‑Embedding‑0.6B** | High‑quality multilingual text embedding model
with a 32k context window and up to 1024‑dimensional embeddings【984059247734186†L65-L104】.
Provides dense semantic vectors for vector search. | Qwen embedding card |
| **Docling** | Document processing pipeline that converts PDFs, Word, PowerPoint,
Excel, HTML, Markdown, text and MP3 audio into clean text chunks and embeds
them into a PGVector database【391127687261448†L490-L605】.  Supports audio transcription via
Whisper and provides an interactive CLI for RAG queries. | Docling RAG agent |
| **Hybrid search engine** | Combines dense vector search, sparse lexical search
(BM25/TSVector) and pattern‑based retrieval (wildcards, n‑grams and fuzzy
matching) to overcome the limitations of single‑method retrieval【445922077582970†L49-L60】.
The agent dynamically adjusts weights based on the query type so that codes
and exact strings can be found while still returning semantically related
content【445922077582970†L61-L62】. | Hybrid search article |
| **Fine‑tuned embeddings pipeline** | Custom SentenceTransformer fine‑tuning loop that
learns from your own query/document pairs so retrieval reflects domain jargon.
Includes a reference slice in `PRPs/examples/fine_tuned_embeddings.py` plus a
process guide in `PRPs/ai_docs/fine-tuned-embeddings.md` covering data prep,
training, evaluation and rollout considerations. | Philipp Schmid tutorial |
| **Archon Claude skill** | Example of a Claude Code skill that wraps an
existing knowledge base API in a token‑efficient interface【898591313443642†L6-L31】.
Skills provide modular, shareable and automatically invoked capabilities for
agent tracking and task management【898591313443642†L80-L104】.  While this project does
not use the n8n environment, the skill demonstrates how to integrate
workflow features into a Python agent. | Archon skill guide |

## Repository structure

```
local_rag_assistant/
├── README.md               # This overview
├── PRPs/
│   ├── INITIAL.md          # Initial requirements for your agent
│   ├── ai_docs/            # Design guides (logging, tools, testing, embeddings)
│   ├── examples/           # Reference pipeline, SQL, and UI examples
│   └── requests/           # Implementation plans (rag pipeline, validation, phase 4)
└── docs/
    ├── models.md           # Details on the chosen models
    ├── docling.md          # Document ingestion & processing guide
    ├── hybrid_search.md    # Explanation of the hybrid search strategy
    ├── archon_SKILL.md     # Summary of the Archon skill concept
    ├── architecture.md     # High‑level architecture and setup guidance
    └── rag_pipeline_ingestion.md  # RAG ingestion config, env vars, and CLI usage
```

## Quickstart: run the local assistant

This section is a concrete “clone → configure → run” guide for the current
codebase. It focuses on getting the backend API and ingestion pipeline running
against your own PostgreSQL database. The frontend UI is provided as an example
under `PRPs/examples/Front_end_UI_example` and will be integrated more tightly
in a future phase. If you need a diagram-first view of how the pieces fit
together, skim `docs/architecture.md` first and then return here for the exact
commands.

### Prerequisites: required vs optional components

| Component | Required for “first question answered”? | Notes |
| --- | --- | --- |
| Python 3.11+, `uv` or `pip`, and GNU build tools | ✅ | Needed to create the virtual environment and install backend dependencies. |
| PostgreSQL with `vector` (PGVector) and `pg_trgm` extensions | ✅ | Provides the storage queried by the agent. A local instance or Supabase project both work. |
| `RAG_DATABASE_URL` / `DATABASE_URL` plus `psycopg[binary]` | ✅ | Required so ingestion can store chunks and the API can connect to the same database. |
| Qwen embedding API key (`QWEN_API_KEY`) | ✅ | Needed for Docling chunk embeddings during ingestion. |
| React/Vite frontend toolchain (Node.js 18+, pnpm/npm) | Optional | Only required if you want to run the example UI today. |
| Docling optional extras (Whisper, OCR dependencies) | Optional | Install once you need advanced conversions; the default text chunker works for plain Markdown/Text. |
| Fine-tuned embeddings workflow (`PRPs/examples/fine_tuned_embeddings.py`) | Optional | Run after you have baseline retrieval metrics. Not needed for smoke tests. |
| Performance tests under `tests/performance/` | Optional | Opt-in benchmarks that require extra data and runtime. |

When in doubt, start with the required items, confirm you can ingest and hit the
`/chat` endpoint, and then layer in the optional enhancements as you harden the
deployment.

### 1. Clone the repo and create a Python environment

```bash
git clone https://github.com/<your-org>/local_rag_assistant-codex.git
cd local_rag_assistant-codex

python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env  # fill in database + model values before running anything
```

If you prefer `uv`, you can instead create and use a uv-managed environment and
run commands with `uv run`.

### 2. Provision PostgreSQL with PGVector

1. Start a local PostgreSQL instance (or Supabase project) with:
   - `vector` (PGVector) extension enabled.
   - `pg_trgm` extension enabled for trigram search.
2. Create a database (for example `rag_local`).
3. Apply the ingestion schema:

```bash
export DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/rag_local"
psql "$DATABASE_URL" -f PRPs/examples/rag_pipeline_docling_supabase.sql
```

For the ingestion pipeline, set `RAG_DATABASE_URL` as well. In a simple local
setup you can point both variables at the same database:

```bash
export RAG_DATABASE_URL="$DATABASE_URL"
```

The full list of ingestion-related environment variables is documented in
`docs/rag_pipeline_ingestion.md`.

### 3. Configure the LLM and embedding model

The agent and pipeline are configuration‑driven:

- `EMBEDDING_MODEL` (default: `Qwen/Qwen3-Embedding-0.6B`)
- `LLM_MODEL` (default: `Qwen/Qwen3-VL-8B-Instruct`)
- `LLM_BASE_URL` (OpenAI-compatible chat endpoint; leave blank to use the local fallback)
- `LLM_API_KEY` (token for the configured LLM endpoint)
- `QWEN_API_KEY` (used by the embedding client when calling hosted Qwen APIs)
- `RETRIEVAL_TOP_K` / `RETRIEVAL_MIN_SCORE` (tune how many chunks are pulled into prompts)
- `QWEN_EMBEDDING_BASE_URL` (optional override for the embedding endpoint)

For a minimal local setup you can start by accepting the default model names
and providing only the embedding API key:

```bash
export EMBEDDING_MODEL="Qwen/Qwen3-Embedding-0.6B"
export LLM_MODEL="Qwen/Qwen3-VL-8B-Instruct"
export QWEN_API_KEY="sk-..."                  # from your Qwen/DashScope account
export LLM_BASE_URL="http://localhost:11434" # or your hosted endpoint, if available
export LLM_API_KEY="sk-..."                  # omit when using the fallback response
```

The agent’s high‑level configuration is defined in `src/shared/config.py`, and
the ingestion‑specific configuration (chunk sizes, source directories, retries)
is defined in `src/rag_pipeline/config.py` and documented in
`docs/rag_pipeline_ingestion.md`.

### 4. Ingest documents into the database

1. Place your documents under `./documents` (the default) or configure
   `RAG_SOURCE_DIRS` to point to one or more folders:

   ```bash
   export RAG_SOURCE_DIRS="./documents"
   ```

2. Optionally tweak chunking and embedding settings (see the table in
   `docs/rag_pipeline_ingestion.md` for all available environment variables).

3. Run the ingestion CLI to populate the database:

   ```bash
   uv run python -m src.rag_pipeline.cli --output-format text
   # or, if using plain Python:
   python -m src.rag_pipeline.cli --output-format text
   ```

The CLI will scan your folders, send chunks to the embedding service, and write
results into the configured PostgreSQL database. A non‑zero exit code indicates
ingestion failures; see `docs/rag_pipeline_ingestion.md` and
`docs/post_ingestion_validation.md` for troubleshooting guidance.

### 5. Run the backend API

Start the FastAPI application that exposes health checks and the `/chat`
endpoint:

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8030 --reload
```

You can then:

- Check health: `curl http://localhost:8030/health`
- Send a test chat request:

  ```bash
  curl -X POST http://localhost:8030/chat \
    -H "Content-Type: application/json" \
    -d '{"query": "How do I use this assistant?"}'
  ```

This will exercise the agent wiring and logging. Once retrieval and generation
are fully connected to the ingestion pipeline, this endpoint will return
answers grounded in your ingested documents.

### 6. (Optional) Try the example frontend UI

A working frontend UI example built with React and Vite lives in
`PRPs/examples/Front_end_UI_example`. It currently targets the Gemini API via a
`geminiService` helper. The planned Phase 4 work will adapt this example to use
the local FastAPI `/chat` endpoint instead so you can run a fully local UI.

For now you can run the example as‑is to explore the UI patterns:

```bash
cd PRPs/examples/Front_end_UI_example
npm install
npm run dev
```

Refer to `PRPs/examples/Front_end_UI_example/README.md` for the latest details.

### What you get after setup

Once you complete Steps 1–6 you should have:

- A running PostgreSQL instance with the Docling/PGVector schema applied and
  your first ingestion run logged in `uv run python -m src.rag_pipeline.cli`.
- Structured ingestion logs showing chunk counts, retries, and failures; use
  `docs/post_ingestion_validation.md` to compare results or capture follow-up
  observations.
- The FastAPI server responding to `GET /health` and to the `POST /chat` curl
  snippet above. The current `RAGAgent.chat` still returns a placeholder answer
  so you can verify wiring before retrieval is fully connected.
- Optional: the React/Vite UI running locally against Gemini until Phase 2
  rewires it for the FastAPI backend. The architecture doc tracks that work.

Call out the placeholder behaviour in onboarding conversations so early users
know ingestion/logging/tests are already production-grade while retrieval and
frontend wiring are being finished in the “End-to-End Developer & User
Experience” plan.

## Getting started

1. **Define your requirements.**  Fill out `PRPs/INITIAL.md` with
   organisational details: document types, privacy constraints, user roles and
   use‑cases.  Follow the context engineering template’s guidelines to keep
   requirements focused and avoid over‑engineering【848933225286564†L23-L55】.

2. **Read the documentation.**  The `docs/` folder summarises the models,
   docling pipeline, hybrid search strategy and Archon skill.  These files
   provide citations back to the original sources for deeper research.

3. **Set up your environment.**  Prepare a Python environment (>=3.9) and
   install dependencies such as `transformers`, `sentence-transformers`,
   `docling`, `psycopg2` and `pgvector`.  Provision a PostgreSQL database with
   the PGVector extension.  Use Qwen3‑Embedding‑0.6B for computing dense
   vectors and Qwen3‑VL‑8B‑Instruct as the assistant model.  See
   `docs/architecture.md` for more guidance.

4. **Ingest documents.**  Place your corporate documents into an ingestion
   folder and run the docling ingestion pipeline to populate the PGVector
   database【391127687261448†L572-L607】.  Use hybrid search in your retrieval layer to
   dynamically switch between dense, lexical and pattern modes based on the
   query type【445922077582970†L49-L62】.

5. **Fine-tune embeddings.**  Gather high-signal question/answer pairs (or
   synthesize them) from your corpus, then follow
   `PRPs/ai_docs/fine-tuned-embeddings.md` and
   `PRPs/examples/fine_tuned_embeddings.py` to train a domain-specific
   SentenceTransformer checkpoint, evaluate it against the base model, and
   version the artifact so your ingestion/retrieval stack can swap models
   without code edits.

6. **Develop and test the agent.**  Implement your agent using the Pydantic
   AI patterns described in the context engineering template.  Start simple
   and only add tools that serve your core purpose.
   Use the Archon skill as inspiration for building modular capabilities and
   for tracking tasks.

7. **Iterate and refine.**  Use the agent with a small group of employees,
   gather feedback and update your requirements.  Expand the document corpus
   and refine the hybrid search weights as needed.



This foundation is meant to be a starting point.  Customise it to your
organisation’s needs and follow best practices for security, privacy and
performance.  The references cited throughout the documentation link back to
the original resources for further reading and verification.
