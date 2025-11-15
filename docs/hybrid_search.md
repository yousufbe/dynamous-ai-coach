# Hybrid Search Strategy

RAG systems depend heavily on the retrieval phase.  If relevant context is not
returned, even the best language model cannot answer correctly.  Most RAG
pipelines rely solely on dense embeddings.  While semantic vectors capture
meaning, they often fail to match exact strings like product codes or
serial numbers【445922077582970†L28-L33】.  A hybrid search approach combines
multiple retrieval methods to improve recall and precision.

## Motivation

During experiments with a traditional vector‑only RAG agent, product codes in
a 10 GB corpus were frequently missed despite being present in the
database【445922077582970†L28-L39】.  A direct wildcard search in the database
confirmed the data existed.  This gap led to the exploration of hybrid
retrieval methods【445922077582970†L41-L44】.

## Components of hybrid retrieval

1. **Dense embeddings (semantic search).**  Converts text into vectors
   using Qwen3‑Embedding‑0.6B.  Returns conceptually related chunks even if
   different wording is used.  Weakness: does not guarantee exact string
   matches【445922077582970†L122-L124】.
2. **Sparse lexical search.**  Classic inverted index methods such as BM25
   or TSVector search tokenised words【445922077582970†L129-L144】.  Strength:
   explainable matches and fast exact token matching【445922077582970†L146-L151】.
   Weakness: tokenisation issues with codes and multi‑language content【445922077582970†L154-L159】.
3. **Pattern‑based retrieval.**  Character n‑gram or trigram indexes,
   wildcard and regex searches catch partial matches and typos【445922077582970†L53-L57】.
   Essential for retrieving small identifiers embedded in noisy text.

## Dynamic weighting

The hybrid engine does not treat all methods equally.  It analyses the query
to determine which retrieval mode should be prioritised【445922077582970†L59-L62】:

* If the query resembles a product code or part number (e.g., contains
  hyphens, digits or uppercase letters), the pattern and lexical searches are
  weighted more heavily.
* If the query is conceptual (“Why won’t my freezer make ice?”), dense
  embeddings dominate.【445922077582970†L59-L62】

The final retrieval result is a combined ranking from the three search
strategies.  This ensures that both exact and semantic matches are returned
to the language model.

## Implementation guidelines

* **Vector store:** Use PGVector to store dense embeddings.  Ensure the
  embedding dimension matches the model configuration (default 1024 for
  Qwen3‑Embedding‑0.6B【984059247734186†L98-L105】).  Use cosine similarity or
  inner product for nearest neighbour search.
* **Lexical index:** Create a full‑text index on the chunk text using
  PostgreSQL’s `tsvector` and `ts_rank`.  Tune the analyser for the
  languages present in your documents.
* **Pattern index:** Add trigram or n‑gram indexes (`pg_trgm`) to support
  wildcard, fuzzy and partial matches.  Use SQL queries with `LIKE` or
  `SIMILAR TO` to perform pattern searches.
* **Query analyser:** Implement a simple heuristic (regex) to detect
  identifiers vs. conceptual queries.  Alternatively, use a small
  classifier or the language model itself to choose retrieval weights.
* **Ranking:** Combine results from the three search strategies.  Options
  include linear interpolation of scores or cascade retrieval (e.g., try
  lexical first, then dense if no match).

By integrating hybrid retrieval, you significantly reduce missed details and
increase the reliability of your RAG assistant.