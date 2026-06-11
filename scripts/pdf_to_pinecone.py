#!/usr/bin/env python3
"""
scripts/pdf_to_pinecone.py

Complete PDF processing pipeline for Pinecone Hybrid Search:
1. Extract text from PDFs → save as .txt
2. Generate summaries using OpenAI
3. Extract metadata (title, authors, date, keywords)
4. Chunk documents with overlap
5. Generate embeddings (OpenAI text-embedding-3-small)
6. Index to Pinecone with dense vectors + sparse (BM25) values

Supports:
- Hybrid search (semantic + lexical)
- Multi-index architecture
- Metadata filtering
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import hashlib
import re
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import tiktoken

# PDF extraction
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    print("⚠️ PyMuPDF not installed. Run: pip install pymupdf")

try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    HAS_PDFMINER = True
except ImportError:
    HAS_PDFMINER = False

# OpenAI
from openai import OpenAI
from dotenv import load_dotenv

# Pinecone
from pinecone import Pinecone, ServerlessSpec

# BM25 for sparse vectors
from rank_bm25 import BM25Okapi
import numpy as np

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "nutriai-papers")

# Use OpenAI embeddings or SentenceTransformers (local)
USE_OPENAI_EMBEDDINGS = os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true"

# Directories
BASE_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = BASE_DIR / "papers" / "pdf"
TXT_DIR = BASE_DIR / "papers" / "txt"
DATA_DIR = BASE_DIR / "app" / "data"
CHUNKS_FILE = DATA_DIR / "paper_chunks.pkl"
METADATA_FILE = DATA_DIR / "paper_metadata.json"

# Chunking settings
CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 50  # tokens

# Embedding configuration
if USE_OPENAI_EMBEDDINGS:
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIM = 1536
else:
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # SentenceTransformers
    EMBEDDING_DIM = 384

# BM25 vocabulary size for sparse vectors
SPARSE_VECTOR_DIM = 30000


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class PaperMetadata:
    """Metadata extracted from a paper."""
    id: str
    filename: str
    title: str
    authors: List[str]
    abstract: str
    keywords: List[str]
    year: Optional[int]
    source: str
    num_pages: int
    word_count: int
    processed_at: str
    summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentChunk:
    """A chunk of text from a document."""
    chunk_id: str
    paper_id: str
    text: str
    chunk_index: int
    total_chunks: int
    token_count: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_text_pymupdf(pdf_path: Path) -> Tuple[str, int]:
    """Extract text from PDF using PyMuPDF (fastest, best quality)."""
    if not HAS_PYMUPDF:
        raise ImportError("PyMuPDF not installed")
    
    doc = fitz.open(pdf_path)
    text_parts = []
    
    for page in doc:
        text_parts.append(page.get_text())
    
    num_pages = len(doc)
    doc.close()
    
    return "\n\n".join(text_parts), num_pages


def extract_text_pdfminer(pdf_path: Path) -> Tuple[str, int]:
    """Extract text using pdfminer (fallback)."""
    if not HAS_PDFMINER:
        raise ImportError("pdfminer not installed")
    
    text = pdfminer_extract(str(pdf_path))
    # Estimate pages (rough)
    num_pages = max(1, text.count('\f') + 1)
    return text, num_pages


def extract_text_from_pdf(pdf_path: Path) -> Tuple[str, int]:
    """Extract text from PDF using best available method."""
    if HAS_PYMUPDF:
        return extract_text_pymupdf(pdf_path)
    elif HAS_PDFMINER:
        return extract_text_pdfminer(pdf_path)
    else:
        raise ImportError("No PDF library available. Install pymupdf or pdfminer.six")


def clean_text(text: str) -> str:
    """Clean extracted text."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove page numbers and headers
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    return text.strip()


