# Document Processing with Docling

Docling is an open‑source document processing pipeline that simplifies
ingestion for RAG systems.  It converts various file formats into
tokenisable text, generates embeddings and stores them in a PGVector
database.  The docling RAG agent referenced in this project serves as
inspiration for building a similar pipeline in Python (without n8n).

## Supported formats

Docling automatically detects and converts the following formats【391127687261448†L572-L585】:

| Format | Notes |
|---|---|
| **PDF** (`.pdf`) | Handles scanned and digital PDFs.  Use OCR to
preserve layout when necessary【445922077582970†L66-L84】. |
| **Word** (`.docx`, `.doc`) | Converts text and inline images to Markdown. |
| **PowerPoint** (`.pptx`, `.ppt`) | Extracts slide text for embedding. |
| **Excel** (`.xlsx`, `.xls`) | Processes cell content; optionally flatten
tables into text. |
| **HTML / Markdown** (`.html`, `.htm`, `.md`, `.markdown`) | Cleans and
normalises markup to plain text. |
| **Plain text** (`.txt`) | Directly ingested as is. |
| **Audio** (`.mp3`) | Transcribes speech using Whisper Turbo ASR
with timestamps【391127687261448†L600-L604】. |

## Ingestion workflow

1. **Environment setup.**  Install Python 3.9+ and dependencies such as
   `docling`, `pgvector`, `psycopg2`, `sentence-transformers` and `whisper`.
2. **Database configuration.**  Provision a PostgreSQL instance with the
   PGVector extension enabled.  Execute the schema file to create the
   `documents` table, `chunks` table and the `match_chunks()` function for
   vector similarity search【391127687261448†L549-L570】.
3. **Place documents.**  Add files to the `documents/` folder.  Docling
   supports batch ingestion; it will clear existing data by default to
   prevent duplicates【391127687261448†L594-L596】.
4. **Run ingestion.**  Execute the ingestion script (`python -m
   ingestion.ingest --documents documents/`).  The pipeline:
   - Detects file type and uses appropriate parser【391127687261448†L600-L602】.
   - Transcribes audio to text (if applicable)【391127687261448†L600-L604】.
   - Converts content to Markdown for consistent chunking【391127687261448†L600-L604】.
   - Splits text into semantic chunks (default size 1000 tokens)【391127687261448†L592-L593】.
   - Generates embeddings using the configured model (replaced with Qwen3
     embeddings in this project).
   - Stores chunks and metadata in PGVector【391127687261448†L569-L570】.
5. **Query via CLI.**  After ingestion, run the CLI to ask questions
   interactively.  The agent will stream responses and cite sources【391127687261448†L613-L641】.

## Adapting Docling for this project

Although the original docling RAG agent uses OpenAI models, you can
substitute Qwen3‑Embedding‑0.6B for embeddings and Qwen3‑VL‑8B‑Instruct for
generation.  Modify the ingestion script to call the Qwen embedding API or
load the model locally.  Ensure that chunking and embedding dimensions match.

Hybrid search integration will require additional indexes: in addition to
PGVector, create text search indexes (e.g., TSVector) and trigram or n‑gram
indexes to support wildcard and fuzzy matching.  See
`docs/hybrid_search.md` for more details.

## Notes on audio and OCR

When ingesting audio or scanned documents, transcription and OCR quality
affects retrieval.  Use high‑quality Whisper models and consider
maintaining timestamps for referencing audio segments.  Qwen3‑VL’s
expanded OCR capabilities【230556131312387†L84-L90】 can also be leveraged
if images are passed directly to the assistant during inference.