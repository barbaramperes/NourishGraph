# Papers corpus

The scientific articles used as the RAG knowledge base are **not redistributed**
in this repository for copyright reasons.

This directory normally contains:

- `pdf/` — source article PDFs
- `txt/` — extracted plain text used for chunking and indexing

## Reproducing the index

1. Place the article PDFs/TXT you are licensed to use under `papers/pdf/` and `papers/txt/`.
2. Run the reindexing script to (re)build embeddings and push them to Pinecone:

   ```bash
   python scripts/reindex_pinecone_hybrid.py
   ```

The fitted sparse vectorizer (`app/data/sparse_vectorizer.pkl`) and article
metadata (`app/data/paper_metadata.json`) are included so the pipeline structure
is reproducible without the raw corpus.