def pdf_to_txt(pdf_path: Path, output_dir: Path) -> Path:
    """Convert PDF to TXT file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    txt_filename = pdf_path.stem + ".txt"
    txt_path = output_dir / txt_filename
    
    text, num_pages = extract_text_from_pdf(pdf_path)
    text = clean_text(text)
    
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    
    print(f"   📄 Saved: {txt_filename} ({num_pages} pages, {len(text.split())} words)")
    return txt_path


# ============================================================
# METADATA EXTRACTION (OpenAI)
# ============================================================

def get_openai_client() -> OpenAI:
    """Get OpenAI client."""
    return OpenAI(api_key=OPENAI_API_KEY)


def extract_metadata_with_llm(text: str, filename: str, client: OpenAI) -> Dict[str, Any]:
    """Extract metadata from paper text using GPT."""
    # Take first ~3000 words for metadata extraction
    text_sample = " ".join(text.split()[:3000])
    
    prompt = f"""Analyze this scientific paper excerpt and extract metadata.

TEXT:
{text_sample}

Extract and return a JSON object with:
{{
    "title": "Full paper title",
    "authors": ["Author 1", "Author 2", ...],
    "abstract": "Paper abstract (if visible, else summarize intro)",
    "keywords": ["keyword1", "keyword2", ...],
    "year": 2023,  // publication year if found, else null
    "source": "Journal or conference name if found"
}}

Return ONLY valid JSON, no markdown."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"   ⚠️ Metadata extraction failed: {e}")
        return {
            "title": filename.replace("_", " ").replace(".pdf", ""),
            "authors": [],
            "abstract": "",
            "keywords": [],
            "year": None,
            "source": "Unknown"
        }


