"""
app/rag_hybrid.py

Hybrid Search (Dense + Sparse + Reranking) for nutrition papers.
Uses Pinecone's native hybrid search approach:
https://docs.pinecone.io/guides/search/hybrid-search

Architecture:
- Dense Index: OpenAI text-embedding-3-small (1536 dims)
- Sparse Index: Pinecone pinecone-sparse-english-v0 (integrated)
- Reranking: Pinecone bge-reranker-v2-m3 (hosted)

Pipeline:
1. Query → Dense embedding (OpenAI) + Sparse embedding (Pinecone)
2. Search both indexes in parallel
3. Merge and deduplicate results
4. Rerank with Pinecone's hosted reranker
5. Return top-k results
"""

from __future__ import annotations

from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
import pickle
import json
import os
import re
import logging
import hashlib
import math
from functools import lru_cache
from collections import Counter

try:
    from pinecone import Pinecone
except ImportError:
    Pinecone = None  # type: ignore
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
DENSE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "nutriai-papers")
SPARSE_INDEX_NAME = os.getenv("PINECONE_SPARSE_INDEX_NAME", f"{DENSE_INDEX_NAME}-sparse")

# Hybrid search: dense + sparse enabled by default
USE_SPARSE = os.getenv("USE_SPARSE_SEARCH", "true").lower() == "true"

# Hybrid fusion weight: 0.7 = 70% semantic, 30% lexical
ALPHA = float(os.getenv("HYBRID_ALPHA", "0.7"))

TOP_K_SEARCH = 40   # Results from each index
TOP_K_FINAL = 5     # Final results after reranking

DATA_DIR = Path(__file__).resolve().parent / "data"
METADATA_FILE = DATA_DIR / "paper_metadata.json"
CHUNKS_FILE = DATA_DIR / "paper_chunks.pkl"

# ============================================================
# LOAD PAPERS METADATA
# ============================================================

def load_paper_metadata() -> Tuple[List[Dict], Dict[str, Dict], Dict[str, Dict]]:
    """Load paper metadata from JSON file."""
    if not METADATA_FILE.exists():
        logger.warning(f"Metadata file not found: {METADATA_FILE}")
        return [], {}, {}
    
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        papers = json.load(f)
    
    id_to_paper = {p["id"]: p for p in papers}
    
    # Create filename lookup for fallback
    filename_to_paper = {}
    for p in papers:
        fname = p.get("filename", "")
        if fname:
            filename_to_paper[fname] = p
            filename_to_paper[fname.replace(".pdf", "")] = p
            filename_to_paper[fname.replace(".pdf", ".txt")] = p
    
    return papers, id_to_paper, filename_to_paper


def load_chunks() -> List[Dict]:
    """Load text chunks from pickle file."""
    if not CHUNKS_FILE.exists():
        logger.warning(f"Chunks file not found: {CHUNKS_FILE}")
        return []
    
    with open(CHUNKS_FILE, "rb") as f:
        chunks = pickle.load(f)
    return chunks


# Load data at initialization
_PAPERS, _ID_TO_PAPER, _FILENAME_TO_PAPER = load_paper_metadata()
_CHUNKS = load_chunks()

logger.info(f"RAG initialized: {len(_PAPERS)} papers, {len(_CHUNKS)} chunks")


def _find_paper(paper_id: str, source: str = "", title: str = "") -> Dict:
    """Find paper by ID, filename, or title."""
    if paper_id and paper_id in _ID_TO_PAPER:
        return _ID_TO_PAPER[paper_id]
    
    if source:
        fname = Path(source).name if source else ""
        if fname in _FILENAME_TO_PAPER:
            return _FILENAME_TO_PAPER[fname]
        fname_noext = fname.replace(".pdf", "").replace(".txt", "")
        if fname_noext in _FILENAME_TO_PAPER:
            return _FILENAME_TO_PAPER[fname_noext]
    
    if title and len(title) > 10:
        title_lower = title.lower().strip()
        for p in _PAPERS:
            p_title = p.get("title", "").lower().strip()
            if p_title.startswith(title_lower[:40]) or title_lower.startswith(p_title[:40]):
                return p
    
    return {}


