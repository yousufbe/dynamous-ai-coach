# Modular Skills and the Archon Example

While this project does not rely on Anthropic Claude or the n8n platform, it
takes inspiration from the **Archon Claude skill** included in the
`ottomator‑agents` repository.  Skills are self‑contained modules that
extend an assistant’s capabilities in a token‑efficient manner.

## What are skills?

Skills are like plug‑ins for large language models.  They encapsulate a
specific workflow – such as interacting with an API, processing a file type
or managing a knowledge base – and provide metadata that tells the model
when to activate them.  According to the Archon skill guide, skills are
modular, shareable and automatically invoked based on context【898591313443642†L80-L104】.

Key characteristics【898591313443642†L80-L104】:

* **Model‑invoked.**  The model decides when to use a skill based on the
  request context; the user doesn’t need to manually trigger it.
* **Modular.**  Each skill lives in its own folder with instructions and
  resources, making it easy to add or remove functionality.
* **Shareable.**  Teams can share skills via Git; they encapsulate best
  practices and workflows.
* **Composable.**  Multiple skills can be combined to handle complex tasks.

## Archon skill overview

The Archon skill wraps a knowledge base and task management API called
Archon.  Instead of running an MCP server that consumes thousands of
tokens at session start, the skill uses only dozens of tokens for
metadata【898591313443642†L6-L18】.  It includes a Python client, API
documentation and interactive setup flows, demonstrating how to build
production‑ready skills that leverage existing APIs【898591313443642†L22-L28】.

Although the Archon skill is tailored for Claude Code, its architecture
offers lessons for this project:

* **Token efficiency.**  By loading only metadata until the skill is needed,
  the agent conserves context window and speeds up responses.
* **Separation of concerns.**  Complex back‑end logic (project management,
  knowledge search) lives in the skill rather than in the core agent.  This
  keeps the main agent prompt small and maintainable.
* **Reusability.**  The same skill can be reused across different agents or
  projects without modification.

## Applying the concept here

For your local RAG assistant, consider building small, focused modules
inspired by skills.  Examples:

* A **document ingestion skill** that encapsulates docling and PGVector
  operations.
* A **user analytics skill** that logs queries and tracks usage for
  monitoring and improvement.
* An **admin skill** that manages user permissions and data retention.

Each module should expose a simple API or function that the main agent can
invoke.  Use Pydantic models to define inputs and outputs, and keep
metadata minimal so the agent can decide when to call a module.  Even
though these skills won’t run inside Claude Code, following the modular
pattern helps keep your agent maintainable and extensible.