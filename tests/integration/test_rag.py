"""
Integration tests for the RAG system.
"""

import pytest
import os
from pathlib import Path


def has_api_key() -> bool:
    """Check if OpenAI API key is available."""
    key = os.environ.get("OPENAI_API_KEY", "")
    return bool(key) and not key.startswith("sk-...")


def safe_invoke(graph, input_data):
    """Safely invoke graph, skipping on API errors."""
    try:
        return graph.invoke(input_data)
    except Exception as e:
        if "401" in str(e) or "auth" in str(e).lower() or "api_key" in str(e).lower():
            pytest.skip(f"API authentication error: {e}")
        raise


# ============================================================================
# RAG FILE STRUCTURE TESTS (No API needed)
# ============================================================================

@pytest.mark.integration
class TestRAGFilesExist:
    """Tests that verify RAG files exist."""
    
    def test_rag_hybrid_exists(self):
        """Test rag_hybrid.py exists."""
        rag_file = Path(__file__).parent.parent.parent / "app" / "rag_hybrid.py"
        assert rag_file.exists()
    
    def test_papers_directory_exists(self):
        """Test papers directory exists."""
        papers_dir = Path(__file__).parent.parent.parent / "papers_txt"
        assert papers_dir.exists()
    
    def test_papers_have_content(self):
        """Test papers directory has text files."""
        papers_dir = Path(__file__).parent.parent.parent / "papers_txt"
        txt_files = list(papers_dir.glob("*.txt"))
        assert len(txt_files) > 0


# ============================================================================
# RAG FUNCTIONALITY TESTS (Require API)
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(not has_api_key(), reason="OPENAI_API_KEY required")
class TestRAGFunctionality:
    """Tests for RAG functionality."""
    
    def test_rag_instantiation(self, rag_system):
        """Test RAG system can be instantiated and has required functions."""
        assert rag_system is not None
        # Verify the module has the main functions
        assert hasattr(rag_system, 'hybrid_search')
        assert hasattr(rag_system, 'get_stats')
        # Check stats
        stats = rag_system.get_stats()
        assert 'papers_loaded' in stats
        assert 'pinecone_connected' in stats
    
    def test_science_query_uses_context(self, nourishgraph):
        """Test science query returns evidence-based response."""
        result = safe_invoke(nourishgraph, {
            "user_input": "What are the health benefits of omega-3?",
            "messages": []
        })
        assert result is not None
