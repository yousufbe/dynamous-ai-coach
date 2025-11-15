# AI Agent Development Instructions

## Project Overview

RAG AI Agent that acts as a company assistant that has access to company documents through various RAG tools.
RAG pipeline that pulls company documents from a specific folder and puts them in a vector database to be queried by the agent.

## Core Principles

1. **TYPE SAFETY IS NON-NEGOTIABLE**
   - All functions, methods, and variables MUST have type annotations
   - Strict mypy configuration is enforced
   - No `Any` types without explicit justification

2. **KISS** (Keep It Simple, Stupid)
   - Prefer simple, readable solutions over clever abstractions. Avoid overengineering.

3. **YAGNI** (You Aren't Gonna Need It)
   - Don't build features until they're actually needed

**Architecture:**
```
src/
├── agent/          # Core AI coach
├── tools/          # Independent slices (rag_tools, etc.)
├── rag_pipeline/   # Documents RAG pipeline
└── utils/          # Cross-cutting (config, logging, middleware)
```

Each tool is a vertical slice containing simple tool.py, schemas.py, service.py.

---

## Fine-tuned Embeddings Strategy

- Treat the fine-tuned embeddings workflow as the baseline retrieval plan. Before touching the code, review `PRPs/ai_docs/fine-tuned-embeddings.md` for requirements and `PRPs/examples/fine_tuned_embeddings.py` for the reference agent slice.
- **Data prep:** Build or synthesize domain-specific query/document pairs from the corpus folders; store metadata (source, version, doc ids) so experiments stay reproducible.
- **Training loop:** Fine-tune a SentenceTransformer checkpoint (start with `all-MiniLM-L6-v2`) with MultipleNegativesRankingLoss, track parameters, and persist the resulting model artifact under a versioned path consumable by the ingestion pipeline.
- **Evaluation:** Add regression suites that compare recall@k of the fine-tuned model vs. the base embeddings on held-out validation queries before promoting a new model.
- **Integration:** Update ingestion/retrieval services so `rag_pipeline` uses the versioned fine-tuned model for chunk embeddings, and expose configuration flags to fall back to baseline embeddings when tests need them.
- **Observability:** Log the model fingerprint, training data snapshot, and retrieval performance whenever the agent serves answers so support engineers can trace regressions quickly.

This strategy must stay aligned with KISS/YAGNI: implement only the features that keep the fine-tuned pipeline verifiable, debuggable, and type-safe.

---

## Important reference guides:

- When building tools, reference the guide: `PRPs/ai_docs/tool_guide.md`

- When implementing logging, reference the guide: `PRPs/ai_docs/logging_guide.md`

- When implementing tests, reference the guide: `PRPs/ai_docs/testing_guide.md`

---

## Documentation Style

**Use Google-style docstrings** for all functions, classes, and modules:

```python
def process_request(user_id: str, query: str) -> dict[str, Any]:
    """Process a user request and return results.

    Args:
        user_id: Unique identifier for the user.
        query: The search query string.

    Returns:
        Dictionary containing results and metadata.

    Raises:
        ValueError: If query is empty or invalid.
        ProcessingError: If processing fails after retries.
    """
```

---

## Development Workflow

**Run server:** `uv run uvicorn src.main:app --host 0.0.0.0 --port 8030 --reload`

**Lint/check (must pass):** `uv run ruff check src/ && uv run mypy src/`

**Auto-fix:** `uv run ruff check --fix src/`

**Run tests:** `uv run pytest tests/ -v`

---

## Adding Features

1. Create vertical slice in `src/tools/<name>/`
2. Define Pydantic schemas in `schemas.py` (types first)
3. Implement with proper logging, docstrings, and type annotations
4. **Create corresponding test file** in `tests/tools/<name>/test_<module>.py`
5. Write unit tests for the component
6. Add integration tests if the feature interacts with other components
7. Verify linters pass: `uv run ruff check src/ && uv run mypy src/`
8. Ensure all tests pass: `uv run pytest tests/`

---

## AI Agent Notes

When debugging:
- Check `source` field for file/function location
- Use `correlation_id` to trace full request flow
- Look for `duration_ms` to identify bottlenecks
- Exception logs include full stack traces with local variables (dev mode)
- All context is in structured log fields—use them to understand and fix issues
