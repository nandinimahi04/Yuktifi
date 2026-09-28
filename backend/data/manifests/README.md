# YUKTI evidence manifests

Each external dataset should have a manifest before it is ingested. Keep raw files under `data/raw/<source>/` and normalize them into YUKTI evidence records.

Required fields: dataset, source, source_url, version/observed_at, geography, format, is_estimate.

The deterministic engines consume structured evidence. Government PDFs/guidelines belong in the RAG index instead of being converted into numeric facts by an LLM.
