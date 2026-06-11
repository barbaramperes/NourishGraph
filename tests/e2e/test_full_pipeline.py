"""
End-to-end tests for the full NourishGraph pipeline.
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
# PIPELINE STRUCTURE TESTS (No API needed)
# ============================================================================

@pytest.mark.e2e
class TestPipelineStructure:
    """Tests for pipeline structure."""
    
    def test_app_exists(self):
        """Test app directory exists."""
        app_dir = Path(__file__).parent.parent.parent / "app"
        assert app_dir.exists()
    
    def test_graph_exists(self):
        """Test graph module exists."""
        graph_file = Path(__file__).parent.parent.parent / "app" / "graph" / "graph.py"
        assert graph_file.exists()
    
    def test_agents_exist(self):
        """Test agents module exists."""
        agents_dir = Path(__file__).parent.parent.parent / "app" / "agents"
        assert agents_dir.exists()


# ============================================================================
# FULL PIPELINE TESTS (Require API)
# ============================================================================

@pytest.mark.e2e
@pytest.mark.skipif(not has_api_key(), reason="OPENAI_API_KEY required")
class TestFullPipeline:
    """End-to-end tests for the complete pipeline."""
    
    def test_nutrition_query_pipeline(self, nourishgraph):
        """Test complete nutrition query processing."""
        result = nourishgraph.invoke({
            "user_input": "How many calories are in an apple?",
            "messages": [],
        })
        assert result is not None
    
    def test_science_query_pipeline(self, nourishgraph):
        """Test complete science query processing."""
        result = nourishgraph.invoke({
            "user_input": "What does research say about Mediterranean diet?",
            "messages": [],
        })
        assert result is not None
    
    def test_meal_planning_pipeline(self, nourishgraph):
        """Test complete meal planning query processing."""
        result = nourishgraph.invoke({
            "user_input": "Create a healthy lunch suggestion",
            "messages": [],
        })
        assert result is not None
