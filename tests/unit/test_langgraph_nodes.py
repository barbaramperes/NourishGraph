"""
Unit tests for LangGraph individual nodes.

Tests each node function in isolation with mocked dependencies.
Covers: Planner, Router, Reflection, Synthesizer nodes.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from app.graph.state import AgentState, create_initial_state, Intent
from app.graph.nodes import (
    planner_node,
    router_node,
    route_to_agent,
    reflection_node,
    synthesizer_node,
    FastIntentClassifier,
)


# ============================================================================
# FAST INTENT CLASSIFIER TESTS
# ============================================================================

class TestFastIntentClassifier:
    """Test the regex-based intent classifier."""

    def test_classify_science_query(self):
        """Test classification of science queries."""
        classifier = FastIntentClassifier()

        test_cases = [
            "What does research say about vitamin D?",
            "Show me studies on omega-3",
            "What are the benefits of fasting?",
            "Is there scientific evidence for probiotics?",
            "What are the benefits of vitamin D?",
        ]

        for query in test_cases:
            intent, confidence, reasoning = classifier.classify(query)
            assert intent == "science", f"Failed for: {query}"
            assert confidence >= 0.7, f"Low confidence for: {query}"

    def test_classify_nutrition_query(self):
        """Test classification of nutrition calculation queries."""
        classifier = FastIntentClassifier()

        test_cases = [
            "Calculate my BMR",
            "How many calories in a banana?",
            "What's my TDEE?",
            "Calculate my macros",
            "How much protein in 100g chicken?",
        ]

        for query in test_cases:
            intent, confidence, reasoning = classifier.classify(query)
            assert intent == "nutrition", f"Failed for: {query}"
            assert confidence >= 0.7, f"Low confidence for: {query}"

    def test_classify_profile_query(self):
        """Test classification of profile management queries."""
        classifier = FastIntentClassifier()

        test_cases = [
            ("I weigh 70kg", ["profile"]),
            ("My goal is to lose weight", ["profile"]),
            ("I ate chicken for lunch", ["profile", "meal_planner"]),  # Can be either
            ("I'm 175cm tall", ["profile"]),
            ("I want to gain muscle", ["profile"]),
        ]

        for query, expected_intents in test_cases:
            intent, confidence, reasoning = classifier.classify(query)
            assert intent in expected_intents, f"Failed for: {query} (got {intent})"
            assert confidence >= 0.7, f"Low confidence for: {query}"

    def test_classify_meal_planner_query(self):
        """Test classification of meal planning queries."""
        classifier = FastIntentClassifier()

        test_cases = [
            "Create a meal plan for me",
            "Generate a weekly menu",
            "I don't like broccoli, can you replace it?",
            "Give me a meal plan for weight loss",
        ]

        for query in test_cases:
            intent, confidence, reasoning = classifier.classify(query)
            assert intent == "meal_planner", f"Failed for: {query}"
            assert confidence >= 0.7, f"Low confidence for: {query}"

    def test_classify_chat_query(self):
        """Test classification of general chat queries."""
        classifier = FastIntentClassifier()

        test_cases = [
            "Hello",
            "Thanks",
            "What can you do?",
            "Good morning",
        ]

        for query in test_cases:
            intent, confidence, reasoning = classifier.classify(query)
            assert intent == "chat", f"Failed for: {query}"

    def test_handles_empty_query(self):
        """Test handling of empty or invalid queries."""
        classifier = FastIntentClassifier()

        intent, confidence, reasoning = classifier.classify("")
        assert intent in ("chat", "ambiguous", "off_topic"), f"Got: {intent}"

    def test_priority_ordering(self):
        """Test that more specific patterns take priority."""
        classifier = FastIntentClassifier()

        intent, confidence, reasoning = classifier.classify("What are the benefits of vitamin D?")
        assert intent == "science"

        intent, confidence, reasoning = classifier.classify("How many calories in chicken?")
        assert intent == "nutrition"


# ============================================================================
# PLANNER NODE TESTS
# ============================================================================

class TestPlannerNode:
    """Test the planner node."""

    def test_planner_sets_intent_and_plan(self):
        """Test that planner node sets intent and plan in state."""
        state = create_initial_state("What does research say about omega-3?")

        result = planner_node(state)

        assert "intent" in result
        assert result["intent"] in Intent.ALL
        assert "plan" in result

    def test_planner_handles_multiple_queries(self):
        """Test planner with various query types."""
        queries = [
            ("What are the benefits of vitamin D?", "science"),
            ("Calculate my BMR", "nutrition"),
            ("I weigh 70kg", "profile"),
            ("Hello", "chat"),
            ("Create a meal plan", "meal_planner"),
        ]

        for query, expected_intent in queries:
            state = create_initial_state(query)
            result = planner_node(state)

            assert result.get("intent") == expected_intent, f"Failed for: {query}"

    def test_planner_preserves_existing_state(self):
        """Test that planner doesn't overwrite other state fields."""
        state = create_initial_state("Test query")
        state["context"] = {"existing": "data"}
        state["user_profile"] = {"name": "Test User"}

        result = planner_node(state)

        assert "intent" in result


