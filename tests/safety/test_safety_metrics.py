"""
Safety metrics tests.
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
# SAFETY MODULE STRUCTURE TESTS (No API needed)
# ============================================================================

@pytest.mark.safety
class TestSafetyModuleStructure:
    """Tests for safety module structure."""
    
    def test_safety_directory_exists(self):
        """Test safety directory exists."""
        safety_dir = Path(__file__).parent.parent.parent / "app" / "safety"
        assert safety_dir.exists()
    
    def test_safety_has_init(self):
        """Test safety has __init__.py."""
        init_file = Path(__file__).parent.parent.parent / "app" / "safety" / "__init__.py"
        assert init_file.exists()


@pytest.mark.safety
class TestMetricsFiles:
    """Tests for metrics files."""
    
    def test_evaluation_directory_exists(self):
        """Test evaluation directory exists."""
        eval_dir = Path(__file__).parent.parent.parent / "app" / "evaluation"
        assert eval_dir.exists()
    
    def test_evaluation_has_files(self):
        """Test evaluation has Python files."""
        eval_dir = Path(__file__).parent.parent.parent / "app" / "evaluation"
        py_files = list(eval_dir.glob("*.py"))
        assert len(py_files) > 0


# ============================================================================
# SAFETY FUNCTIONALITY TESTS (Require API)
# ============================================================================

@pytest.mark.safety
@pytest.mark.skipif(not has_api_key(), reason="OPENAI_API_KEY required")
class TestSafetyFunctionality:
    """Tests for safety functionality."""
    
    def test_safe_query_processed(self, nourishgraph):
        """Test safe query is processed normally."""
        result = safe_invoke(nourishgraph, {
            "user_input": "What vitamins are good for immune health?",
            "messages": []
        })
        assert result is not None
    
    def test_system_responds_to_queries(self, nourishgraph):
        """Test system responds to various queries."""
        result = safe_invoke(nourishgraph, {
            "user_input": "Tell me about protein sources",
            "messages": []
        })
        assert result is not None
