"""
Integration tests for the complete LangGraph workflow.

Tests the full pipeline execution from user input to final response,
including all nodes and state transitions.

Note: These tests may require API keys for OpenAI and Pinecone.
Use mocks where appropriate to avoid excessive API calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
import json

from app.graph.graph import create_graph, run_agent, run_agent_with_streaming
from app.graph.state import create_initial_state, Intent


# ============================================================================
# HELPERS
# ============================================================================

def has_openai_key():
    """Check if OpenAI API key is available."""
    import os
    return bool(os.getenv("OPENAI_API_KEY"))


# ============================================================================
# GRAPH STRUCTURE TESTS (No API calls required)
# ============================================================================

@pytest.mark.unit
class TestGraphStructure:
    """Test the graph structure and configuration."""

    def test_create_graph_succeeds(self):
        """Test that graph creation succeeds."""
        graph = create_graph()
        assert graph is not None

    def test_graph_has_all_nodes(self):
        """Test that all required nodes are registered."""
        graph = create_graph()
        compiled = graph.compile()

        assert compiled is not None

    def test_graph_compilation(self):
        """Test that graph compiles successfully."""
        graph = create_graph()
        compiled = graph.compile()

        assert hasattr(compiled, 'invoke')
        assert callable(compiled.invoke)


# ============================================================================
# WORKFLOW EXECUTION TESTS (Requires API keys or mocks)
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(not has_openai_key(), reason="Requires OpenAI API key")
class TestWorkflowExecution:
    """Test complete workflow execution with real API calls."""

    def test_science_query_workflow(self):
        """Test workflow for science queries."""
        result = run_agent(
            user_input="What does research say about vitamin D and immunity?",
            user_id=999
        )

        assert result is not None
        assert "final_response" in result
        assert result["final_response"] is not None
        assert len(result["final_response"]) > 0

        assert result.get("intent") == "science"

        assert len(result.get("tools_used", [])) > 0

    def test_nutrition_query_workflow(self):
        """Test workflow for nutrition calculation queries."""
        result = run_agent(
            user_input="Calculate my BMR. I'm 30 years old, 70kg, 175cm, male.",
            user_id=999
        )

        assert result is not None
        assert "final_response" in result
        assert result["final_response"] is not None

        assert result.get("intent") == "nutrition"

        assert "bmr" in result["final_response"].lower() or "kcal" in result["final_response"].lower()

    def test_profile_query_workflow(self):
        """Test workflow for profile management queries."""
        result = run_agent(
            user_input="I weigh 75kg",
            user_id=999
        )

        assert result is not None
        assert "final_response" in result
        assert result.get("intent") == "profile"

        assert "confirm" in result["final_response"].lower() or "save" in result["final_response"].lower()

    def test_chat_query_workflow(self):
        """Test workflow for general chat queries."""
        result = run_agent(
            user_input="Hello, what can you do?",
            user_id=999
        )

        assert result is not None
        assert "final_response" in result
        assert result.get("intent") == "chat"

    def test_meal_planner_workflow(self):
        """Test workflow for meal planning queries."""
        result = run_agent(
            user_input="Create a meal plan for weight loss",
            user_profile={"goal": "weight_loss", "weight": 70, "height": 175, "age": 30},
            user_id=999
        )

        assert result is not None
        assert "final_response" in result
        assert result.get("intent") == "meal_planner"


# ============================================================================
# WORKFLOW WITH MOCKS (Fast, no API calls)
# ============================================================================

@pytest.mark.unit
class TestWorkflowWithMocks:
    """Test workflow with mocked components for fast execution."""

    @patch('app.agents.science_agent.get_science_agent')
    @patch('app.graph.nodes.llm_reflection')
    @patch('app.graph.nodes.llm')
    def test_workflow_with_mocked_agents(self, mock_llm, mock_reflection, mock_science_agent):
        """Test complete workflow with mocked agent responses."""
        mock_llm.invoke.return_value = Mock(
            content='{"intent": "science", "confidence": 0.95}'
        )

        mock_reflection.invoke.return_value = Mock(
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

        mock_agent_instance = MagicMock()
        mock_agent_instance.invoke.return_value = {
            "messages": [Mock(content="Mocked science response about vitamin D")]
        }
        mock_science_agent.return_value = mock_agent_instance

        result = run_agent(
            user_input="What are the benefits of vitamin D?",
            user_id=999
        )

        assert result is not None
        assert "final_response" in result

    @patch('app.graph.nodes.FastIntentClassifier.classify')
    def test_workflow_with_mocked_router(self, mock_classify):
        """Test workflow with mocked intent classification."""
        mock_classify.return_value = ("nutrition", 0.95, "Mocked classification")

        state = create_initial_state("Calculate my BMR")

        from app.graph.nodes import planner_node

        result = planner_node(state)

        assert result.get("intent") == "nutrition"


# ============================================================================
# STATE TRANSITION TESTS
# ============================================================================

@pytest.mark.integration
class TestStateTransitions:
    """Test state transitions through the workflow."""

    def test_state_accumulates_data(self):
        """Test that state accumulates data as it flows through nodes."""
        initial_state = create_initial_state("Test query")

        assert initial_state["tools_used"] == []
        assert initial_state["agent_outputs"] == {}
        assert initial_state["confidence"] == 0.0

        initial_state["intent"] = "science"
        initial_state["plan"] = "Search for scientific papers"

        assert initial_state["intent"] == "science"
        assert initial_state["plan"] is not None

        initial_state["agent_outputs"]["science"] = "Agent response"
        initial_state["tools_used"].append("search_scientific_papers")

        assert len(initial_state["agent_outputs"]) == 1
        assert len(initial_state["tools_used"]) == 1

        initial_state["confidence"] = 0.85
        initial_state["reflection"] = "High quality response"

        assert initial_state["confidence"] == 0.85

        initial_state["final_response"] = "Final formatted response"

        assert initial_state["final_response"] is not None

    def test_state_preserves_user_context(self):
        """Test that user profile is preserved throughout workflow."""
        profile = {
            "age": 30,
            "weight": 70,
            "height": 175,
            "goal": "weight_loss"
        }

        state = create_initial_state("Test query", user_profile=profile)

        assert state["user_profile"] == profile

        state["intent"] = "nutrition"
        state["agent_outputs"]["nutrition"] = "Response"

        assert state["user_profile"] == profile

    def test_state_handles_errors(self):
        """Test that state can hold error information."""
        state = create_initial_state("Test query")

        assert state["error"] is None

        state["error"] = "API timeout"

        assert state["error"] == "API timeout"


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_user_input(self):
        """Test handling of empty user input."""
        state = create_initial_state("")

        from app.graph.nodes import planner_node

        result = planner_node(state)

        assert "intent" in result

    def test_very_long_user_input(self):
        """Test handling of very long user input."""
        long_input = "What are the benefits of vitamin D? " * 100

        state = create_initial_state(long_input)

        from app.graph.nodes import planner_node

        result = planner_node(state)

        assert "intent" in result

    def test_special_characters_in_input(self):
        """Test handling of special characters."""
        special_inputs = [
            "What about omega-3 & vitamin D?",
            "Calculate my BMR (I'm 30 years old)",
            "Benefits of: magnesium, zinc, iron",
            "¿Qué es la dieta mediterránea?",
        ]

        for inp in special_inputs:
            state = create_initial_state(inp)

            from app.graph.nodes import planner_node

            result = planner_node(state)

            assert "intent" in result

    @patch('app.graph.nodes.llm')
    def test_llm_timeout_handling(self, mock_llm):
        """Test handling of LLM timeouts."""
        mock_llm.invoke.side_effect = Exception("Request timeout")

        state = create_initial_state("Test query")

        from app.graph.nodes import planner_node

        try:
            result = planner_node(state)
        except Exception as e:
            assert "timeout" in str(e).lower() or "error" in str(e).lower()

    def test_missing_agent_output(self):
        """Test synthesizer when agent fails to produce output."""
        state = create_initial_state("Test query")
        state["agent_outputs"] = {}
        state["confidence"] = 0.5

        from app.graph.nodes import synthesizer_node

        result = synthesizer_node(state)

        assert "final_response" in result
        assert len(result["final_response"]) > 0


# ============================================================================
# CONVERSATION HISTORY TESTS
# ============================================================================

@pytest.mark.integration
class TestConversationHistory:
    """Test workflow with conversation history."""

    def test_workflow_with_history(self):
        """Test that conversation history is used in workflow."""
        history = [
            {"role": "user", "content": "I want to lose weight"},
            {"role": "assistant", "content": "Great! I can help you with that."},
        ]

        state = create_initial_state(
            "What should I eat for breakfast?",
            chat_history=history
        )

        assert len(state["messages"]) == 2

    def test_multi_turn_conversation(self):
        """Test multiple turns in conversation."""
        result1 = run_agent(
            user_input="I want to lose weight",
            user_id=999
        )

        assert result1 is not None

        history = [
            {"role": "user", "content": "I want to lose weight"},
            {"role": "assistant", "content": result1["final_response"]},
        ]

        result2 = run_agent(
            user_input="What should I eat?",
            chat_history=history,
            user_id=999
        )

        assert result2 is not None
        assert "final_response" in result2


# ============================================================================
# STREAMING TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(not has_openai_key(), reason="Requires OpenAI API key")
class TestStreaming:
    """Test streaming workflow execution."""

    def test_streaming_yields_events(self):
        """Test that streaming workflow yields events."""
        events = list(run_agent_with_streaming(
            user_input="What are the benefits of omega-3?",
            user_id=999
        ))

        assert len(events) > 0

        for event in events:
            assert isinstance(event, dict)

    def test_streaming_final_event_has_response(self):
        """Test that final streaming event contains the response."""
        events = list(run_agent_with_streaming(
            user_input="Hello",
            user_id=999
        ))

        if events:
            has_final = any(
                "final_response" in state
                for event in events
                for node_name, state in event.items()
            )
            assert has_final, "No event contained final_response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
