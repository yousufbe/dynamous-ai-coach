# Sample Handbook Excerpt

## Mission and Scope
- Equip teams with a private assistant for document Q&A across engineering, operations, and compliance content.
- Keep all processing on self-hosted infrastructure unless an exception is explicitly approved.

## Data Handling Standards
- Store ingested content in PostgreSQL with PGVector and `pg_trgm` enabled.
- Keep source file references and version identifiers in metadata so answers can be traced.
- Retire documents that are older than 18 months unless a steward renews them.

## Support Channels
- Engineering: `#ai-rag-dev`
- Operations: `#ai-rag-ops`
- Security reviews: open a ticket in the `sec-requests` queue with a 2-business-day SLA.
