# YUKTI RAG

YUKTI uses a grounded retrieval layer for unstructured government documents such as scheme guidelines, circulars, regulations and methodology reports.

**Structured datasets do not go into RAG.** Census, prices, livestock, rainfall, competitors and geospatial facts are stored as evidence and queried/calculated deterministically.

Flow:

`Government documents -> chunks -> retrieval -> grounded context -> LLM explanation`

Endpoints:
- `POST /api/rag/ingest` with `{path, source, source_url, effective_date}`
- `POST /api/rag/query` with `{query, top_k, use_llm}`

The current local retriever is dependency-light lexical retrieval. It is intentionally replaceable with an embedding/hybrid backend later without changing the API contract.
