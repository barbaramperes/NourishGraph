"""
app/tools/search_tools.py

Scientific search tools for the Science Agent.
Uses Hybrid Search (Dense + BM25) over nutrition papers.

Protocols:
- RAG (Retrieval-Augmented Generation)
- Hybrid Search (Dense + Sparse)
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# ============================================================
# GLOBAL STATE - Last search results
# ============================================================

_LAST_SEARCH_RESULTS: List[Dict] = []


def get_last_search_results() -> List[Dict]:
    """Get the last search results from hybrid search."""
    return _LAST_SEARCH_RESULTS


def clear_last_search_results():
    """Clear the last search results."""
    global _LAST_SEARCH_RESULTS
    _LAST_SEARCH_RESULTS = []


# ============================================================
# SCHEMAS
# ============================================================

class SearchResult(BaseModel):
    """Result from a paper search."""
    id: str
    title: str
    authors: List[str] = []
    year: Optional[int] = None
    abstract: str = ""
    url: str = ""
    source: str = ""
    score: float = 0.0


# ============================================================
# TOOLS
# ============================================================

@tool
def search_scientific_papers(
    query: str,
    max_results: int = 5
) -> str:
    """
    Searches for scientific papers on nutrition using Hybrid Search.
    
    Uses a combination of:
    - Dense embeddings (semantic) - understands context and synonyms
    - BM25 (lexical) - finds exact terms
    
    Args:
        query: Search terms (e.g., "vitamin D immune system")
        max_results: Maximum number of results (default: 5). ALWAYS use 5.
    
    Returns:
        Formatted string with found papers
    
    Example:
        search_scientific_papers("intermittent fasting weight loss")
    """
    try:
        # Import here to avoid circular imports
        from app.rag_hybrid import hybrid_search
        
        results = hybrid_search(query, top_k=max_results)
        
        if not results:
            return f"No papers found about '{query}'. Try rephrasing your search in English."
        
        # Store results globally for later retrieval
        global _LAST_SEARCH_RESULTS
        _LAST_SEARCH_RESULTS = results
        
        # Format results with full details
        output = f"Found {len(results)} scientific paper(s) about '{query}':\n\n"
        
        for i, paper in enumerate(results, 1):
            title = paper.get("title", "No title")
            year = paper.get("year", "n.d.")
            authors = paper.get("authors", [])
            abstract = paper.get("abstract", "") or paper.get("text", "")
            source = paper.get("source", "")
            
            # Format authors
            if isinstance(authors, list) and authors:
                authors_str = ", ".join(authors[:3])
                if len(authors) > 3:
                    authors_str += " et al."
            elif isinstance(authors, str):
                authors_str = authors
            else:
                authors_str = "Unknown authors"
            
            # Truncate abstract - keep 800 chars for more context
            if len(abstract) > 800:
                abstract = abstract[:800] + "..."
            
            output += f"PAPER {i}:\n"
            output += f"Title: {title}\n"
            output += f"Authors: {authors_str}\n"
            output += f"Year: {year}\n"
            if source:
                output += f"Journal: {source}\n"
            output += f"Key Findings: {abstract}\n\n"
        
        return output
    
    except Exception as e:
        import traceback
        return f"Search error: {str(e)}\n{traceback.format_exc()}"


@tool
def get_paper_details(paper_id: str) -> str:
    """
    Gets complete details of a specific paper.
    
    Args:
        paper_id: Paper ID (obtained from search_scientific_papers)
    
    Returns:
        Complete paper details
    """
    try:
        from app.rag_hybrid import _ID_TO_PAPER
        
        paper = _ID_TO_PAPER.get(paper_id)
        
        if not paper:
            return f"Paper with ID '{paper_id}' not found."
        
        title = paper.get("title", "No title")
        authors = paper.get("authors", [])
        year = paper.get("year", "n.d.")
        abstract = paper.get("abstract", "") or paper.get("text", "")
        url = paper.get("url", "")
        source = paper.get("source", "")
        
        output = f"**{title}**\n\n"
        output += f"**Authors:** {', '.join(authors) if authors else 'N/A'}\n"
        output += f"**Year:** {year}\n"
        output += f"**Source:** {source}\n"
        output += f"**Link:** {url}\n\n"
        output += f"**Full Abstract:**\n{abstract}\n"
        
        return output
    
    except Exception as e:
        return f"Error getting details: {str(e)}"


# ============================================================
# TOOLS LIST FOR EXPORT
# ============================================================

SEARCH_TOOLS = [
    search_scientific_papers,
]
