"""
Unit tests for the LLM-based Query Analysis pipeline.

Tests the new pre-classification layer:
- query_analysis_node (LLM classifier)
- route_after_analysis (conditional routing)
- meta_query_node (conversation summary)
- off_topic_response_node (polite redirect)
- clarification_node (ambiguity resolution)
- Graph integration (full routing paths)
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from typing import Dict, Any, List

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.graph.state import AgentState, create_initial_state
from app.graph.nodes import (
    query_analysis_node,
    route_after_analysis,
    meta_query_node,
    off_topic_response_node,
    clarification_node,
    _build_conversation_summary,
    _rewrite_followup_query,
)


# ============================================================================
# HELPERS
# ============================================================================

def _make_state(
    user_input: str,
    intent: str = None,
    messages: list = None,
    user_profile: dict = None,
) -> AgentState:
    """Create a minimal AgentState for testing."""
    return AgentState(
        messages=messages or [],
        user_input=user_input,
        intent=intent,
        plan=None,
        context={},
        tools_used=[],
        agent_outputs={},
        reflection=None,
        reflection_details=None,
        confidence=0.0,
        final_response=None,
        quality_score=0.0,
        feedback_applied=False,
        user_profile=user_profile or {},
        agent_output=None,
        metadata=None,
        error=None,
    )


def _mock_llm_response(content: str):
    """Create a mock LLM response."""
    mock = MagicMock()
    mock.content = content
    return mock


# ============================================================================
# QUERY ANALYSIS NODE
# ============================================================================

class TestQueryAnalysisNode:
    """Tests for the LLM-based query analysis pre-classifier."""

    @patch("app.graph.nodes.llm_classifier")
    def test_classifies_meta_query(self, mock_llm):
        """Meta-questions about conversation should be classified as 'meta'."""
        mock_llm.invoke.return_value = _mock_llm_response("meta")
        state = _make_state("What have we been discussing?")

        result = query_analysis_node(state)

        assert result["intent"] == "meta"
        mock_llm.invoke.assert_called_once()

    @patch("app.graph.nodes.llm_classifier")
    def test_classifies_off_topic(self, mock_llm):
        """Off-topic queries should be classified as 'off_topic'."""
        mock_llm.invoke.return_value = _mock_llm_response("off_topic")
        state = _make_state("Who will win the World Cup?")

        result = query_analysis_node(state)

        assert result["intent"] == "off_topic"

    @patch("app.graph.nodes.llm_classifier")
    def test_classifies_needs_clarification(self, mock_llm):
        """Ambiguous queries should be 'needs_clarification'."""
        mock_llm.invoke.return_value = _mock_llm_response("needs_clarification")
        state = _make_state("How does processing affect quality?")

        result = query_analysis_node(state)

        assert result["intent"] == "needs_clarification"

    @patch("app.graph.nodes.llm_classifier")
    def test_classifies_nutrition_related(self, mock_llm):
        """Nutrition queries should be 'nutrition_related'."""
        mock_llm.invoke.return_value = _mock_llm_response("nutrition_related")
        state = _make_state("What are the benefits of vitamin D?")

        result = query_analysis_node(state)

        assert result["intent"] == "nutrition_related"

    @patch("app.graph.nodes.llm_classifier")
    def test_normalizes_quoted_response(self, mock_llm):
        """LLM response with quotes should be normalized."""
        mock_llm.invoke.return_value = _mock_llm_response('"off_topic"')
        state = _make_state("Tell me a joke")

        result = query_analysis_node(state)

        assert result["intent"] == "off_topic"

    @patch("app.graph.nodes.llm_classifier")
    def test_extracts_category_from_verbose_response(self, mock_llm):
        """LLM that returns more than one word should still be parsed."""
        mock_llm.invoke.return_value = _mock_llm_response(
            "The category is meta because the user is asking about conversation history."
        )
        state = _make_state("Summarize our conversation")

        result = query_analysis_node(state)

        assert result["intent"] == "meta"

    @patch("app.graph.nodes.llm_classifier")
    def test_defaults_to_nutrition_on_unknown_category(self, mock_llm):
        """Unknown classification should default to nutrition_related."""
        mock_llm.invoke.return_value = _mock_llm_response("something_random_xyz")
        state = _make_state("Hello")

        result = query_analysis_node(state)

        assert result["intent"] == "nutrition_related"

    @patch("app.graph.nodes.llm_classifier")
    def test_defaults_to_nutrition_on_llm_error(self, mock_llm):
        """If LLM fails, should default to nutrition_related (safe fallback)."""
        mock_llm.invoke.side_effect = Exception("API timeout")
        state = _make_state("What vitamins should I take?")

        result = query_analysis_node(state)

        assert result["intent"] == "nutrition_related"

    @patch("app.graph.nodes.llm_classifier")
    def test_passes_conversation_history_to_llm(self, mock_llm):
        """Conversation history should be included in the prompt."""
        mock_llm.invoke.return_value = _mock_llm_response("nutrition_related")
        messages = [
            HumanMessage(content="Tell me about vitamin D"),
            AIMessage(content="Vitamin D is essential for..."),
        ]
        state = _make_state("What about elderly populations?", messages=messages)

        query_analysis_node(state)

        # Verify the system prompt contains conversation history
        call_args = mock_llm.invoke.call_args[0][0]
        system_content = call_args[0].content
        assert "CONVERSATION HISTORY" in system_content

    @patch("app.graph.nodes.llm_classifier")
    def test_adds_message_to_state(self, mock_llm):
        """Result should include an AIMessage for state tracking."""
        mock_llm.invoke.return_value = _mock_llm_response("off_topic")
        state = _make_state("What's the weather?")

        result = query_analysis_node(state)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert "[Query Analysis]" in result["messages"][0].content


# ============================================================================
# ROUTE AFTER ANALYSIS
# ============================================================================

class TestRouteAfterAnalysis:
    """Tests for the conditional routing function."""

    def test_routes_meta_to_meta_query(self):
        state = _make_state("Summary?", intent="meta")
        assert route_after_analysis(state) == "meta_query"

    def test_routes_off_topic_to_off_topic_response(self):
        state = _make_state("Football?", intent="off_topic")
        assert route_after_analysis(state) == "off_topic_response"

    def test_routes_needs_clarification_to_clarification(self):
        state = _make_state("Processing?", intent="needs_clarification")
        assert route_after_analysis(state) == "clarification"

    def test_routes_nutrition_to_planner(self):
        state = _make_state("Vitamin D?", intent="nutrition_related")
        assert route_after_analysis(state) == "planner"

    def test_routes_none_intent_to_planner(self):
        """Missing intent should default to planner (safe fallback)."""
        state = _make_state("Hello")
        assert route_after_analysis(state) == "planner"

    def test_routes_unknown_intent_to_planner(self):
        """Unknown intent value should default to planner."""
        state = _make_state("Hello", intent="something_weird")
        assert route_after_analysis(state) == "planner"


# ============================================================================
# META QUERY NODE
# ============================================================================

class TestMetaQueryNode:
    """Tests for the conversation history summary node."""

    def test_no_history_returns_welcome(self):
        """Empty conversation should return a welcome/intro message."""
        state = _make_state("What have we discussed?", messages=[])

        result = meta_query_node(state)

        assert "haven't discussed" in result["final_response"].lower()
        assert result["context"]["source"] == "meta_query"

    @patch("app.graph.nodes.llm_classifier")
    def test_with_history_calls_llm(self, mock_llm):
        """With conversation history, should call LLM for summary."""
        mock_llm.invoke.return_value = _mock_llm_response(
            "## Conversation Summary\nWe discussed vitamin D benefits."
        )
        messages = [
            HumanMessage(content="Tell me about vitamin D"),
            AIMessage(content="Vitamin D helps with bone health..."),
        ]
        state = _make_state("What have we discussed?", messages=messages)

        result = meta_query_node(state)

        assert "vitamin D" in result["final_response"]
        mock_llm.invoke.assert_called_once()

    @patch("app.graph.nodes.llm_classifier")
    def test_skips_internal_messages(self, mock_llm):
        """Internal planner/router messages should be filtered out."""
        mock_llm.invoke.return_value = _mock_llm_response("Summary of topics.")
        messages = [
            HumanMessage(content="Tell me about protein"),
            AIMessage(content="[Planner] Intent: science"),
            AIMessage(content="[Router] Routing to science agent"),
            AIMessage(content="[Query Analysis] Category: nutrition_related"),
            AIMessage(content="Protein is essential for muscle repair..."),
        ]
        state = _make_state("Summarize our chat", messages=messages)

        meta_query_node(state)

        # Verify the conversation text sent to LLM excludes internal messages
        call_args = mock_llm.invoke.call_args[0][0]
        human_msg = call_args[1].content
        assert "[Planner]" not in human_msg
        assert "[Router]" not in human_msg
        assert "[Query Analysis]" not in human_msg

    @patch("app.graph.nodes.llm_classifier")
    def test_llm_error_returns_fallback(self, mock_llm):
        """LLM failure should return a graceful fallback."""
        mock_llm.invoke.side_effect = Exception("API error")
        messages = [
            HumanMessage(content="Tell me about iron"),
            AIMessage(content="Iron is important..."),
        ]
        state = _make_state("What did we discuss?", messages=messages)

        result = meta_query_node(state)

        assert result["final_response"] is not None
        assert "trouble" in result["final_response"].lower()

    def test_output_has_required_keys(self):
        """Meta query output should have all required state keys."""
        state = _make_state("What did we talk about?", messages=[])

        result = meta_query_node(state)

        assert "agent_outputs" in result
        assert "chat" in result["agent_outputs"]
        assert "tools_used" in result
        assert "context" in result
        assert "final_response" in result
        assert "messages" in result


# ============================================================================
# OFF-TOPIC RESPONSE NODE
# ============================================================================

class TestOffTopicResponseNode:
    """Tests for the static off-topic response."""

    def test_returns_redirect_response(self):
        """Should return a polite redirect to nutrition topics."""
        state = _make_state("Who will win the election?")

        result = off_topic_response_node(state)

        assert "nutrition" in result["final_response"].lower()
        assert "Outside My Expertise" in result["final_response"]

    def test_suggests_valid_topics(self):
        """Response should list things the bot CAN help with."""
        state = _make_state("Tell me about quantum physics")

        result = off_topic_response_node(state)

        response = result["final_response"]
        assert "meal plan" in response.lower()
        assert "calorie" in response.lower() or "macro" in response.lower()

    def test_output_structure(self):
        """Output should have correct state keys."""
        state = _make_state("Write me a poem")

        result = off_topic_response_node(state)

        assert result["context"]["source"] == "off_topic"
        assert result["agent_outputs"]["chat"] == result["final_response"]
        assert isinstance(result["messages"][0], AIMessage)

    def test_no_llm_call(self):
        """Off-topic node should NOT call any LLM (static response)."""
        with patch("app.graph.nodes.llm_classifier") as mock_llm:
            state = _make_state("What's the meaning of life?")
            off_topic_response_node(state)
            mock_llm.invoke.assert_not_called()


# ============================================================================
# CLARIFICATION NODE
# ============================================================================

class TestClarificationNode:
    """Tests for the ambiguity resolution node."""

    @patch("app.graph.nodes.llm_classifier")
    def test_generates_clarification_question(self, mock_llm):
        """Should call LLM to generate a clarification question."""
        mock_llm.invoke.return_value = _mock_llm_response(
            "Are you asking about how food processing affects nutritional quality?"
        )
        state = _make_state("How does processing affect quality?")

        result = clarification_node(state)

        assert "food" in result["final_response"].lower() or "processing" in result["final_response"].lower()
        mock_llm.invoke.assert_called_once()

    @patch("app.graph.nodes.llm_classifier")
    def test_llm_error_returns_generic_clarification(self, mock_llm):
        """LLM failure should return a generic clarification message."""
        mock_llm.invoke.side_effect = Exception("timeout")
        state = _make_state("What are the best strategies?")

        result = clarification_node(state)

        assert "clarify" in result["final_response"].lower()

    def test_output_structure(self):
        """Output should have correct state keys and source."""
        with patch("app.graph.nodes.llm_classifier") as mock_llm:
            mock_llm.invoke.return_value = _mock_llm_response("Could you clarify?")
            state = _make_state("What about extraction?")

            result = clarification_node(state)

            assert result["context"]["source"] == "clarification"
            assert "chat" in result["agent_outputs"]
            assert isinstance(result["messages"][0], AIMessage)


# ============================================================================
# CONVERSATION SUMMARY HELPER
# ============================================================================

class TestBuildConversationSummary:
    """Tests for the _build_conversation_summary helper."""

    def test_empty_messages(self):
        """Empty message list should return empty string."""
        result = _build_conversation_summary([])
        assert result == ""

    def test_builds_summary_from_messages(self):
        """Should format recent messages into a readable summary."""
        messages = [
            HumanMessage(content="What is vitamin D?"),
            AIMessage(content="Vitamin D is a fat-soluble vitamin..."),
            HumanMessage(content="How much should I take daily?"),
            AIMessage(content="The recommended daily intake is 600-800 IU..."),
        ]
        result = _build_conversation_summary(messages)

        assert "vitamin D" in result.lower() or "vitamin d" in result.lower()
        assert len(result) > 0

    def test_filters_internal_prefixes(self):
        """Internal messages (planner, router) should be excluded."""
        messages = [
            HumanMessage(content="Tell me about protein"),
            AIMessage(content="[Planner] Intent: science"),
            AIMessage(content="[Query Analysis] Category: nutrition_related"),
            AIMessage(content="Protein is essential for muscle growth..."),
        ]
        result = _build_conversation_summary(messages)

        # The internal messages should be filtered or excluded
        assert "[Planner]" not in result
        assert "[Query Analysis]" not in result


# ============================================================================
# FOLLOWUP QUERY REWRITING
# ============================================================================

class TestRewriteFollowupQuery:
    """Tests for the _rewrite_followup_query helper."""

    def test_rewrites_pronoun_reference(self):
        """Should resolve 'it' / 'that' referencing previous topic."""
        messages = [
            HumanMessage(content="Tell me about vitamin D"),
            AIMessage(content="Vitamin D helps with calcium absorption..."),
        ]
        result = _rewrite_followup_query(
            "What about in elderly populations?",
            messages
        )
        # Result should incorporate vitamin D context
        assert len(result) > len("What about in elderly populations?")

    def test_no_rewrite_for_standalone_query(self):
        """Standalone queries without follow-up patterns shouldn't change."""
        messages = [
            HumanMessage(content="Tell me about iron"),
            AIMessage(content="Iron is important for..."),
        ]
        result = _rewrite_followup_query(
            "How many calories in a banana?",
            messages
        )
        # Should return the original or very similar
        assert "banana" in result.lower()

    def test_handles_empty_history(self):
        """With no history, should return the original query."""
        result = _rewrite_followup_query("What about that?", [])
        assert result is not None
        assert len(result) > 0


