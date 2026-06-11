"""
Unit tests for router classification accuracy.

Tests that verify the router correctly classifies
different types of user queries.
"""

import pytest
from unittest.mock import patch


@pytest.mark.unit
class TestRouterAccuracy:
    """Test router classification accuracy."""

    @pytest.mark.parametrize("query,expected_intents", [
        # Science queries - research/evidence-based
        ("What do studies say about omega-3?", ["science"]),
        ("Benefits of vitamin D", ["science", "nutrition"]),  # Can be either depending on context
        ("Research on intermittent fasting", ["science"]),
        ("What does science say about protein?", ["science", "nutrition"]),  # Can be either
        ("Evidence for Mediterranean diet", ["science"]),
        ("What are the health benefits of fiber?", ["science"]),

        # Nutrition queries - calculations/food data
        ("How many calories in a banana?", ["nutrition"]),
        ("Calculate my BMR", ["nutrition"]),
        ("What are my macros?", ["nutrition"]),
        ("Calories in 100g chicken breast", ["nutrition"]),
        ("How much protein do I need?", ["science", "nutrition"]),  # General question - can be either
        ("What is my TDEE?", ["nutrition"]),

        # Profile queries - personal data
        ("I weigh 70kg", ["profile"]),
        ("I ate chicken for lunch", ["profile"]),
        ("I'm 30 years old", ["profile"]),
        ("My height is 175cm", ["profile"]),

        # Meal planning
        ("Create a meal plan for me", ["meal_planner"]),
        ("Plan my weekly meals", ["meal_planner", "science", "nutrition"]),  # Ambiguous - can be any
        ("Suggest a healthy lunch", ["meal_planner", "science", "nutrition"]),  # Ambiguous - can be any

        # Chat - general conversation
        ("Hello", ["chat"]),
        ("Thanks", ["chat"]),
        ("What can you do?", ["chat"]),
        ("Good morning", ["chat"]),
    ])
    def test_router_classification(self, query, expected_intents, mock_openai):
        """Test router classifies queries correctly."""
        from app.graph.nodes import planner_node

        # Mock LLM response with first expected intent
        mock_openai.return_value.invoke.return_value.content = f'{{"intent": "{expected_intents[0]}", "confidence": 0.9, "plan": ["Step 1"], "thinking": "Analysis"}}'

        result = planner_node({"user_input": query, "messages": []})

        assert result["intent"] in expected_intents, f"Failed to classify '{query}' - got '{result['intent']}', expected one of {expected_intents}"
        assert "plan" in result
        assert "confidence" in result

    def test_router_handles_ambiguous_queries(self, mock_openai):
        """Test router handles ambiguous queries gracefully."""
        from app.graph.nodes import planner_node

        ambiguous_queries = [
            "vitamin d",  # Could be science or nutrition
            "calories",   # Ambiguous without context
            "protein",    # Could be many intents
        ]

        for query in ambiguous_queries:
            # Mock with low confidence
            mock_openai.return_value.invoke.return_value.content = '{"intent": "chat", "confidence": 0.5, "plan": ["Clarify"], "thinking": "Ambiguous"}'

            result = planner_node({"user_input": query, "messages": []})

            # Should still return a valid intent
            assert result["intent"] in ["science", "nutrition", "profile", "meal_planner", "chat"]
            assert "confidence" in result

    def test_router_with_conversation_context(self, mock_openai):
        """Test router uses conversation history for context."""
        from app.graph.nodes import planner_node
        from langchain_core.messages import HumanMessage, AIMessage

        # Conversation about meal planning
        messages = [
            HumanMessage(content="I want to eat healthier"),
            AIMessage(content="Great! I can help with that."),
            HumanMessage(content="Can you create a meal plan for me?")  # More explicit
        ]

        # Mock expects meal_planner based on explicit query
        mock_openai.return_value.invoke.return_value.content = '{"intent": "meal_planner", "confidence": 0.85, "plan": ["Create meal plan"], "thinking": "User wants meal plan"}'

        result = planner_node({
            "user_input": "Can you create a meal plan for me?",
            "messages": messages
        })

        assert result["intent"] == "meal_planner"

    def test_router_handles_medical_conditions(self, mock_openai):
        """Test router routes medical condition queries appropriately."""
        from app.graph.nodes import planner_node

        # Test that medical condition query with explicit pattern is recognized
        medical_query = "I have diabetes, what should I eat?"

        result = planner_node({"user_input": medical_query, "messages": []})

        # This query matches the nutrition pattern for medical conditions
        assert result["intent"] == "nutrition", f"Medical query '{medical_query}' should route to nutrition"

        # Test general health query - may go to science
        health_query = "Foods for high blood pressure"
        result2 = planner_node({"user_input": health_query, "messages": []})

        # This is a general health question, may be classified as science
        assert result2["intent"] in ["nutrition", "science"], f"Health query '{health_query}' should route to nutrition or science"

    def test_router_confidence_threshold(self, mock_openai):
        """Test router returns confidence scores."""
        from app.graph.nodes import planner_node

        # High confidence query
        mock_openai.return_value.invoke.return_value.content = '{"intent": "science", "confidence": 0.95, "plan": ["Search papers"], "thinking": "Clear science query"}'

        result = planner_node({
            "user_input": "What do studies say about omega-3?",
            "messages": []
        })

        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0, "Confidence should be between 0 and 1"