def generate_summary(text: str, client: OpenAI, max_words: int = 300) -> str:
    """Generate a summary of the paper."""
    # Take first ~5000 words
    text_sample = " ".join(text.split()[:5000])
    
    prompt = f"""Summarize this scientific paper in {max_words} words or less.
Focus on:
1. Main objective/research question
2. Methods used
3. Key findings
4. Conclusions and implications

TEXT:
{text_sample}

Provide a clear, concise summary:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"   ⚠️ Summary generation failed: {e}")
        return ""


# ============================================================
# TEXT CHUNKING
# ============================================================

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens in text."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def chunk_text_into_parts(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> List[str]:
    """
    Split text into overlapping chunks.
    Uses sentence boundaries for cleaner splits.
    """
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)
        
        if current_tokens + sentence_tokens > chunk_size and current_chunk:
            # Save current chunk
            chunk_str = " ".join(current_chunk)
            chunks.append(chunk_str)
            
            # Start new chunk with overlap
            overlap_tokens = 0
            overlap_sentences = []
            for s in reversed(current_chunk):
                s_tokens = count_tokens(s)
                if overlap_tokens + s_tokens <= chunk_overlap:
                    overlap_sentences.insert(0, s)
                    overlap_tokens += s_tokens
                else:
                    break
            
            current_chunk = overlap_sentences
            current_tokens = overlap_tokens
        
        current_chunk.append(sentence)
        current_tokens += sentence_tokens
    
    # Add last chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks


# Alias for backward compatibility
chunk_text = chunk_text_into_parts


def create_chunks_for_paper(
    paper_id: str,
    text: str,
    metadata: Dict[str, Any]
) -> List[DocumentChunk]:
    """Create document chunks for a paper."""
    raw_chunks = chunk_text_into_parts(text)
    
    chunks = []
    for i, chunk_content in enumerate(raw_chunks):
        chunk_id = f"{paper_id}_chunk_{i:04d}"
        
        chunk = DocumentChunk(
            chunk_id=chunk_id,
            paper_id=paper_id,
            text=chunk_content,
            chunk_index=i,
            total_chunks=len(raw_chunks),
            token_count=count_tokens(chunk_content),
            metadata={
                "title": metadata.get("title", ""),
                "authors": metadata.get("authors", []),
                "year": metadata.get("year"),
                "keywords": metadata.get("keywords", []),
                "source": metadata.get("source", ""),
            }
        )
        chunks.append(chunk)
    
    return chunks


# ============================================================
# EMBEDDINGS (OpenAI or SentenceTransformers)
# ============================================================

# Load SentenceTransformer model if not using OpenAI
_SENTENCE_TRANSFORMER = None
if not USE_OPENAI_EMBEDDINGS:
    try:
        from sentence_transformers import SentenceTransformer
        _SENTENCE_TRANSFORMER = SentenceTransformer(EMBEDDING_MODEL)
        print(f"✅ Loaded SentenceTransformer model: {EMBEDDING_MODEL}")
    except Exception as e:
        print(f"⚠️ Could not load SentenceTransformer: {e}")


def generate_embeddings_batch(
    texts: List[str],
    client: OpenAI = None,
    model: str = EMBEDDING_MODEL,
    batch_size: int = 100
) -> List[List[float]]:
    """Generate embeddings for a batch of texts using OpenAI or SentenceTransformers."""
    
    if USE_OPENAI_EMBEDDINGS and client:
        # Use OpenAI embeddings
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = client.embeddings.create(
                    model=model,
                    input=batch
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
                print(f"   📊 Embedded {len(all_embeddings)}/{len(texts)} chunks (OpenAI)")
                
            except Exception as e:
                print(f"   ⚠️ Embedding error: {e}")
                all_embeddings.extend([[0.0] * EMBEDDING_DIM] * len(batch))
        
        return all_embeddings
    
    elif _SENTENCE_TRANSFORMER:
        # Use SentenceTransformers (local, free)
        print(f"   📊 Generating embeddings with SentenceTransformers...")
        embeddings = _SENTENCE_TRANSFORMER.encode(texts, show_progress_bar=True)
        print(f"   📊 Embedded {len(texts)}/{len(texts)} chunks (SentenceTransformers)")
        return embeddings.tolist()
    
    else:
        raise RuntimeError("No embedding model available. Set USE_OPENAI_EMBEDDINGS=true or install sentence-transformers.")


# ============================================================
# SPARSE VECTORS (BM25)
# ============================================================

class SparseVectorizer:
    """Generate sparse vectors using BM25-style tokenization."""
    
    def __init__(self, vocab_size: int = SPARSE_VECTOR_DIM):
        self.vocab_size = vocab_size
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.bm25 = None
        self.corpus_tokens: List[List[str]] = []
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        text = text.lower()
        tokens = re.findall(r'\b[a-z0-9]+\b', text)
        # Remove stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
                     'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be',
                     'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                     'will', 'would', 'could', 'should', 'may', 'might', 'must',
                     'this', 'that', 'these', 'those', 'it', 'its', 'as', 'from'}
        return [t for t in tokens if t not in stopwords and len(t) > 2]
    
    def _hash_token(self, token: str) -> int:
        """Hash token to vocabulary index."""
        return int(hashlib.md5(token.encode()).hexdigest(), 16) % self.vocab_size
    
    def fit(self, documents: List[str]) -> 'SparseVectorizer':
        """Fit BM25 on corpus."""
        self.corpus_tokens = [self._tokenize(doc) for doc in documents]
        self.bm25 = BM25Okapi(self.corpus_tokens)
        
        # Build vocabulary from corpus
        all_tokens = set()
        for tokens in self.corpus_tokens:
            all_tokens.update(tokens)
        
        for token in all_tokens:
            idx = self._hash_token(token)
            self.vocab[token] = idx
        
        print(f"   📊 BM25 fitted on {len(documents)} documents, vocab size: {len(self.vocab)}")
        return self
    
    def get_sparse_vector(self, text: str) -> Dict[str, Any]:
        """
        Get sparse vector for text.
        Returns Pinecone-compatible sparse vector format.
        """
        tokens = self._tokenize(text)
        
        if not tokens:
            return {"indices": [], "values": []}
        
        # Count token frequencies
        token_counts: Dict[int, float] = {}
        for token in tokens:
            idx = self._hash_token(token)
            token_counts[idx] = token_counts.get(idx, 0) + 1
        
        # Normalize by document length
        doc_len = len(tokens)
        for idx in token_counts:
            token_counts[idx] = token_counts[idx] / doc_len
        
        indices = list(token_counts.keys())
        values = list(token_counts.values())
        
        return {"indices": indices, "values": values}
    
    def save(self, path: Path):
        """Save vectorizer to disk."""
        with open(path, "wb") as f:
            pickle.dump({
                "vocab": self.vocab,
                "vocab_size": self.vocab_size,
                "corpus_tokens": self.corpus_tokens
            }, f)
    
    @classmethod
    def load(cls, path: Path) -> 'SparseVectorizer':
        """Load vectorizer from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        
        vectorizer = cls(vocab_size=data["vocab_size"])
        vectorizer.vocab = data["vocab"]
        vectorizer.corpus_tokens = data["corpus_tokens"]
        vectorizer.bm25 = BM25Okapi(vectorizer.corpus_tokens)
        return vectorizer