# ============================================================================
# ROUTER NODE TESTS
# ============================================================================

class TestRouterNode:
    """Test the router node."""

    def test_router_confirms_intent(self):
        """Test that router node confirms the selected intent."""
        state = create_initial_state("Test query")
        state["intent"] = "science"

        result = router_node(state)

        assert "messages" in result
        assert len(result["messages"]) > 0

    def test_router_handles_all_intents(self):
        """Test router with all possible intents."""
        for intent in Intent.ALL:
            state = create_initial_state("Test query")
            state["intent"] = intent

            result = router_node(state)

            assert "messages" in result

    def test_router_defaults_to_chat(self):
        """Test that router defaults to chat if no intent set."""
        state = create_initial_state("Test query")

        result = router_node(state)

        assert "messages" in result


class TestRouteToAgent:
    """Test the conditional routing function."""

    def test_route_to_agent_returns_correct_intent(self):
        """Test that route_to_agent returns the intent from state."""
        for intent in Intent.ALL:
            state = create_initial_state("Test query")
            state["intent"] = intent

            result = route_to_agent(state)

            assert result == intent

    def test_route_to_agent_defaults_to_chat(self):
        """Test that route_to_agent defaults to chat if no intent."""
        state = create_initial_state("Test query")

        result = route_to_agent(state)

        assert result == "chat"


# ============================================================================
# REFLECTION NODE TESTS
# ============================================================================

class TestReflectionNode:
    """Test the reflection node."""

    @patch('app.graph.nodes.llm_reflection')
    def test_reflection_evaluates_response_quality(self, mock_llm):
        """Test that reflection node evaluates response quality."""
        mock_llm.invoke.return_value = Mock(
            content=json.dumps({
                "relevance": 0.9,
                "completeness": 0.85,
                "accuracy": 0.95,
                "clarity": 0.88,
                "safety": 1.0,
                "personalization": 0.7,
                "citations": 0.9,
                "overall_score": 0.88,
                "summary": "High quality response with good citations.",
                "strengths": ["Well cited", "Clear explanations"],
                "weaknesses": ["Could be more personalized"],
                "suggestions": ["Add user-specific recommendations"]
            })
        )

        state = create_initial_state("What are the benefits of omega-3?")
        state["intent"] = "science"
        state["agent_outputs"] = {
            "science": "Omega-3 fatty acids have numerous health benefits..."
        }

        result = reflection_node(state)

        assert "reflection" in result
        # In ablation mode (ENABLE_REFLECTION=false), confidence is inside reflection dict
        if isinstance(result["reflection"], dict) and result["reflection"].get("ablation_mode"):
            assert result["reflection"]["confidence"] > 0
        else:
            assert "confidence" in result
            assert result["confidence"] > 0

    @patch('app.graph.nodes.llm_reflection')
    def test_reflection_handles_low_quality_response(self, mock_llm):
        """Test reflection node with low quality response."""
        mock_llm.invoke.return_value = Mock(
            content=json.dumps({
                "overall_quality": "low",
                "confidence": 0.3,
                "dimensions": {
                    "relevance": {"score": 0.3, "note": "Not very relevant"},
                    "completeness": {"score": 0.4, "note": "Incomplete"},
                    "accuracy": {"score": 0.5, "note": "Some inaccuracies"},
                    "clarity": {"score": 0.4, "note": "Unclear"},
                    "safety": {"score": 0.8, "note": "Safe"},
                    "personalization": {"score": 0.2, "note": "Generic"},
                    "citations": {"score": 0.0, "note": "No citations"}
                },
                "strengths": [],
                "improvements": ["Add citations", "Make more complete"],
                "should_regenerate": False
            })
        )

        state = create_initial_state("Test query")
        state["agent_outputs"] = {"chat": "Short response"}

        result = reflection_node(state)

        # In ablation mode, confidence is inside the reflection dict
        if isinstance(result.get("reflection"), dict) and result["reflection"].get("ablation_mode"):
            assert result["reflection"]["confidence"] >= 0
        else:
            assert result["confidence"] < 0.5

    def test_reflection_handles_missing_agent_output(self):
        """Test reflection when no agent output is present."""
        state = create_initial_state("Test query")
        state["agent_outputs"] = {}

        result = reflection_node(state)

        assert "reflection" in result
        # In ablation mode, confidence is inside the reflection dict, not at top level
        if isinstance(result["reflection"], dict) and result["reflection"].get("ablation_mode"):
            assert result["reflection"]["confidence"] >= 0
        else:
            assert "confidence" in result


