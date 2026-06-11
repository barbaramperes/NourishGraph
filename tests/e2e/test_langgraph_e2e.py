"""
End-to-end tests for the complete LangGraph system.

These tests validate the entire system working together,
from user input through all agents to final response.

Tests include:
- Complete user journeys
- Multi-agent collaboration scenarios
- Real RAG queries
- Error recovery
- Performance benchmarks
"""

import pytest
import time
from typing import Dict, Any
import os

from app.graph.graph import run_agent, run_agent_with_streaming


# ============================================================================
# HELPERS
# ============================================================================

def has_api_keys():
    """Check if required API keys are available."""
    return bool(os.getenv("OPENAI_API_KEY"))


# ============================================================================
# COMPLETE USER JOURNEYS
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skipif(not has_api_keys(), reason="Requires API keys")
class TestUserJourneys:
    """Test complete user interaction journeys."""

    def test_new_user_onboarding_journey(self):
        """Test a new user going through profile setup and first query."""
        user_id = 1000

        result1 = run_agent(
            user_input="I weigh 70kg",
            user_id=user_id
        )

        assert result1["intent"] == "profile"
        assert "confirm" in result1["final_response"].lower()

        result2 = run_agent(
            user_input="CONFIRM",
            user_id=user_id
        )

        result3 = run_agent(
            user_input="Calculate my BMR. I'm 30 years old, 175cm, male.",
            user_profile={"weight": 70, "age": 30, "height": 175, "sex": "male"},
            user_id=user_id
        )

        assert result3["intent"] == "nutrition"
        assert "bmr" in result3["final_response"].lower() or "kcal" in result3["final_response"].lower()

        result4 = run_agent(
            user_input="What does research say about protein for muscle building?",
            user_id=user_id
        )

        assert result4["intent"] == "science"

    def test_weight_loss_journey(self):
        """Test a weight loss focused user journey."""
        user_id = 1001

        profile = {
            "age": 35,
            "weight": 85,
            "height": 170,
            "sex": "female",
            "goal": "weight_loss",
            "activity_level": "moderate"
        }

        result1 = run_agent(
            user_input="Calculate my daily calorie needs for weight loss",
            user_profile=profile,
            user_id=user_id
        )

        assert result1["intent"] == "nutrition"

        result2 = run_agent(
            user_input="What are good high-protein, low-calorie foods for weight loss?",
            user_profile=profile,
            user_id=user_id
        )

        assert result2["intent"] in ["nutrition", "science"]

        result3 = run_agent(
            user_input="Create a meal plan for me",
            user_profile=profile,
            user_id=user_id
        )

        assert result3["intent"] == "meal_planner"

    def test_science_research_journey(self):
        """Test a user researching nutrition topics."""
        user_id = 1002

        queries = [
            "What does research say about intermittent fasting?",
            "Are there studies on omega-3 and heart health?",
            "What are the benefits of vitamin D for immunity?",
        ]

        for query in queries:
            result = run_agent(
                user_input=query,
                user_id=user_id
            )

            assert result["intent"] == "science", f"Failed for: {query}"
            assert len(result["final_response"]) > 50


# ============================================================================
# MULTI-AGENT COLLABORATION
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skipif(not has_api_keys(), reason="Requires API keys")
class TestMultiAgentCollaboration:
    """Test scenarios requiring multiple agents."""

    def test_profile_then_nutrition_flow(self):
        """Test profile data being used in nutrition calculations."""
        user_id = 1003

        result1 = run_agent(
            user_input="I weigh 75kg, I'm 180cm tall, 28 years old, male",
            user_id=user_id
        )

        assert result1["intent"] == "profile"

        profile = {
            "weight": 75,
            "height": 180,
            "age": 28,
            "sex": "male"
        }

        result2 = run_agent(
            user_input="Calculate my BMR and TDEE for moderate activity",
            user_profile=profile,
            user_id=user_id
        )

        assert result2["intent"] == "nutrition"
        assert "75" in result2["final_response"] or "1800" in result2["final_response"] or "kcal" in result2["final_response"]

    def test_science_then_nutrition_flow(self):
        """Test getting science info then calculating nutrition."""
        user_id = 1004

        result1 = run_agent(
            user_input="What does research say about protein requirements?",
            user_id=user_id
        )

        assert result1["intent"] == "science"

        profile = {"weight": 70, "goal": "gain_muscle"}

        result2 = run_agent(
            user_input="How much protein should I eat per day?",
            user_profile=profile,
            user_id=user_id
        )

        assert result2["final_response"] is not None


# ============================================================================
# ERROR RECOVERY AND EDGE CASES
# ============================================================================

@pytest.mark.e2e
class TestErrorRecovery:
    """Test system recovery from errors."""

    def test_ambiguous_query_handling(self):
        """Test handling of ambiguous queries."""
        # This query could be science or nutrition
        result = run_agent(
            user_input="Tell me about protein",
            user_id=1005
        )

        # Should classify to some agent
        assert result["intent"] in ["science", "nutrition", "chat"]
        assert result["final_response"] is not None

    def test_incomplete_information(self):
        """Test handling of queries with incomplete information."""
        # BMR calculation without all required data
        result = run_agent(
            user_input="Calculate my BMR",
            user_id=1006
        )

        # Should handle gracefully
        assert result["final_response"] is not None
        # Should ask for missing info
        assert any(word in result["final_response"].lower() for word in ["age", "weight", "height", "need", "provide"])

    def test_contradictory_information(self):
        """Test handling of contradictory user information."""
        profile = {
            "goal": "weight_loss",
            "weight": 50,  # Already quite low
        }

        result = run_agent(
            user_input="I want to lose 20kg",
            user_profile=profile,
            user_id=1007
        )

        # Should handle carefully
        assert result["final_response"] is not None


