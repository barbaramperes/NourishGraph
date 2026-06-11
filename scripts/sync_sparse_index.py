#!/usr/bin/env python3
"""
Sync sparse index with dense index chunks.
Uses Pinecone's integrated sparse embedding model.
"""

import os
import json
import pickle
from pathlib import Path
from pinecone import Pinecone
from dotenv import load_dotenv

# Load env from file directly
load_dotenv(Path(__file__).parent.parent / ".env")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

pc = Pinecone(api_key=PINECONE_API_KEY)

# Get the sparse index that supports integrated embedding
sparse_index = pc.Index("nutriai-papers-openai-sparse")

# Load chunks
DATA_DIR = Path(__file__).parent.parent / "app" / "data"
CHUNKS_FILE = DATA_DIR / "paper_chunks.pkl"

print("Loading chunks...")
with open(CHUNKS_FILE, "rb") as f:
    chunks = pickle.load(f)

print(f"Loaded {len(chunks)} chunks")

# Prepare records for sparse index (using integrated embedding)
batch_size = 96  # Pinecone limit for integrated embeddings

total_upserted = 0
records_batch = []

for i, chunk in enumerate(chunks):
    # Get chunk data
    chunk_id = chunk.chunk_id if hasattr(chunk, 'chunk_id') else f"chunk_{i}"
    text = chunk.text if hasattr(chunk, 'text') else str(chunk.get('text', ''))
    
    if not text or len(text) < 10:
        continue
    
    # Prepare metadata
    metadata = chunk.metadata if hasattr(chunk, 'metadata') else chunk.get('metadata', {})
    
    record = {
        "_id": chunk_id,
        "chunk_text": text[:10000],  # Pinecone limit
        "title": (metadata.get("title") or "")[:200],
        "authors": ", ".join(metadata.get("authors", [])[:3]) if isinstance(metadata.get("authors"), list) else str(metadata.get("authors", ""))[:200],
        "year": metadata.get("year") or 0,
        "paper_id": metadata.get("paper_id") or chunk_id.rsplit("_chunk_", 1)[0] if "_chunk_" in chunk_id else chunk_id,
    }
    
    records_batch.append(record)
    
    if len(records_batch) >= batch_size:
        sparse_index.upsert_records(namespace="__default__", records=records_batch)
        total_upserted += len(records_batch)
        print(f"  Upserted {total_upserted}/{len(chunks)}", end="\r")
        records_batch = []

# Upsert remaining
if records_batch:
    sparse_index.upsert_records(namespace="__default__", records=records_batch)
    total_upserted += len(records_batch)

print(f"\n\n✅ Upserted {total_upserted} records to sparse index")

# Verify
import time
time.sleep(2)  # Wait for index to update
stats = sparse_index.describe_index_stats()
print(f"Sparse index now has: {stats['total_vector_count']} vectors")
