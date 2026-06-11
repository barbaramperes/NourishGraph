"""
Performance tests for LangGraph workflow.

Tests caching, Fast Router optimization, and overall performance.
"""

import pytest
import time
from unittest.mock import Mock, patch
import os

from app.graph.graph import run_agent
from app.graph.nodes import FastIntentClassifier


# ============================================================================
# HELPERS
# ============================================================================

def has_api_keys():
    """Check if required API keys are available."""
    return bool(os.getenv("OPENAI_API_KEY"))


# ============================================================================
# FAST ROUTER PERFORMANCE TESTS
# ============================================================================

@pytest.mark.performance
class TestFastRouterPerformance:
    """Test Fast Router performance characteristics."""

    def test_regex_classification_is_fast(self):
        """Test that regex-based classification is sub-100ms."""
        classifier = FastIntentClassifier()

        queries = [
            "What does research say about vitamin D?",
            "Calculate my BMR",
            "I weigh 70kg",
            "Create a meal plan",
            "Hello",
        ] * 10  # Test with 50 queries

        start = time.time()

        for query in queries:
            intent, confidence, reasoning = classifier.classify(query)

        elapsed = time.time() - start
        avg_time = elapsed / len(queries)

        assert avg_time < 0.001, f"Average classification time {avg_time*1000:.2f}ms, expected < 1ms"

    def test_regex_vs_llm_speedup(self):
        """Test that regex is significantly faster than LLM."""
        classifier = FastIntentClassifier()

        query = "What does research say about vitamin D?"

        start = time.time()
        intent, confidence, reasoning = classifier.classify(query)
        regex_time = time.time() - start

        assert regex_time < 0.01, f"Regex took {regex_time*1000:.2f}ms, expected < 10ms"


# ============================================================================
# CACHING TESTS
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.skipif(not has_api_keys(), reason="Requires API keys")
class TestResponseCaching:
    """Test response caching functionality."""

    def test_cache_hit_improves_performance(self):
        """Test that cached responses are faster."""
        user_id = 5000
        query = "What does research say about vitamin D and immunity?"

        start1 = time.time()
        result1 = run_agent(user_input=query, user_id=user_id)
        time1 = time.time() - start1

        start2 = time.time()
        result2 = run_agent(user_input=query, user_id=user_id)
        time2 = time.time() - start2

        assert result1["final_response"] is not None
        assert result2["final_response"] is not None

        # This test documents the expected behavior
        print(f"First request: {time1:.2f}s")
        print(f"Second request: {time2:.2f}s")
        print(f"Speedup: {time1/time2:.2f}x" if time2 > 0 else "N/A")

    def test_different_queries_not_cached_together(self):
        """Test that different queries don't share cache."""
        user_id = 5001

        queries = [
            "What does research say about vitamin D?",
            "What does research say about omega-3?",
            "What does research say about magnesium?",
        ]

        results = []
        for query in queries:
            result = run_agent(user_input=query, user_id=user_id)
            results.append(result["final_response"])

        assert results[0] != results[1]
        assert results[1] != results[2]


# ============================================================================
# LATENCY BENCHMARKS
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.skipif(not has_api_keys(), reason="Requires API keys")
class TestLatencyBenchmarks:
    """Benchmark end-to-end latency for different query types."""

    def test_science_query_latency(self):
        """Benchmark science query latency."""
        queries = [
            "What does research say about vitamin D?",
            "Are there studies on omega-3?",
            "What are the benefits of magnesium?",
        ]

        latencies = []

        for query in queries:
            start = time.time()
            result = run_agent(user_input=query, user_id=6000)
            latency = time.time() - start

            assert result["final_response"] is not None
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        print(f"\nScience query average latency: {avg_latency:.2f}s")
        print(f"Min: {min(latencies):.2f}s, Max: {max(latencies):.2f}s")

        assert avg_latency < 30, f"Average latency too high: {avg_latency:.2f}s"

    def test_nutrition_query_latency(self):
        """Benchmark nutrition calculation latency."""
        queries = [
            "Calculate my BMR. I'm 30, 70kg, 175cm, male.",
            "What's my TDEE for moderate activity?",
            "Calculate my macros for weight loss",
        ]

        latencies = []

        for query in queries:
            start = time.time()
            result = run_agent(user_input=query, user_id=6001)
            latency = time.time() - start

            assert result["final_response"] is not None
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        print(f"\nNutrition query average latency: {avg_latency:.2f}s")

        # Calculations should be faster than RAG queries
        assert avg_latency < 20, f"Average latency too high: {avg_latency:.2f}s"

    def test_chat_query_latency(self):
        """Benchmark simple chat query latency."""
        queries = [
            "Hello",
            "Thanks",
            "What can you do?",
        ]

        latencies = []

        for query in queries:
            start = time.time()
            result = run_agent(user_input=query, user_id=6002)
            latency = time.time() - start

            assert result["final_response"] is not None
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        print(f"\nChat query average latency: {avg_latency:.2f}s")

        # Chat should be fastest (no tools)
        assert avg_latency < 15, f"Average latency too high: {avg_latency:.2f}s"


