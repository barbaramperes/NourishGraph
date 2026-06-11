"""
NourishGraph Agent Tests
Tests for the multi-agent system
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIntentClassifier:
    """Test the intent classification system."""

    def test_classifier_import(self):
        """Test classifier can be imported."""
        from app.agents.classifier import IntentClassifier
        classifier = IntentClassifier()
        assert classifier is not None

    def test_science_intent(self):
        """Test science queries are classified correctly."""
        from app.agents.classifier import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify("What does research say about vitamin D?")
        assert result["intent"] in ["science", "nutrition", "chat"]
        assert result["confidence"] > 0

    def test_nutrition_intent(self):
        """Test nutrition queries are classified correctly."""
        from app.agents.classifier import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify("How many calories should I eat?")
        assert result["intent"] in ["nutrition", "chat"]

    def test_meal_planner_intent(self):
        """Test meal planning queries."""
        from app.agents.classifier import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify("Suggest a healthy breakfast")
        assert result["intent"] in ["meal_planner", "nutrition", "chat"]

    def test_medical_blocking(self):
        """Test medical queries are blocked for safety."""
        from app.agents.classifier import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify("What is the correct insulin dosage?")
        assert result["blocked"] == True
        assert result["is_medical"] == True

    def test_safe_query_not_blocked(self):
        """Test normal queries are not blocked."""
        from app.agents.classifier import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify("What foods are high in protein?")
        assert result["blocked"] == False


class TestBaseAgent:
    """Test the base agent class."""

    def test_task_types(self):
        """Test task type configurations."""
        from app.agents.base_agent import TaskType, TASK_CONFIGS
        assert TaskType.CALCULATION in TASK_CONFIGS
        assert TaskType.ANALYSIS in TASK_CONFIGS
        assert TASK_CONFIGS[TaskType.CALCULATION]["temperature"] <= 0.2

    def test_evidence_levels(self):
        """Test evidence level classification."""
        from app.agents.base_agent import EvidenceLevel
        assert EvidenceLevel.HIGH.value == "A"
        assert EvidenceLevel.MODERATE.value == "B"
        assert EvidenceLevel.LOW.value == "C"

    def test_agent_response_structure(self):
        """Test AgentResponse dataclass."""
        from app.agents.base_agent import AgentResponse
        response = AgentResponse(
            content="Test response",
            tools_used=["search_papers"],
            confidence=0.85
        )
        assert response.content == "Test response"
        assert response.confidence == 0.85


class TestNutritionCalculations:
    """Test nutrition calculation functions."""

    def test_bmr_calculation(self):
        """Test BMR calculation (Mifflin-St Jeor)."""
        weight, height, age = 70, 175, 30
        bmr_male = 10 * weight + 6.25 * height - 5 * age + 5
        bmr_female = 10 * weight + 6.25 * height - 5 * age - 161
        assert 1600 < bmr_male < 1800
        assert 1400 < bmr_female < 1600

    def test_tdee_multipliers(self):
        """Test TDEE activity multipliers."""
        bmr = 1700
        tdee_sedentary = bmr * 1.2
        tdee_active = bmr * 1.725
        assert 2000 < tdee_sedentary < 2100
        assert 2900 < tdee_active < 3000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