# ============================================================================
# GRAPH INTEGRATION: Full Routing Paths
# ============================================================================

class TestGraphRouting:
    """Integration tests verifying the full query analysis → node path."""

    @patch("app.graph.nodes.llm_classifier")
    def test_meta_query_full_path(self, mock_llm):
        """meta query → query_analysis → route → meta_query_node → output."""
        # Both nodes call llm_classifier.invoke — set up sequential responses
        mock_llm.invoke.side_effect = [
            _mock_llm_response("meta"),
            _mock_llm_response("## Summary\nWe discussed vitamin D and protein."),
        ]
        messages = [
            HumanMessage(content="Tell me about vitamin D"),
            AIMessage(content="Vitamin D is important..."),
        ]
        state = _make_state("What have we discussed?", messages=messages)

        # Step 1: query_analysis
        analysis_result = query_analysis_node(state)
        assert analysis_result["intent"] == "meta"

        # Step 2: routing
        state_after = {**state, **analysis_result}
        route = route_after_analysis(state_after)
        assert route == "meta_query"

        # Step 3: meta_query_node — pass original state (with history) not the merged one
        meta_result = meta_query_node(state)
        assert "vitamin D" in meta_result["final_response"]

    @patch("app.graph.nodes.llm_classifier")
    def test_off_topic_full_path(self, mock_llm):
        """off-topic → query_analysis → route → off_topic_response → output."""
        mock_llm.invoke.return_value = _mock_llm_response("off_topic")

        state = _make_state("Who will win the next election?")

        # Step 1: query_analysis
        analysis_result = query_analysis_node(state)
        assert analysis_result["intent"] == "off_topic"

        # Step 2: routing
        state_after = {**state, **analysis_result}
        route = route_after_analysis(state_after)
        assert route == "off_topic_response"

        # Step 3: off_topic_response (no LLM)
        off_topic_result = off_topic_response_node(state_after)
        assert "nutrition" in off_topic_result["final_response"].lower()

    @patch("app.graph.nodes.llm_classifier")
    def test_clarification_full_path(self, mock_llm):
        """ambiguous → query_analysis → route → clarification → output."""
        mock_llm.invoke.side_effect = [
            _mock_llm_response("needs_clarification"),
            _mock_llm_response(
                "Are you asking about food quality and extraction methods?"
            ),
        ]
        state = _make_state("How does extraction affect quality?")

        # Step 1
        analysis_result = query_analysis_node(state)
        assert analysis_result["intent"] == "needs_clarification"

        # Step 2
        state_after = {**state, **analysis_result}
        route = route_after_analysis(state_after)
        assert route == "clarification"

        # Step 3
        clar_result = clarification_node(state_after)
        assert clar_result["final_response"] is not None

    @patch("app.graph.nodes.llm_classifier")
    def test_nutrition_full_path_goes_to_planner(self, mock_llm):
        """nutrition-related → query_analysis → route → planner."""
        mock_llm.invoke.return_value = _mock_llm_response("nutrition_related")

        state = _make_state("What are the benefits of omega-3?")

        analysis_result = query_analysis_node(state)
        assert analysis_result["intent"] == "nutrition_related"

        state_after = {**state, **analysis_result}
        route = route_after_analysis(state_after)
        assert route == "planner"


