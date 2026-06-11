"""
Ablation study tests.
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
# ABLATION STRUCTURE TESTS (No API needed)
# ============================================================================

@pytest.mark.ablation
class TestAblationStructure:
    """Tests for ablation structure."""
    
    def test_agents_directory_exists(self):
        """Test agents directory exists for ablation studies."""
        agents_dir = Path(__file__).parent.parent.parent / "app" / "agents"
        assert agents_dir.exists()
    
    def test_rag_exists(self):
        """Test RAG exists for ablation studies."""
        rag_file = Path(__file__).parent.parent.parent / "app" / "rag_hybrid.py"
        assert rag_file.exists()


# ============================================================================
# ABLATION TESTS (Require API)
# ============================================================================

@pytest.mark.ablation
@pytest.mark.slow
@pytest.mark.skipif(not has_api_key(), reason="OPENAI_API_KEY required")
class TestAgentContributions:
    """Tests for agent contributions."""
    
    def test_nutrition_agent_contribution(self, nourishgraph):
        """Test nutrition agent contribution."""
        result = safe_invoke(nourishgraph, {
            "user_input": "What are good sources of protein?",
            "messages": []
        })
        assert result is not None
    
    def test_science_agent_contribution(self, nourishgraph):
        """Test science agent contribution."""
        result = safe_invoke(nourishgraph, {
            "user_input": "What research exists on vitamin D and immunity?",
            "messages": []
        })
        assert result is not None
