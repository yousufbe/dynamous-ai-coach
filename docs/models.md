# Models

This document summarises the models chosen for the local RAG assistant and
explains why they are appropriate for the task.  The models are open and can
be deployed locally to preserve privacy.

## Qwen3‑VL‑8B‑Instruct (assistant model)

**Type:** Vision‑language instruction‑tuned model (8 billion parameters).  
**Context length:** Native 256 K tokens (expandable to 1 M)【230556131312387†L78-L80】.  
**Modalities:** Text and images; supports multi‑image and video input【230556131312387†L55-L90】.  
**Key capabilities:**

* **Superior text understanding and generation** – provides high‑quality
  responses similar to pure LLMs【230556131312387†L58-L92】.
* **Advanced visual perception and spatial reasoning** – can recognise objects,
  judge positions and handle occlusions【230556131312387†L69-L76】.
* **Extended OCR** – supports 32 languages, robust under low light and with
  tilted or blurry text【230556131312387†L84-L89】.  This helps when documents
  include images of scanned text or diagrams.
* **Long context** – the large context window enables processing of entire
  manuals or long PDFs without losing earlier content【230556131312387†L78-L80】.
* **Agent interaction** – designed to recognise UI elements and invoke tools
  when integrated into automation flows【230556131312387†L69-L71】.

These features make Qwen3‑VL‑8B‑Instruct well suited for a company assistant
that needs to handle lengthy documents, images and tables, while running
entirely on local hardware.

## Qwen3‑Embedding‑0.6B (embedding model)

**Type:** Text embedding model (0.6 billion parameters).  
**Context length:** 32 K tokens【984059247734186†L99-L104】.  
**Embedding dimension:** User configurable between 32 and 1024 dimensions (default
1024)【984059247734186†L98-L105】.  
**Languages:** Supports over 100 languages and various programming languages
【984059247734186†L90-L93】.

**Highlights:**

* **Dense semantic vectors** – produces high‑quality embeddings that achieve
  state‑of‑the‑art performance on text retrieval, classification and
  clustering tasks【984059247734186†L65-L84】.
* **Multilingual capability** – can embed queries and documents across
  languages for cross‑lingual search【984059247734186†L90-L93】.
* **Flexible dimensionality** – supports lower dimensions for efficiency or
  full 1024 dimensions for maximum quality【984059247734186†L98-L105】.

Qwen3‑Embedding‑0.6B is used in this project to generate the dense vector
representations for document chunks.  Combined with PGVector and lexical
indexes, these embeddings form one of the three pillars of the hybrid
retrieval system.

## Alternatives and fallbacks

If hardware limitations prevent running the full 8 B model, smaller variants
such as **Qwen3‑VL‑1B‑Instruct** or **Mistral‑7B** can be substituted.  They
provide shorter context windows and reduced quality but still support local
deployment.  Always ensure the embedding model remains consistent across
retrieval and generation to avoid mismatch.