def _normalize_title(title: str) -> str:
    """Normalize title for deduplication."""
    if not title:
        return ""
    normalized = re.sub(r'[^a-z0-9\s]', '', title.lower())
    normalized = ' '.join(normalized.split())
    return normalized[:50]


# ============================================================
# OPENAI EMBEDDINGS (Dense)
# ============================================================

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
_OPENAI_CLIENT = None

try:
    from openai import OpenAI
    _OPENAI_CLIENT = OpenAI()
    logger.info(f"Embeddings: OpenAI ({EMBEDDING_MODEL_NAME})")
except Exception as e:
    logger.error(f"OpenAI client error: {e}")


@lru_cache(maxsize=500)
def _cached_get_embedding(text_hash: str, text: str) -> tuple:
    """Cached version of get_embedding."""
    if _OPENAI_CLIENT:
        response = _OPENAI_CLIENT.embeddings.create(
            model=EMBEDDING_MODEL_NAME,
            input=text
        )
        return tuple(response.data[0].embedding)
    else:
        raise RuntimeError("OpenAI client not initialized")


def get_embedding(text: str) -> List[float]:
    """Get dense embedding for text using OpenAI."""
    text_hash = hashlib.md5(text.encode()).hexdigest()
    return list(_cached_get_embedding(text_hash, text))


# ============================================================
# LOCAL FALLBACK SEARCH (TF-IDF over papers/txt/)
# ============================================================

PAPERS_TXT_DIR = Path(__file__).resolve().parent.parent / "papers" / "txt"

_LOCAL_DOCS: List[Dict] = []     # [{filename, title, text, tokens}]
_LOCAL_IDF: Dict[str, float] = {}
_LOCAL_READY = False


def _tokenize(text: str) -> List[str]:
    """Simple whitespace + lowercase tokenizer."""
    return re.findall(r"[a-z0-9]{2,}", text.lower())


def _build_local_index():
    """Build a lightweight TF-IDF index over papers/txt/ files."""
    global _LOCAL_DOCS, _LOCAL_IDF, _LOCAL_READY

    if not PAPERS_TXT_DIR.exists():
        logger.warning(f"papers/txt directory not found: {PAPERS_TXT_DIR}")
        return

    doc_freq: Counter = Counter()
    docs: List[Dict] = []

    for txt_file in sorted(PAPERS_TXT_DIR.glob("*.txt")):
        try:
            text = txt_file.read_text(encoding="utf-8", errors="ignore")
            if len(text) < 100:
                continue
            tokens = _tokenize(text)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                doc_freq[t] += 1

            # Try to match metadata
            fname_stem = txt_file.stem
            paper = {}
            for p in _PAPERS:
                p_stem = p.get("filename", "").replace(".pdf", "")
                if p_stem and (p_stem == fname_stem or fname_stem.startswith(p_stem[:40])):
                    paper = p
                    break

            docs.append({
                "filename": txt_file.name,
                "title": paper.get("title", fname_stem.replace("_", " ")),
                "authors": paper.get("authors", []),
                "year": paper.get("year"),
                "paper_id": paper.get("id", fname_stem),
                "source": paper.get("source", "PDF"),
                "text": text,
                "tokens": tokens,
                "token_counts": Counter(tokens),
            })
        except Exception as e:
            logger.debug(f"Skipping {txt_file.name}: {e}")

    # Compute IDF
    n_docs = len(docs)
    idf: Dict[str, float] = {}
    if n_docs > 0:
        for term, df in doc_freq.items():
            idf[term] = math.log((n_docs + 1) / (df + 1)) + 1.0

    _LOCAL_DOCS = docs
    _LOCAL_IDF = idf
    _LOCAL_READY = True
    logger.info(f"Local fallback index built: {len(docs)} documents, {len(idf)} terms")