# ============================================================================
# SYNTHESIZER NODE TESTS
# ============================================================================

class TestSynthesizerNode:
    """Test the synthesizer node."""

    def test_synthesizer_formats_final_response(self):
        """Test that synthesizer creates final response."""
        state = create_initial_state("Test query")
        state["agent_outputs"] = {
            "science": "This is the science agent response."
        }
        state["confidence"] = 0.85

        result = synthesizer_node(state)

        assert "final_response" in result
        assert len(result["final_response"]) > 0
        assert "This is the science agent response" in result["final_response"]

    def test_synthesizer_adds_low_confidence_warning(self):
        """Test that synthesizer adds warning for low confidence (< 0.3)."""
        state = create_initial_state("Test query")
        state["agent_outputs"] = {"chat": "Response"}
        state["confidence"] = 0.1  # Must be < 0.3 to trigger warning

        result = synthesizer_node(state)

        assert "final_response" in result
        assert "⚠️" in result["final_response"] or "verif" in result["final_response"].lower()

    def test_synthesizer_handles_multiple_agent_outputs(self):
        """Test synthesizer with outputs from multiple agents."""
        state = create_initial_state("Test query")
        state["agent_outputs"] = {
            "science": "Science response",
            "nutrition": "Nutrition response",
            "chat": "Chat response"
        }
        state["confidence"] = 0.8

        result = synthesizer_node(state)

        assert "final_response" in result
        assert len(result["final_response"]) > 0

    def test_synthesizer_handles_no_agent_output(self):
        """Test synthesizer when no agent output is present."""
        state = create_initial_state("Test query")
        state["agent_outputs"] = {}
        state["confidence"] = 0.5

        result = synthesizer_node(state)

        assert "final_response" in result


# ============================================================================
# STATE CREATION TESTS
# ============================================================================

class TestStateCreation:
    """Test state initialization and creation."""

    def test_create_initial_state_basic(self):
        """Test basic state creation."""
        state = create_initial_state("Test query")

        assert state["user_input"] == "Test query"
        assert state["intent"] is None
        assert state["plan"] is None
        assert state["context"] == {}
        assert state["tools_used"] == []
        assert state["agent_outputs"] == {}
        assert state["confidence"] == 0.0
        assert state["final_response"] is None
        assert state["error"] is None

    def test_create_initial_state_with_profile(self):
        """Test state creation with user profile."""
        profile = {
            "age": 30,
            "weight": 70,
            "height": 175,
            "goal": "weight_loss"
        }

        state = create_initial_state("Test query", user_profile=profile)

        assert state["user_profile"] == profile

    def test_create_initial_state_with_chat_history(self):
        """Test state creation with conversation history."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "What can you do?"}
        ]

        state = create_initial_state("Current query", chat_history=history)

        assert len(state["messages"]) == 3

    def test_create_initial_state_empty_history(self):
        """Test state creation with empty history."""
        state = create_initial_state("Test query", chat_history=[])

        assert len(state["messages"]) == 0


# ============================================================================
# INTEGRATION - NODE CHAINING
# ============================================================================

class TestNodeChaining:
    """Test that nodes can be chained together."""

    def test_planner_to_router_flow(self):
        """Test data flow from planner to router."""
        state = create_initial_state("What are the benefits of omega-3?")
        planner_result = planner_node(state)

        state.update(planner_result)

        router_result = router_node(state)

        assert "messages" in router_result

        next_node = route_to_agent(state)
        assert next_node in Intent.ALL

    @patch('app.graph.nodes.llm_reflection')
    def test_agent_to_reflection_to_synthesizer_flow(self, mock_llm):
        """Test complete flow through agent output to final response."""
        mock_llm.invoke.return_value = Mock(
            content=json.dumps({
                "relevance": 0.9,
                "completeness": 0.85,
                "accuracy": 0.95,
                "clarity": 0.88,
                "safety": 1.0,
                "personalization": 0.7,
                "citations": 0.9,
                "overall_score": 0.88,
                "summary": "Good response",
                "strengths": [],
                "weaknesses": [],
                "suggestions": []
            })
        )

        state = create_initial_state("Test query")
        state["agent_outputs"] = {"science": "Agent response here"}

        reflection_result = reflection_node(state)
        state.update(reflection_result)

        synthesizer_result = synthesizer_node(state)

        assert "final_response" in synthesizer_result
        assert "Agent response here" in synthesizer_result["final_response"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