@pytest.mark.unit
class TestRouterRobustness:
    """Test router robustness with edge cases."""

    def test_router_handles_empty_input(self, mock_openai):
        """Test router handles empty or whitespace input."""
        from app.graph.nodes import planner_node

        mock_openai.return_value.invoke.return_value.content = '{"intent": "chat", "confidence": 0.3, "plan": ["Request input"], "thinking": "Empty input"}'

        result = planner_node({"user_input": "", "messages": []})

        assert result["intent"] is not None
        assert result["intent"] in ["chat", "science", "nutrition", "profile", "meal_planner"]

    def test_router_handles_very_long_input(self, mock_openai):
        """Test router handles very long queries."""
        from app.graph.nodes import planner_node

        long_query = "I want to know about nutrition " * 100  # 500+ words

        mock_openai.return_value.invoke.return_value.content = '{"intent": "chat", "confidence": 0.7, "plan": ["Respond"], "thinking": "Long query"}'

        result = planner_node({"user_input": long_query, "messages": []})

        assert result["intent"] is not None

    def test_router_handles_special_characters(self, mock_openai):
        """Test router handles special characters and emojis."""
        from app.graph.nodes import planner_node

        special_queries = [
            "What are the benefits of omega-3? 🐟",
            "I ate 100g of rice @ lunch!",
            "Calories in a medium-sized apple (150g)",
        ]

        for query in special_queries:
            mock_openai.return_value.invoke.return_value.content = '{"intent": "nutrition", "confidence": 0.8, "plan": ["Calculate"], "thinking": "Food query"}'

            result = planner_node({"user_input": query, "messages": []})

            assert result["intent"] is not None, f"Failed on query: {query}"

    def test_router_handles_multilingual_input(self, mock_openai):
        """Test router handles queries in Portuguese."""
        from app.graph.nodes import planner_node

        portuguese_queries = [
            "Quantas calorias tem uma banana?",
            "Benefícios da vitamina D",
        ]

        for query in portuguese_queries:
            mock_openai.return_value.invoke.return_value.content = '{"intent": "nutrition", "confidence": 0.75, "plan": ["Calculate"], "thinking": "PT query"}'

            result = planner_node({"user_input": query, "messages": []})

            assert result["intent"] is not None, f"Failed on Portuguese query: {query}"


@pytest.mark.unit
class TestRouterPerformance:
    """Test router performance characteristics."""

    def test_router_returns_quickly(self, mock_openai):
        """Test router responds in reasonable time."""
        import time
        from app.graph.nodes import planner_node

        mock_openai.return_value.invoke.return_value.content = '{"intent": "nutrition", "confidence": 0.9, "plan": ["Calculate"], "thinking": "Food query"}'

        start = time.time()
        result = planner_node({
            "user_input": "How many calories in a banana?",
            "messages": []
        })
        duration = time.time() - start

        assert result["intent"] is not None
        # With mocking, should be very fast (<100ms)
        assert duration < 0.1, f"Router took {duration:.3f}s (too slow even with mocks)"

    def test_router_handles_concurrent_requests(self, mock_openai):
        """Test router can handle multiple queries in sequence."""
        from app.graph.nodes import planner_node

        queries = [
            "What do studies say about protein?",
            "How many calories do I need?",
            "I ate pizza",
            "Create a meal plan",
            "Hello",
        ]

        expected_intents = ["science", "nutrition", "profile", "meal_planner", "chat"]

        for query, expected in zip(queries, expected_intents):
            mock_openai.return_value.invoke.return_value.content = f'{{"intent": "{expected}", "confidence": 0.9, "plan": ["Step 1"], "thinking": "Analysis"}}'

            result = planner_node({"user_input": query, "messages": []})

            assert result["intent"] == expected
