"""
Unit tests for utility modules.
"""

import pytest
import os
import json
from pathlib import Path


def has_api_key() -> bool:
    """Check if OpenAI API key is available."""
    key = os.environ.get("OPENAI_API_KEY", "")
    return bool(key) and not key.startswith("sk-...")


# ============================================================================
# STRUCTURE TESTS (No API needed)
# ============================================================================

@pytest.mark.unit
class TestToolFilesExist:
    """Tests that verify tool files exist."""
    
    def test_tools_directory_exists(self):
        """Test tools directory exists."""
        tools_dir = Path(__file__).parent.parent.parent / "app" / "tools"
        assert tools_dir.exists()
    
    def test_tools_init_exists(self):
        """Test tools __init__.py exists."""
        init_file = Path(__file__).parent.parent.parent / "app" / "tools" / "__init__.py"
        assert init_file.exists()


@pytest.mark.unit
class TestMemoryFilesExist:
    """Tests that verify memory module files exist."""
    
    def test_memory_directory_exists(self):
        """Test memory directory exists."""
        memory_dir = Path(__file__).parent.parent.parent / "app" / "memory"
        assert memory_dir.exists()


@pytest.mark.unit
class TestRAGFilesExist:
    """Tests that verify RAG files exist."""
    
    def test_hybrid_rag_exists(self):
        """Test rag_hybrid.py exists."""
        rag_file = Path(__file__).parent.parent.parent / "app" / "rag_hybrid.py"
        assert rag_file.exists()


@pytest.mark.unit
class TestDataFilesExist:
    """Tests that verify data/evaluation files exist."""
    
    def test_evaluation_directory_exists(self):
        """Test evaluation directory exists."""
        eval_dir = Path(__file__).parent.parent.parent / "app" / "evaluation"
        assert eval_dir.exists()
    
    def test_golden_dataset_exists(self):
        """Test golden dataset exists."""
        dataset_path = Path(__file__).parent.parent / "golden_dataset.json"
        assert dataset_path.exists()
    
    def test_golden_dataset_valid_json(self):
        """Test golden dataset is valid JSON."""
        dataset_path = Path(__file__).parent.parent / "golden_dataset.json"
        with open(dataset_path, "r") as f:
            data = json.load(f)
        assert "test_cases" in data
    
    def test_adversarial_prompts_exists(self):
        """Test adversarial prompts file exists."""
        prompts_path = Path(__file__).parent.parent / "safety" / "adversarial_prompts.json"
        assert prompts_path.exists()
    
    def test_adversarial_prompts_valid_json(self):
        """Test adversarial prompts is valid JSON."""
        prompts_path = Path(__file__).parent.parent / "safety" / "adversarial_prompts.json"
        with open(prompts_path, "r") as f:
            data = json.load(f)
        assert "prompts" in data