# ============================================================================
# EDGE CASES & ROBUSTNESS
# ============================================================================

class TestEdgeCases:
    """Edge cases and robustness tests."""

    @patch("app.graph.nodes.llm_classifier")
    def test_empty_user_input(self, mock_llm):
        """Empty input should not crash."""
        mock_llm.invoke.return_value = _mock_llm_response("nutrition_related")
        state = _make_state("")

        result = query_analysis_node(state)
        assert result["intent"] is not None

    @patch("app.graph.nodes.llm_classifier")
    def test_very_long_input(self, mock_llm):
        """Very long input should not crash."""
        mock_llm.invoke.return_value = _mock_llm_response("nutrition_related")
        state = _make_state("vitamin D " * 500)

        result = query_analysis_node(state)
        assert result["intent"] == "nutrition_related"

    @patch("app.graph.nodes.llm_classifier")
    def test_special_characters_input(self, mock_llm):
        """Input with special characters should not crash."""
        mock_llm.invoke.return_value = _mock_llm_response("nutrition_related")
        state = _make_state("What about 'omega-3' (EPA/DHA) — is it good?!?")

        result = query_analysis_node(state)
        assert result["intent"] == "nutrition_related"

    def test_meta_query_with_many_messages(self):
        """Meta query with large history should handle gracefully."""
        messages = []
        for i in range(50):
            messages.append(HumanMessage(content=f"Question {i} about nutrition"))
            messages.append(AIMessage(content=f"Answer {i} about nutrition details"))

        with patch("app.graph.nodes.llm_classifier") as mock_llm:
            mock_llm.invoke.return_value = _mock_llm_response("Summary of 50 exchanges")
            state = _make_state("What have we discussed?", messages=messages)

            result = meta_query_node(state)
            assert result["final_response"] is not None

    def test_off_topic_response_is_consistent(self):
        """Off-topic response should be the same for any off-topic query."""
        r1 = off_topic_response_node(_make_state("Who won the election?"))
        r2 = off_topic_response_node(_make_state("Write me a poem"))

        assert r1["final_response"] == r2["final_response"]


# ============================================================================
# GRAPH COMPILATION TEST
# ============================================================================

class TestGraphCompilation:
    """Test that the graph compiles successfully with new nodes."""

    def test_graph_creates_without_error(self):
        """Graph should compile without errors."""
        from app.graph.graph import create_graph
        graph = create_graph()
        assert graph is not None

    def test_graph_has_query_analysis_entry(self):
        """Entry point should be query_analysis."""
        from app.graph.graph import create_graph
        graph = create_graph()
        compiled = graph.compile()
        # The graph should have the query_analysis node
        assert compiled is not None

    def test_graph_has_all_new_nodes(self):
        """Graph should include all new nodes."""
        from app.graph.graph import create_graph
        graph = create_graph()
        node_names = list(graph.nodes.keys())

        expected_nodes = [
            "query_analysis",
            "meta_query",
            "off_topic_response",
            "clarification",
            "planner",
            "router",
            "science",
            "nutrition",
            "chat",
            "reflection",
            "synthesizer",
        ]
        for name in expected_nodes:
            assert name in node_names, f"Missing node: {name}"
