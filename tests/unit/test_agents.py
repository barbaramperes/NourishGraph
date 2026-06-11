"""
Unit tests for individual agents.
"""

import pytest
import os
from pathlib import Path


def has_api_key() -> bool:
    """Check if OpenAI API key is available."""
    key = os.environ.get("OPENAI_API_KEY", "")
    return bool(key) and not key.startswith("sk-...")


# ============================================================================
# STRUCTURE TESTS (No API needed)
# ============================================================================

@pytest.mark.unit
class TestAgentModulesExist:
    """Tests that verify agent module files exist."""
    
    def test_agents_directory_exists(self):
        """Test agents directory exists."""
        agents_dir = Path(__file__).parent.parent.parent / "app" / "agents"
        assert agents_dir.exists()
    
    def test_nutrition_agent_file_exists(self):
        """Test nutrition_agent.py exists."""
        agent_file = Path(__file__).parent.parent.parent / "app" / "agents" / "nutrition_agent.py"
        assert agent_file.exists()
    
    def test_science_agent_file_exists(self):
        """Test science_agent.py exists."""
        agent_file = Path(__file__).parent.parent.parent / "app" / "agents" / "science_agent.py"
        assert agent_file.exists()
    
    def test_meal_planner_agent_file_exists(self):
        """Test meal_planner_agent.py exists."""
        agent_file = Path(__file__).parent.parent.parent / "app" / "agents" / "meal_planner_agent.py"
        assert agent_file.exists()
    
    def test_base_agent_file_exists(self):
        """Test base_agent.py exists."""
        agent_file = Path(__file__).parent.parent.parent / "app" / "agents" / "base_agent.py"
        assert agent_file.exists()


@pytest.mark.unit
class TestAgentFileContent:
    """Tests that verify agent files have expected content."""
    
    def test_nutrition_agent_has_class(self):
        """Test nutrition_agent.py contains NutritionAgent class."""
        agent_file = Path(__file__).parent.parent.parent / "app" / "agents" / "nutrition_agent.py"
        content = agent_file.read_text()
        assert "class NutritionAgent" in content
    
    def test_science_agent_has_class(self):
        """Test science_agent.py contains ScienceAgent class."""
        agent_file = Path(__file__).parent.parent.parent / "app" / "agents" / "science_agent.py"
        content = agent_file.read_text()
        assert "class ScienceAgent" in content
    
    def test_base_agent_has_class(self):
        """Test base_agent.py contains BaseAgent class."""
        agent_file = Path(__file__).parent.parent.parent / "app" / "agents" / "base_agent.py"
        content = agent_file.read_text()
        assert "class BaseAgent" in content


# ============================================================================
# IMPORT/INSTANTIATION TESTS (Require API)
# ============================================================================

@pytest.mark.unit
@pytest.mark.skipif(not has_api_key(), reason="OPENAI_API_KEY required")
class TestAgentImports:
    """Tests that verify agents can be imported."""
    
    def test_nutrition_agent_import(self):
        """Test NutritionAgent can be imported."""
        from app.agents.nutrition_agent import NutritionAgent
        assert NutritionAgent is not None
    
    def test_science_agent_import(self):
        """Test ScienceAgent can be imported."""
        from app.agents.science_agent import ScienceAgent
        assert ScienceAgent is not None


@pytest.mark.unit
@pytest.mark.skipif(not has_api_key(), reason="OPENAI_API_KEY required")
class TestAgentFunctional:
    """Functional tests for agents."""
    
    def test_nutrition_agent_instantiation(self, nutrition_agent):
        """Test NutritionAgent can be instantiated."""
        assert nutrition_agent is not None
    
    def test_science_agent_instantiation(self, science_agent):
        """Test ScienceAgent can be instantiated."""
        assert science_agent is not None