# ============================================================
# PINECONE INDEXING
# ============================================================

def get_pinecone_client() -> Pinecone:
    """Get Pinecone client."""
    return Pinecone(api_key=PINECONE_API_KEY)


def create_or_get_index(
    pc: Pinecone,
    index_name: str = PINECONE_INDEX_NAME,
    dimension: int = EMBEDDING_DIM,
    metric: str = "dotproduct"  # Required for hybrid search
) -> Any:
    """Create Pinecone index if it doesn't exist."""
    
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    
    if index_name not in existing_indexes:
        print(f"🔧 Creating Pinecone index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        print(f"✅ Index created!")
    else:
        print(f"✅ Using existing index: {index_name}")
    
    return pc.Index(index_name)


def upsert_to_pinecone(
    index: Any,
    chunks: List[DocumentChunk],
    embeddings: List[List[float]],
    sparse_vectorizer: SparseVectorizer = None,
    batch_size: int = 100,
    namespace: str = ""
) -> int:
    """
    Upsert chunks to Pinecone with dense vectors.
    Sparse vectors are optional (requires Pinecone index with dotproduct metric).
    """
    vectors = []
    use_sparse = sparse_vectorizer is not None
    
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        # Clean metadata - Pinecone doesn't accept null values
        year = chunk.metadata.get("year")
        
        vector_data = {
            "id": chunk.chunk_id,
            "values": embedding,
            "metadata": {
                "paper_id": chunk.paper_id,
                "text": chunk.text[:1000] if chunk.text else "",
                "title": (chunk.metadata.get("title") or "")[:200],
                "authors": ", ".join(chunk.metadata.get("authors", [])[:3]) or "Unknown",
                "year": year if year is not None else 0,
                "keywords": ", ".join(chunk.metadata.get("keywords", [])[:5]) or "",
                "source": chunk.metadata.get("source") or "PDF",
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
            }
        }
        
        vectors.append(vector_data)
        
        # Upsert in batches
        if len(vectors) >= batch_size:
            index.upsert(vectors=vectors, namespace=namespace)
            print(f"   📤 Upserted {i + 1}/{len(chunks)} vectors")
            vectors = []
    
    # Upsert remaining
    if vectors:
        index.upsert(vectors=vectors, namespace=namespace)
    
    return len(chunks)


# ============================================================
# HYBRID SEARCH
# ============================================================

def hybrid_search(
    query: str,
    index: Any,
    openai_client: OpenAI,
    sparse_vectorizer: SparseVectorizer,
    top_k: int = 10,
    alpha: float = 0.7,  # Weight for dense (semantic)
    namespace: str = "papers",
    filter_dict: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search (dense + sparse).
    
    Args:
        query: Search query
        index: Pinecone index
        openai_client: OpenAI client for embeddings
        sparse_vectorizer: For sparse vectors
        top_k: Number of results
        alpha: Weight for dense search (0-1)
        namespace: Pinecone namespace
        filter_dict: Metadata filters
    
    Returns:
        List of search results with scores
    """
    # Generate query embedding
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    )
    query_embedding = response.data[0].embedding
    
    # Generate sparse query vector
    sparse_query = sparse_vectorizer.get_sparse_vector(query)
    
    # Hybrid query to Pinecone
    results = index.query(
        vector=query_embedding,
        sparse_vector=sparse_query,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace,
        filter=filter_dict
    )
    
    # Process results
    output = []
    for match in results.matches:
        output.append({
            "id": match.id,
            "score": match.score,
            "text": match.metadata.get("text", ""),
            "title": match.metadata.get("title", ""),
            "authors": match.metadata.get("authors", ""),
            "year": match.metadata.get("year"),
            "paper_id": match.metadata.get("paper_id", ""),
        })
    
    return output


# ============================================================
# MAIN PIPELINE
# ============================================================

def process_pdfs(
    pdf_dir: Path = PDF_DIR,
    txt_dir: Path = TXT_DIR,
    generate_summaries: bool = True
) -> Tuple[List[PaperMetadata], List[DocumentChunk]]:
    """
    Process all PDFs in directory.
    
    Steps:
    1. Extract text from PDFs → save as .txt
    2. Extract metadata using LLM
    3. Generate summaries
    4. Create chunks
    """
    pdf_dir.mkdir(parents=True, exist_ok=True)
    txt_dir.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"⚠️ No PDF files found in {pdf_dir}")
        print(f"   Please add PDF files to: {pdf_dir}")
        return [], []
    
    print(f"📚 Found {len(pdf_files)} PDF files")
    
    client = get_openai_client()
    all_metadata: List[PaperMetadata] = []
    all_chunks: List[DocumentChunk] = []
    
    for i, pdf_path in enumerate(pdf_files):
        print(f"\n[{i+1}/{len(pdf_files)}] Processing: {pdf_path.name}")
        
        # 1. Extract text
        try:
            txt_path = pdf_to_txt(pdf_path, txt_dir)
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"   ❌ Failed to extract text: {e}")
            continue
        
        # 2. Generate paper ID
        paper_id = hashlib.md5(pdf_path.name.encode()).hexdigest()[:12]
        
        # 3. Extract metadata
        print("   🔍 Extracting metadata...")
        meta_dict = extract_metadata_with_llm(text, pdf_path.name, client)
        
        # 4. Generate summary
        summary = ""
        if generate_summaries:
            print("   📝 Generating summary...")
            summary = generate_summary(text, client)
        
        # 5. Create metadata object
        metadata = PaperMetadata(
            id=paper_id,
            filename=pdf_path.name,
            title=meta_dict.get("title", pdf_path.stem),
            authors=meta_dict.get("authors", []),
            abstract=meta_dict.get("abstract", ""),
            keywords=meta_dict.get("keywords", []),
            year=meta_dict.get("year"),
            source=meta_dict.get("source", ""),
            num_pages=0,  # Would need to extract separately
            word_count=len(text.split()),
            processed_at=datetime.now().isoformat(),
            summary=summary
        )
        all_metadata.append(metadata)
        
        # 6. Create chunks
        print("   ✂️ Creating chunks...")
        chunks = create_chunks_for_paper(paper_id, text, meta_dict)
        all_chunks.extend(chunks)
        print(f"   ✅ Created {len(chunks)} chunks")
    
    # Save metadata
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump([m.to_dict() for m in all_metadata], f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved metadata to {METADATA_FILE}")
    
    # Save chunks
    with open(CHUNKS_FILE, "wb") as f:
        pickle.dump([c.to_dict() for c in all_chunks], f)
    print(f"💾 Saved {len(all_chunks)} chunks to {CHUNKS_FILE}")
    
    return all_metadata, all_chunks


def index_to_pinecone(
    chunks: List[DocumentChunk] = None,
    rebuild_sparse: bool = True
) -> Dict[str, Any]:
    """
    Index all chunks to Pinecone.
    
    Steps:
    1. Generate embeddings (OpenAI)
    2. Build/load sparse vectorizer
    3. Upsert to Pinecone with hybrid vectors
    """
    # Load chunks if not provided
    if chunks is None:
        if not CHUNKS_FILE.exists():
            print("❌ No chunks file found. Run process_pdfs() first.")
            return {}
        
        with open(CHUNKS_FILE, "rb") as f:
            chunk_dicts = pickle.load(f)
        chunks = [DocumentChunk(**c) for c in chunk_dicts]
    
    if not chunks:
        print("❌ No chunks to index")
        return {}
    
    print(f"\n🔧 Indexing {len(chunks)} chunks to Pinecone")
    
    # 1. Get clients
    openai_client = get_openai_client()
    pc = get_pinecone_client()
    
    # 2. Create/get index
    index = create_or_get_index(pc)
    
    # 3. Generate embeddings
    print("\n📊 Generating embeddings...")
    texts = [c.text for c in chunks]
    embeddings = generate_embeddings_batch(texts, openai_client)
    
    # 4. Build sparse vectorizer
    sparse_vectorizer_path = DATA_DIR / "sparse_vectorizer.pkl"
    
    if rebuild_sparse or not sparse_vectorizer_path.exists():
        print("\n📊 Building sparse vectorizer (BM25)...")
        sparse_vectorizer = SparseVectorizer()
        sparse_vectorizer.fit(texts)
        sparse_vectorizer.save(sparse_vectorizer_path)
    else:
        print("\n📊 Loading existing sparse vectorizer...")
        sparse_vectorizer = SparseVectorizer.load(sparse_vectorizer_path)
    
    # 5. Upsert to Pinecone
    print("\n📤 Uploading to Pinecone...")
    num_indexed = upsert_to_pinecone(
        index=index,
        chunks=chunks,
        embeddings=embeddings,
        sparse_vectorizer=sparse_vectorizer
    )
    
    # 6. Get stats
    stats = index.describe_index_stats()
    
    result = {
        "chunks_indexed": num_indexed,
        "total_vectors": stats.total_vector_count,
        "namespaces": dict(stats.namespaces) if stats.namespaces else {},
        "dimension": stats.dimension
    }
    
    print(f"\n✅ Indexing complete!")
    print(f"   📊 Total vectors: {stats.total_vector_count}")
    
    return result


def test_hybrid_search(
    queries: List[str] = None,
    top_k: int = 5
) -> None:
    """Test search functionality using SentenceTransformers."""
    if queries is None:
        queries = [
            "vitamin D immune system",
            "protein muscle synthesis",
            "intermittent fasting weight loss",
            "omega-3 brain health",
            "gut microbiome probiotics"
        ]
    
    # Load components
    pc = get_pinecone_client()
    index = pc.Index(PINECONE_INDEX_NAME)
    
    # Use SentenceTransformers for query embedding (same as indexing)
    if _SENTENCE_TRANSFORMER is None:
        print("❌ SentenceTransformer not loaded.")
        return
    
    print("="*60)
    print("SEARCH TEST (SentenceTransformers)")
    print("="*60)
    
    for query in queries:
        print(f"\n🔍 Query: '{query}'")
        print("-"*40)
        
        # Generate query embedding with SentenceTransformers
        query_embedding = _SENTENCE_TRANSFORMER.encode(query).tolist()
        
        # Query Pinecone
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        
        for i, match in enumerate(results.matches):
            print(f"  [{i+1}] Score: {match.score:.3f}")
            title = match.metadata.get('title', 'N/A')[:60]
            print(f"      Title: {title}...")
            print(f"      Year: {match.metadata.get('year', 'N/A')}")
            print()


# ============================================================
# CLI
# ============================================================

def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="PDF to Pinecone Hybrid Search Pipeline"
    )
    parser.add_argument(
        "command",
        choices=["process", "index", "search", "all"],
        help="Command to run"
    )
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default=str(PDF_DIR),
        help="Directory with PDF files"
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip summary generation"
    )
    parser.add_argument(
        "--rebuild-sparse",
        action="store_true",
        help="Rebuild sparse vectorizer"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Search query"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results"
    )
    
    args = parser.parse_args()
    
    if args.command == "process":
        print("📄 STEP 1: Processing PDFs...")
        process_pdfs(
            pdf_dir=Path(args.pdf_dir),
            generate_summaries=not args.no_summary
        )
    
    elif args.command == "index":
        print("📤 STEP 2: Indexing to Pinecone...")
        index_to_pinecone(rebuild_sparse=args.rebuild_sparse)
    
    elif args.command == "search":
        if args.query:
            test_hybrid_search(queries=[args.query], top_k=args.top_k)
        else:
            test_hybrid_search(top_k=args.top_k)
    
    elif args.command == "all":
        print("🚀 FULL PIPELINE")
        print("="*60)
        
        print("\n📄 STEP 1: Processing PDFs...")
        metadata, chunks = process_pdfs(
            pdf_dir=Path(args.pdf_dir),
            generate_summaries=not args.no_summary
        )
        
        if chunks:
            print("\n📤 STEP 2: Indexing to Pinecone...")
            index_to_pinecone(chunks=chunks, rebuild_sparse=True)
            
            print("\n🔍 STEP 3: Testing search...")
            test_hybrid_search(top_k=args.top_k)
        
        print("\n✅ Pipeline complete!")


if __name__ == "__main__":
    main()
