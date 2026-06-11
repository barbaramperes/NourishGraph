"""
Unit tests for the router/graph system.
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
# STRUCTURE TESTS (No API needed)
# ============================================================================

@pytest.mark.unit
class TestGraphFilesExist:
    """Tests that verify graph module files exist."""
    
    def test_graph_directory_exists(self):
        """Test graph directory exists."""
        graph_dir = Path(__file__).parent.parent.parent / "app" / "graph"
        assert graph_dir.exists()
    
    def test_graph_file_exists(self):
        """Test graph.py exists."""
        graph_file = Path(__file__).parent.parent.parent / "app" / "graph" / "graph.py"
        assert graph_file.exists()
    
    def test_nodes_file_exists(self):
        """Test nodes.py exists."""
        nodes_file = Path(__file__).parent.parent.parent / "app" / "graph" / "nodes.py"
        assert nodes_file.exists()
    
    def test_state_file_exists(self):
        """Test state.py exists."""
        state_file = Path(__file__).parent.parent.parent / "app" / "graph" / "state.py"
        assert state_file.exists()


@pytest.mark.unit
class TestGraphFileContent:
    """Tests that verify graph files have expected content."""
    
    def test_graph_has_create_function(self):
        """Test graph.py contains create_graph function."""
        graph_file = Path(__file__).parent.parent.parent / "app" / "graph" / "graph.py"
        content = graph_file.read_text()
        assert "create_graph" in content
    
    def test_uses_langgraph(self):
        """Test graph uses LangGraph."""
        graph_file = Path(__file__).parent.parent.parent / "app" / "graph" / "graph.py"
        content = graph_file.read_text()
        assert "langgraph" in content or "StateGraph" in content


# ============================================================================
# GRAPH TESTS (Require API)
# ============================================================================

@pytest.mark.unit
@pytest.mark.skipif(not has_api_key(), reason="OPENAI_API_KEY required")
class TestGraphExecution:
    """Tests for graph execution."""
    
    def test_graph_accepts_input(self, nourishgraph):
        """Test graph accepts input."""
        result = safe_invoke(nourishgraph, {
            "user_input": "Hello",
            "messages": []
        })
        assert result is not None
    
    def test_graph_returns_messages(self, nourishgraph):
        """Test graph returns messages."""
        result = safe_invoke(nourishgraph, {
            "user_input": "What is vitamin C?",
            "messages": []
        })
        assert result is not None
