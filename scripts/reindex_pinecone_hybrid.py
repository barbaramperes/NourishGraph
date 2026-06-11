"""
scripts/reindex_pinecone_hybrid.py

Reindex papers to Pinecone with BOTH dense and sparse embeddings.
Following Pinecone's recommended hybrid search approach:
https://docs.pinecone.io/guides/search/hybrid-search

This creates a SEPARATE sparse index alongside the existing dense index.
"""

import os
import sys
import json
import pickle
from pathlib import Path
from dotenv import load_dotenv

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from pinecone import Pinecone

# Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
DENSE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "nutriai-papers")
SPARSE_INDEX_NAME = f"{DENSE_INDEX_NAME}-sparse"

DATA_DIR = Path(__file__).parent.parent / "app" / "data"
CHUNKS_FILE = DATA_DIR / "paper_chunks.pkl"
METADATA_FILE = DATA_DIR / "paper_metadata.json"


def load_chunks():
    """Load text chunks from pickle file."""
    if not CHUNKS_FILE.exists():
        print(f"❌ Chunks file not found: {CHUNKS_FILE}")
        return []
    
    with open(CHUNKS_FILE, "rb") as f:
        chunks = pickle.load(f)
    print(f"✅ Loaded {len(chunks)} chunks")
    return chunks


def create_sparse_index(pc: Pinecone):
    """Create sparse index if it doesn't exist."""
    existing = [idx.name for idx in pc.list_indexes()]
    
    if SPARSE_INDEX_NAME in existing:
        print(f"✅ Sparse index '{SPARSE_INDEX_NAME}' already exists")
        return pc.Index(SPARSE_INDEX_NAME)
    
    print(f"📦 Creating sparse index '{SPARSE_INDEX_NAME}'...")
    
    # Create sparse index with integrated embedding model
    pc.create_index_for_model(
        name=SPARSE_INDEX_NAME,
        cloud="aws",
        region="us-east-1",
        embed={
            "model": "pinecone-sparse-english-v0",
            "field_map": {"text": "chunk_text"}
        }
    )
    
    print(f"✅ Created sparse index '{SPARSE_INDEX_NAME}'")
    return pc.Index(SPARSE_INDEX_NAME)


def upsert_to_sparse_index(sparse_index, chunks, batch_size=32, start_from=0, delay=12):
    """Upsert chunks to sparse index with integrated embeddings.
    
    Args:
        batch_size: Records per batch (32 for free tier rate limits)
        delay: Seconds to wait between batches (12s for free tier — 250k tokens/min)
    """
    import time
    
    print(f"📤 Upserting {len(chunks)} chunks to sparse index")
    print(f"   Batch size: {batch_size}, Delay: {delay}s, Start from: {start_from}")
    print(f"   ⏱️  Estimated time: ~{((len(chunks) - start_from) / batch_size) * delay / 60:.0f} minutes")
    
    records = []
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", "")
        text = chunk.get("text", "")
        
        if not chunk_id or not text:
            continue
        
        records.append({
            "_id": chunk_id,
            "chunk_text": text,  # Field mapped to sparse embedding model
            "paper_id": chunk.get("paper_id", ""),
            "title": chunk.get("metadata", {}).get("title", ""),
            "source": chunk.get("metadata", {}).get("source", ""),
        })
    
    # Upsert in batches with rate limiting
    total = 0
    for i in range(start_from, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            sparse_index.upsert_records("__default__", batch)
            total += len(batch)
            print(f"  ✅ Upserted {i + len(batch)}/{len(records)} records...")
            # Rate limit: wait between batches to avoid 429
            if i + batch_size < len(records):
                print(f"     ⏳ Waiting {delay}s for rate limit...")
                time.sleep(delay)
        except Exception as e:
            print(f"  ❌ Error at batch {i}: {e}")
            print(f"  Resume with start_from={i}")
            raise
    
    print(f"✅ Upserted {total} records to sparse index")


def main():
    print("=" * 60)
    print("PINECONE HYBRID SEARCH REINDEXING")
    print("=" * 60)
    print()
    
    if not PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY not set")
        return
    
    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    
    # Load chunks
    chunks = load_chunks()
    if not chunks:
        return
    
    # Check dense index
    dense_index = pc.Index(DENSE_INDEX_NAME)
    stats = dense_index.describe_index_stats()
    print(f"📊 Dense index: {stats.get('total_vector_count', 0)} vectors")
    
    # Create/get sparse index
    sparse_index = create_sparse_index(pc)
    
    # Check how many are already indexed
    sparse_stats = sparse_index.describe_index_stats()
    already_indexed = sparse_stats.get('total_vector_count', 0)
    print(f"📊 Sparse index: {already_indexed} vectors already indexed")
    
    if already_indexed >= len(chunks):
        print("✅ All chunks already indexed!")
    else:
        # Resume from where we left off
        start_from = already_indexed
        print(f"📍 Resuming from index {start_from}")
        upsert_to_sparse_index(sparse_index, chunks, start_from=start_from)
    
    # Verify
    sparse_stats = sparse_index.describe_index_stats()
    print()
    print("=" * 60)
    print("INDEXING COMPLETE")
    print("=" * 60)
    print(f"Dense index:  {stats.get('total_vector_count', 0)} vectors")
    print(f"Sparse index: {sparse_stats.get('total_vector_count', 0)} vectors")
    print()
    print("Update .env with:")
    print(f"  PINECONE_SPARSE_INDEX_NAME={SPARSE_INDEX_NAME}")


if __name__ == "__main__":
    main()
