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
│   └── INITIAL.md          # Initial requirements for your agent
└── docs/
    ├── models.md           # Details on the chosen models
    ├── docling.md          # Document ingestion & processing guide
    ├── hybrid_search.md    # Explanation of the hybrid search strategy
    ├── skill_archon.md     # Summary of the Archon skill concept
    └── architecture.md     # High‑level architecture and setup guidance
```

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
