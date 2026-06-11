"""
Baseline comparison tests.
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
# BASELINE STRUCTURE TESTS (No API needed)
# ============================================================================

@pytest.mark.baseline
class TestBaselineStructure:
    """Tests for baseline structure."""
    
    def test_graph_exists(self):
        """Test graph exists for baseline comparison."""
        graph_file = Path(__file__).parent.parent.parent / "app" / "graph" / "graph.py"
        assert graph_file.exists()


# ============================================================================
# BASELINE TESTS (Require API)
# ============================================================================

@pytest.mark.baseline
@pytest.mark.slow
@pytest.mark.skipif(not has_api_key(), reason="OPENAI_API_KEY required")
class TestNourishGraphBaseline:
    """Tests for NourishGraph baseline."""
    
    def test_nourishgraph_response_quality(self, nourishgraph):
        """Test NourishGraph response quality."""
        result = safe_invoke(nourishgraph, {
            "user_input": "What are the benefits of a Mediterranean diet?",
            "messages": []
        })
        assert result is not None
    
    def test_nourishgraph_handles_variety(self, nourishgraph):
        """Test NourishGraph handles variety of queries."""
        queries = [
            "What vitamins are in spinach?",
            "How does fiber help digestion?",
            "Plan a healthy breakfast"
        ]
        for query in queries:
            result = safe_invoke(nourishgraph, {
                "user_input": query,
                "messages": []
            })
            assert result is not None