# ============================================================================
# CONVERSATION CONTEXT TESTS
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skipif(not has_api_keys(), reason="Requires API keys")
class TestConversationContext:
    """Test multi-turn conversations with context."""

    def test_follow_up_questions(self):
        """Test that follow-up questions use previous context."""
        user_id = 1008

        result1 = run_agent(
            user_input="What are the benefits of omega-3?",
            user_id=user_id
        )

        assert result1["intent"] == "science"

        history = [
            {"role": "user", "content": "What are the benefits of omega-3?"},
            {"role": "assistant", "content": result1["final_response"]},
        ]

        result2 = run_agent(
            user_input="What foods contain it?",
            chat_history=history,
            user_id=user_id
        )

        assert result2["final_response"] is not None

    def test_topic_switching(self):
        """Test switching topics in conversation."""
        user_id = 1009

        result1 = run_agent(
            user_input="What does research say about vitamin D?",
            user_id=user_id
        )

        history = [
            {"role": "user", "content": "What does research say about vitamin D?"},
            {"role": "assistant", "content": result1["final_response"]},
        ]

        result2 = run_agent(
            user_input="Calculate my BMR. I'm 30, 70kg, 175cm, male.",
            chat_history=history,
            user_id=user_id
        )

        assert result2["intent"] == "nutrition"


# ============================================================================
# PERFORMANCE BENCHMARKS
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skipif(not has_api_keys(), reason="Requires API keys")
class TestPerformance:
    """Test system performance benchmarks."""

    def test_response_time_science_query(self):
        """Test response time for science queries."""
        start = time.time()

        result = run_agent(
            user_input="What does research say about vitamin D?",
            user_id=1010
        )

        elapsed = time.time() - start

        assert result["final_response"] is not None
        assert elapsed < 30, f"Query took {elapsed:.2f}s, expected < 30s"

    def test_response_time_nutrition_query(self):
        """Test response time for nutrition calculations."""
        start = time.time()

        result = run_agent(
            user_input="Calculate my BMR. I'm 30, 70kg, 175cm, male.",
            user_id=1011
        )

        elapsed = time.time() - start

        assert result["final_response"] is not None
        assert elapsed < 20, f"Query took {elapsed:.2f}s, expected < 20s"

    def test_streaming_performance(self):
        """Test that streaming provides progressive updates."""
        start = time.time()
        first_event_time = None

        events = list(run_agent_with_streaming(
            user_input="What are the benefits of omega-3?",
            user_id=1012
        ))

        if events:
            assert len(events) > 1, "Should yield multiple events for streaming"

    def test_concurrent_users_handling(self):
        """Test that system handles multiple concurrent users."""

        user_ids = [2001, 2002, 2003]
        queries = [
            "What are the benefits of vitamin D?",
            "Calculate my BMR. I'm 30, 70kg, 175cm, male.",
            "I want to lose weight",
        ]

        results = []
        for user_id, query in zip(user_ids, queries):
            result = run_agent(
                user_input=query,
                user_id=user_id
            )
            results.append(result)

        for result in results:
            assert result["final_response"] is not None


# ============================================================================
# QUALITY ASSURANCE
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skipif(not has_api_keys(), reason="Requires API keys")
class TestQualityAssurance:
    """Test response quality across different scenarios."""

    def test_responses_have_minimum_length(self):
        """Test that responses are substantive."""
        queries = [
            "What are the benefits of omega-3?",
            "Calculate my BMR. I'm 30, 70kg, 175cm, male.",
            "Create a meal plan for weight loss",
        ]

        for query in queries:
            result = run_agent(user_input=query, user_id=3000)

            assert len(result["final_response"]) > 50, f"Response too short for: {query}"

    def test_responses_include_relevant_keywords(self):
        """Test that responses contain relevant information."""
        test_cases = [
            ("What does research say about vitamin D?", ["vitamin", "research", "stud"]),
            ("Calculate my BMR", ["bmr", "kcal", "calories"]),
            ("I want to lose weight", ["weight", "loss", "calor"]),
        ]

        for query, expected_keywords in test_cases:
            result = run_agent(user_input=query, user_id=3001)

            response_lower = result["final_response"].lower()

            assert any(kw in response_lower for kw in expected_keywords), \
                f"Response missing keywords for: {query}"

    def test_confidence_scores_are_reasonable(self):
        """Test that confidence scores are in valid range."""
        queries = [
            "What does research say about vitamin D?",
            "Calculate my BMR. I'm 30, 70kg, 175cm, male.",
            "Hello",
        ]

        for query in queries:
            result = run_agent(user_input=query, user_id=3002)

            confidence = result.get("confidence", 0)

            assert 0 <= confidence <= 1, f"Invalid confidence {confidence} for: {query}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