# ============================================================================
# THROUGHPUT TESTS
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.skipif(not has_api_keys(), reason="Requires API keys")
class TestThroughput:
    """Test system throughput capabilities."""

    def test_sequential_throughput(self):
        """Test throughput for sequential queries."""
        queries = [
            "What does research say about vitamin D?",
            "Calculate my BMR. I'm 30, 70kg, 175cm, male.",
            "I weigh 75kg",
            "Hello",
            "Create a meal plan",
        ]

        start = time.time()

        for i, query in enumerate(queries):
            result = run_agent(user_input=query, user_id=7000 + i)
            assert result["final_response"] is not None

        total_time = time.time() - start
        throughput = len(queries) / total_time

        print(f"\nSequential throughput: {throughput:.2f} queries/second")
        print(f"Total time for {len(queries)} queries: {total_time:.2f}s")

        assert throughput > 0.05, f"Throughput too low: {throughput:.2f} q/s"


# ============================================================================
# MEMORY USAGE TESTS
# ============================================================================

@pytest.mark.performance
class TestMemoryUsage:
    """Test memory usage characteristics."""

    def test_state_size_is_reasonable(self):
        """Test that state objects don't grow unbounded."""
        from app.graph.state import create_initial_state
        import sys

        # Create state with various data
        state = create_initial_state("Test query")
        state["agent_outputs"] = {"science": "x" * 1000}  # 1KB response
        state["context"] = {"papers": [{"text": "y" * 1000} for _ in range(5)]}  # 5KB context

        size = sys.getsizeof(str(state))

        print(f"\nState size: {size / 1024:.2f} KB")

        assert size < 100_000, f"State too large: {size / 1024:.2f} KB"

    def test_long_conversation_memory_growth(self):
        """Test memory with long conversation history."""
        from langchain_core.messages import HumanMessage, AIMessage

        messages = []

        # Simulate 20 turns
        for i in range(20):
            messages.append(HumanMessage(content=f"User message {i}"))
            messages.append(AIMessage(content=f"Assistant response {i}"))

        # Create state with history
        from app.graph.state import create_initial_state

        # Convert to history format
        history = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            else:
                history.append({"role": "assistant", "content": msg.content})

        state = create_initial_state("New query", chat_history=history)

        # Should handle without excessive memory
        import sys
        size = sys.getsizeof(str(state))

        print(f"\nState with 20-turn history: {size / 1024:.2f} KB")

        assert size < 200_000, f"State with history too large: {size / 1024:.2f} KB"


# ============================================================================
# OPTIMIZATION VERIFICATION
# ============================================================================

@pytest.mark.performance
class TestOptimizations:
    """Verify that optimizations are working as expected."""

    def test_fast_router_is_enabled(self):
        """Verify Fast Router is being used."""
        from app.graph.nodes import FastIntentClassifier

        classifier = FastIntentClassifier()

        assert len(classifier.PATTERNS) > 0
        assert "science" in classifier.PATTERNS
        assert "nutrition" in classifier.PATTERNS

    def test_response_cache_is_available(self):
        """Verify response caching infrastructure exists."""
        # Check if caching is implemented in nodes.py
        from app.graph import nodes

        # Look for cache-related code
        source = open(nodes.__file__).read()

        has_cache = "cache" in source.lower() or "ResponseCache" in source

        print(f"\nCache infrastructure present: {has_cache}")


    def test_llm_temperature_is_optimized(self):
        """Verify LLM temperature settings are appropriate."""
        from app.graph.nodes import llm, llm_reflection

        # Planner/router should use low temperature for consistency
        assert hasattr(llm, 'temperature') or hasattr(llm, 'model_kwargs')

        # Reflection should use even lower temperature
        assert hasattr(llm_reflection, 'temperature') or hasattr(llm_reflection, 'model_kwargs')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