def local_search(query: str, top_k: int = 5) -> List[Dict]:
    """
    TF-IDF search over local papers/txt/ files.
    Used as fallback when Pinecone is not available.
    """
    if not _LOCAL_READY:
        _build_local_index()
    if not _LOCAL_DOCS:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    # Also expand query with synonyms
    expanded_tokens = list(query_tokens)
    query_lower = query.lower()
    for term, synonyms in QUERY_SYNONYMS.items():
        if term in query_lower:
            for syn in synonyms[:2]:
                expanded_tokens.extend(_tokenize(syn))

    # Score each document with TF-IDF cosine-like scoring
    scored: List[Tuple[float, int]] = []
    for idx, doc in enumerate(_LOCAL_DOCS):
        score = 0.0
        doc_len = len(doc["tokens"]) or 1
        for qt in expanded_tokens:
            tf = doc["token_counts"].get(qt, 0) / doc_len
            idf = _LOCAL_IDF.get(qt, 0)
            score += tf * idf
        if score > 0:
            scored.append((score, idx))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Normalise scores to 0-1 range
    max_score = scored[0][0] if scored else 1.0

    results = []
    for score, idx in scored[:top_k]:
        doc = _LOCAL_DOCS[idx]
        # Extract a relevant snippet (first 800 chars around first query term match)
        snippet = _extract_snippet(doc["text"], query_tokens)
        results.append({
            "id": doc["paper_id"],
            "title": doc["title"],
            "abstract": snippet,
            "year": doc.get("year"),
            "source": doc.get("source", "PDF"),
            "authors": doc.get("authors", []),
            "filename": doc["filename"].replace(".txt", ".pdf"),
            "paper_id": doc["paper_id"],
            "score_dense": round(score / max_score, 4) if max_score else 0,
            "score_sparse": 0,
            "score_hybrid": round(score / max_score, 4) if max_score else 0,
            "rerank_score": round(score / max_score, 4) if max_score else 0,
        })

    return results


def _extract_snippet(text: str, query_tokens: List[str], window: int = 400) -> str:
    """Extract a relevant snippet of text around the first query match."""
    text_lower = text.lower()
    best_pos = -1
    for qt in query_tokens:
        pos = text_lower.find(qt)
        if pos != -1:
            best_pos = pos
            break

    if best_pos == -1:
        return text[:800]

    start = max(0, best_pos - window // 2)
    end = min(len(text), best_pos + window)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


# ============================================================
# PINECONE CONNECTION
# ============================================================

_pc = None
_dense_index = None
_sparse_index = None
HAS_DENSE = False
HAS_SPARSE = False

if PINECONE_API_KEY and Pinecone is not None:
    try:
        _pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # Connect to dense index
        _dense_index = _pc.Index(DENSE_INDEX_NAME)
        dense_stats = _dense_index.describe_index_stats()
        logger.info(f"Dense index connected: {dense_stats.get('total_vector_count', 0)} vectors")
        HAS_DENSE = True
        
        # Try to connect to sparse index (only if enabled)
        if USE_SPARSE:
            try:
                existing_indexes = [idx.name for idx in _pc.list_indexes()]
                if SPARSE_INDEX_NAME in existing_indexes:
                    _sparse_index = _pc.Index(SPARSE_INDEX_NAME)
                    sparse_stats = _sparse_index.describe_index_stats()
                    logger.info(f"Sparse index connected: {sparse_stats.get('total_vector_count', 0)} vectors")
                    HAS_SPARSE = True
                else:
                    logger.info(f"Sparse index '{SPARSE_INDEX_NAME}' not found - using dense-only search")
            except Exception as e:
                logger.warning(f"Sparse index not available: {e}")
        else:
            logger.info("Sparse search disabled (USE_SPARSE_SEARCH=false)")
        
    except Exception as e:
        logger.error(f"Pinecone connection error: {e}")


# ============================================================
# DENSE SEARCH (Semantic - OpenAI embeddings)
# ============================================================

def dense_search(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict]:
    """
    Semantic search using dense embeddings.
    Uses OpenAI text-embedding-3-small → Pinecone dense index.
    """
    if not HAS_DENSE or not _dense_index:
        return []
    
    try:
        # Get dense embedding from OpenAI
        q_emb = get_embedding(query)
        
        # Query dense index
        res = _dense_index.query(
            vector=q_emb,
            top_k=top_k,
            include_metadata=True,
            namespace="papers"
        )
        
        results = []
        for match in res.get("matches", []):
            metadata = match.get("metadata", {})
            chunk_id = match["id"]
            
            paper_id = metadata.get("paper_id", "")
            if not paper_id and "_chunk_" in chunk_id:
                paper_id = chunk_id.rsplit("_chunk_", 1)[0]
            
            results.append({
                "id": chunk_id,
                "score": float(match["score"]),
                "title": metadata.get("title", ""),
                "text": metadata.get("text", ""),
                "source": metadata.get("source", ""),
                "year": metadata.get("year"),
                "authors": metadata.get("authors", ""),
                "paper_id": paper_id or chunk_id,
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Dense search error: {e}")
        return []


# ============================================================
# SPARSE SEARCH (Lexical - Pinecone sparse embeddings)
# ============================================================

def sparse_search(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict]:
    """
    Lexical search using sparse embeddings.
    Uses Pinecone's integrated pinecone-sparse-english-v0 model.
    """
    if not HAS_SPARSE or not _sparse_index:
        return []
    
    try:
        # Query sparse index with integrated embedding
        # Pinecone automatically converts query text to sparse vector
        res = _sparse_index.search(
            namespace="__default__",
            query={
                "top_k": top_k,
                "inputs": {
                    "text": query
                }
            }
        )
        
        results = []
        for hit in res.get("result", {}).get("hits", []):
            chunk_id = hit["_id"]
            fields = hit.get("fields", {})
            
            paper_id = fields.get("paper_id", "")
            if not paper_id and "_chunk_" in chunk_id:
                paper_id = chunk_id.rsplit("_chunk_", 1)[0]
            
            results.append({
                "id": chunk_id,
                "score": float(hit["_score"]),
                "title": fields.get("title", ""),
                "text": fields.get("chunk_text", ""),
                "source": fields.get("source", ""),
                "paper_id": paper_id or chunk_id,
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Sparse search error: {e}")
        return []


# ============================================================
# MERGE AND DEDUPLICATE RESULTS
# ============================================================

def merge_results(dense_results: List[Dict], sparse_results: List[Dict]) -> List[Dict]:
    """
    Merge dense and sparse results, deduplicate by ID.
    Returns list of dicts with _id and chunk_text for reranking.
    """
    merged = {}
    
    # Add dense results
    for r in dense_results:
        rid = r["id"]
        if rid not in merged:
            merged[rid] = {
                "_id": rid,
                "chunk_text": r.get("text", ""),
                "title": r.get("title", ""),
                "source": r.get("source", ""),
                "paper_id": r.get("paper_id", ""),
                "score_dense": r["score"],
                "score_sparse": 0.0,
            }
        else:
            merged[rid]["score_dense"] = r["score"]
    
    # Add sparse results
    for r in sparse_results:
        rid = r["id"]
        if rid not in merged:
            merged[rid] = {
                "_id": rid,
                "chunk_text": r.get("text", ""),
                "title": r.get("title", ""),
                "source": r.get("source", ""),
                "paper_id": r.get("paper_id", ""),
                "score_dense": 0.0,
                "score_sparse": r["score"],
            }
        else:
            merged[rid]["score_sparse"] = r["score"]
    
    # Convert to list
    results = list(merged.values())
    
    # Sort by combined score (RRF-style)
    for r in results:
        r["score_hybrid"] = ALPHA * r["score_dense"] + (1 - ALPHA) * r["score_sparse"]
    
    results.sort(key=lambda x: x["score_hybrid"], reverse=True)
    
    return results


# ============================================================
# RERANKING (Pinecone hosted bge-reranker-v2-m3)
# ============================================================

def rerank_results(query: str, results: List[Dict], top_n: int = TOP_K_FINAL) -> List[Dict]:
    """
    Rerank results using Pinecone's hosted reranker.
    Model: bge-reranker-v2-m3
    """
    if not _pc or not results:
        return results[:top_n]
    
    try:
        # Prepare documents for reranking (max 100 for bge-reranker-v2-m3)
        documents = [
            {"_id": r["_id"], "chunk_text": r.get("chunk_text", "")[:1000]}  # Truncate text
            for r in results[:100]  # Max 100 documents
            if r.get("chunk_text")
        ]
        
        if not documents:
            return results[:top_n]
        
        # Call Pinecone's reranker
        rerank_result = _pc.inference.rerank(
            model="bge-reranker-v2-m3",
            query=query,
            documents=documents,
            rank_fields=["chunk_text"],
            top_n=top_n,
            return_documents=True,
            parameters={"truncate": "END"}
        )
        
        # Map reranked results back to original data
        reranked = []
        id_to_original = {r["_id"]: r for r in results}
        
        for item in rerank_result.data:
            doc = item.get("document", {})
            doc_id = doc.get("_id", "")
            
            if doc_id in id_to_original:
                original = id_to_original[doc_id]
                original["rerank_score"] = item.get("score", 0)
                reranked.append(original)
        
        logger.info(f"Reranked {len(results)} → {len(reranked)} results with bge-reranker-v2-m3")
        return reranked
        
    except Exception as e:
        logger.warning(f"Reranking failed: {e}")
        return results[:top_n]


# ============================================================
# QUERY EXPANSION
# ============================================================

QUERY_SYNONYMS = {
    "vitamin d": ["cholecalciferol", "vitamin d3", "25-hydroxyvitamin d"],
    "vitamin b12": ["cobalamin", "cyanocobalamin", "methylcobalamin"],
    "omega 3": ["omega-3", "epa", "dha", "fish oil", "n-3 fatty acids"],
    "omega 6": ["omega-6", "linoleic acid", "n-6 fatty acids"],
    "gut health": ["microbiome", "gut microbiota", "intestinal flora"],
    "weight loss": ["fat loss", "caloric deficit", "obesity"],
    "muscle gain": ["muscle hypertrophy", "protein synthesis"],
    "intermittent fasting": ["time-restricted eating", "fasting"],
    "keto": ["ketogenic", "ketosis", "low carb"],
    "mediterranean diet": ["mediterranean eating pattern"],
    "diabetes": ["type 2 diabetes", "T2DM", "glycemic control"],
    "heart health": ["cardiovascular", "heart disease", "CVD"],
    "immune": ["immunity", "immune system", "immune function"],
    "inflammation": ["inflammatory", "anti-inflammatory"],
    "probiotics": ["probiotic", "lactobacillus", "bifidobacterium"],
    "fiber": ["dietary fiber", "fibre", "prebiotic"],
    "iron": ["iron deficiency", "ferritin", "anemia"],
    "calcium": ["bone health", "osteoporosis"],
}


def expand_query(query: str, max_expansions: int = 2) -> List[str]:
    """Expand query with synonyms for better recall."""
    lower = query.lower()
    expansions = [query]
    
    for term, synonyms in QUERY_SYNONYMS.items():
        if term in lower:
            for syn in synonyms[:2]:
                expanded = query.replace(term, syn)
                if expanded != query and expanded not in expansions:
                    expansions.append(expanded)
    
    return expansions[:max_expansions + 1]


# ============================================================
# HYBRID SEARCH (Main function)
# ============================================================

def hybrid_search(query: str, top_k: int = TOP_K_FINAL, use_reranking: bool = True, use_expansion: bool = True) -> List[Dict]:
    """
    Performs Hybrid Search following Pinecone's recommended approach.
    Falls back to local TF-IDF search when Pinecone is unavailable.
    
    Pipeline:
    1. Query Expansion (synonyms) → +30% recall
    2. Dense Search (OpenAI → Pinecone) for semantic similarity
    3. Sparse Search (Pinecone sparse) for lexical matching
    4. Merge and deduplicate results
    5. Rerank with Pinecone's bge-reranker-v2-m3 → +40% precision
    6. Filter by relevance and deduplicate by paper
    
    Args:
        query: Search query
        top_k: Number of results to return
        use_reranking: Whether to apply Pinecone reranking
        use_expansion: Whether to expand query with synonyms
        
    Returns:
        List of deduplicated, reranked results with paper metadata
    """
    # ── LOCAL FALLBACK when Pinecone is not available ──
    if not HAS_DENSE:
        logger.info("Pinecone unavailable — using local TF-IDF fallback")
        return local_search(query, top_k=top_k)

    # 1. Query expansion
    queries = expand_query(query) if use_expansion else [query]
    logger.debug(f"Searching with {len(queries)} query variant(s)")
    
    # 2. Collect results from all query variants
    all_dense = []
    all_sparse = []
    
    for q in queries:
        # Dense search (semantic)
        dense_results = dense_search(q, top_k=TOP_K_SEARCH)
        all_dense.extend(dense_results)
        
        # Sparse search (lexical) - only if sparse index available
        if HAS_SPARSE:
            sparse_results = sparse_search(q, top_k=TOP_K_SEARCH)
            all_sparse.extend(sparse_results)
    
    logger.debug(f"Raw results: {len(all_dense)} dense, {len(all_sparse)} sparse")
    
    # 3. Merge and deduplicate
    merged = merge_results(all_dense, all_sparse)
    
    logger.debug(f"Merged: {len(merged)} unique chunks")
    
    # 4. Rerank with Pinecone's hosted model
    if use_reranking and merged:
        reranked = rerank_results(query, merged, top_n=min(len(merged), top_k * 5))
    else:
        reranked = merged[:top_k * 5]
    
    # 5. Deduplicate by paper and add full metadata
    seen_titles = set()
    results = []
    
    # Minimum rerank score threshold to filter low-relevance results
    # bge-reranker-v2-m3 scores typically range from 0 to 1
    MIN_RERANK_SCORE = 0.15  # Filter out very low relevance results
    
    for r in reranked:
        # Skip results with very low rerank score (likely irrelevant)
        rerank_score = r.get("rerank_score", 0)
        if use_reranking and rerank_score is not None and rerank_score < MIN_RERANK_SCORE:
            logger.debug(f"Filtered out low-relevance result (score={rerank_score:.3f}): {r.get('title', '')[:50]}")
            continue
        
        paper_id = r.get("paper_id", "")
        paper = _find_paper(paper_id, r.get("source", ""), r.get("title", ""))
        
        title = paper.get("title", "") or r.get("title", "")
        if not title:
            continue
        
        norm_title = _normalize_title(title)
        if not norm_title or norm_title in seen_titles:
            continue
        
        seen_titles.add(norm_title)
        
        filename = paper.get("filename", "")
        if not filename:
            continue
        
        abstract = paper.get("abstract", "") or r.get("chunk_text", "")
        
        results.append({
            "id": paper.get("id", paper_id or r["_id"]),
            "title": title,
            "abstract": abstract[:800] if abstract else "",
            "year": paper.get("year") or r.get("year"),
            "source": paper.get("source", "") or "PDF",
            "authors": paper.get("authors", []),
            "filename": filename,
            "paper_id": paper.get("id", paper_id),
            "score_dense": r.get("score_dense", 0),
            "score_sparse": r.get("score_sparse", 0),
            "score_hybrid": r.get("score_hybrid", 0),
            "rerank_score": r.get("rerank_score"),
        })
        
        if len(results) >= top_k:
            break
    
    logger.debug(f"Returning {len(results)} unique papers")
    
    return results


# ============================================================
# STATS
# ============================================================

def get_stats() -> Dict:
    """Returns system statistics."""
    return {
        "papers_loaded": len(_PAPERS),
        "chunks_loaded": len(_CHUNKS),
        "dense_index_connected": HAS_DENSE,
        "sparse_index_connected": HAS_SPARSE,
        "hybrid_enabled": HAS_DENSE and HAS_SPARSE,
        "local_fallback_ready": _LOCAL_READY,
        "local_docs_count": len(_LOCAL_DOCS),
        "alpha": ALPHA,
        "reranker": "bge-reranker-v2-m3" if HAS_DENSE else "local-tfidf",
    }


# ============================================================
# BACKWARDS COMPATIBILITY
# ============================================================

# Keep old function names for compatibility
_pc_index = _dense_index
HAS_PINECONE = HAS_DENSE

def get_embeddings_model():
    """Returns the embedding model name."""
    return f"OpenAI ({EMBEDDING_MODEL_NAME})"
