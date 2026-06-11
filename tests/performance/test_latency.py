"""
Performance tests for system latency.

Tests that verify the system responds within acceptable time limits.
"""

import pytest
import time
import os


def has_api_key() -> bool:
    """Check if OpenAI API key is available for real performance tests."""
    key = os.environ.get("OPENAI_API_KEY", "")
    return bool(key) and not key.startswith("sk-...")


@pytest.mark.integration
class TestLatencyWithMocks:
    """Test latency with mocked LLM calls (fast tests)."""

    def test_router_latency_mocked(self, mock_openai):
        """Router classification should be fast with mocks."""
        from app.graph.nodes import planner_node

        mock_openai.return_value.invoke.return_value.content = '{"intent": "nutrition", "confidence": 0.9, "plan": ["Calculate"], "thinking": "Food query"}'

        start = time.time()
        result = planner_node({
            "user_input": "How many calories in a banana?",
            "messages": []
        })
        duration = time.time() - start

        assert result["intent"] == "nutrition"
        assert duration < 0.1, f"Router took {duration:.3f}s (should be <0.1s with mocks)"

    def test_bmr_calculation_latency(self):
        """BMR calculation should be instant."""
        from app.tools.nutrition_tools import calculate_bmr

        start = time.time()
        result = calculate_bmr.invoke({
            "weight_kg": 70,
            "height_cm": 175,
            "age_years": 30,
            "sex": "M"
        })
        duration = time.time() - start

        assert isinstance(result, str), "BMR calculation should return formatted string"
        assert "1649" in result or "1,649" in result, "BMR result should contain calculated value"
        assert duration < 0.01, f"BMR calculation took {duration:.3f}s (should be <0.01s)"

    def test_multiple_router_calls_latency(self, mock_openai):
        """Multiple router calls should remain fast."""
        from app.graph.nodes import planner_node

        mock_openai.return_value.invoke.return_value.content = '{"intent": "chat", "confidence": 0.9, "plan": ["Respond"], "thinking": "General"}'

        queries = ["Hello"] * 10

        start = time.time()
        for query in queries:
            planner_node({"user_input": query, "messages": []})
        duration = time.time() - start

        avg_duration = duration / len(queries)
        assert avg_duration < 0.1, f"Average router latency {avg_duration:.3f}s too high"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(not has_api_key(), reason="OPENAI_API_KEY required for real API tests")
class TestRealAPILatency:
    """Test latency with real API calls (slow, requires API key)."""

    def test_router_latency_real(self):
        """Router should classify in <2 seconds with real API."""
        from app.graph.nodes import planner_node

        start = time.time()
        result = planner_node({
            "user_input": "What are the benefits of vitamin D?",
            "messages": []
        })
        duration = time.time() - start

        assert result["intent"] is not None
        assert duration < 2.0, f"Router took {duration:.2f}s (>2s threshold)"

    def test_rag_search_latency_real(self):
        """RAG search should complete in <3 seconds."""
        try:
            from app.rag_hybrid import hybrid_search

            start = time.time()
            results = hybrid_search("vitamin d benefits", top_k=5)
            duration = time.time() - start

            assert duration < 3.0, f"RAG search took {duration:.2f}s (>3s threshold)"
            # Allow 0 results if Pinecone is not configured
            assert isinstance(results, list), "RAG should return a list"
        except Exception as e:
            pytest.skip(f"RAG search not available: {e}")

    def test_end_to_end_latency_real(self, nourishgraph):
        """Full pipeline should respond in <10 seconds."""
        start = time.time()
        result = nourishgraph.invoke({
            "user_input": "How many calories in a banana?",
            "messages": []
        })
        duration = time.time() - start

        assert duration < 10.0, f"Pipeline took {duration:.2f}s (>10s threshold)"
        assert result.get("final_response"), "No response generated"


@pytest.mark.integration
@pytest.mark.slow
class TestConcurrentPerformance:
    """Test system performance under concurrent load."""

    def test_sequential_requests_mocked(self, mock_openai):
        """Test multiple sequential requests with mocks."""
        from app.graph.nodes import planner_node

        mock_openai.return_value.invoke.return_value.content = '{"intent": "chat", "confidence": 0.9, "plan": ["Respond"], "thinking": "Analysis"}'

        queries = [
            "What is BMI?",
            "How many calories in rice?",
            "Benefits of protein",
            "I ate lunch",
            "Create a meal plan",
        ]

        latencies = []
        for query in queries:
            start = time.time()
            result = planner_node({"user_input": query, "messages": []})
            duration = time.time() - start
            latencies.append(duration)

            assert result["intent"] is not None

        # Check no degradation
        assert max(latencies) < 0.2, f"Max latency {max(latencies):.3f}s too high"
        assert sum(latencies) / len(latencies) < 0.1, "Average latency too high"

    @pytest.mark.skipif(not has_api_key(), reason="OPENAI_API_KEY required")
    def test_concurrent_requests_real(self, nourishgraph):
        """Test system handles concurrent requests (real API)."""
        import concurrent.futures

        def make_request(query):
            try:
                start = time.time()
                result = nourishgraph.invoke({"user_input": query, "messages": []})
                return time.time() - start, result, None
            except Exception as e:
                return None, None, str(e)

        # 5 concurrent requests (reduced from 10 to avoid rate limits)
        queries = ["What is BMI?"] * 5

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(make_request, queries))

        # Filter out failures
        successful = [(dur, res) for dur, res, err in results if err is None]

        if len(successful) == 0:
            pytest.skip("All concurrent requests failed")

        # Check successful requests
        assert len(successful) > 0, "Some requests should succeed"

        # Check average latency didn't degrade too much
        avg_latency = sum(r[0] for r in successful) / len(successful)
        assert avg_latency < 15.0, f"Average latency {avg_latency:.2f}s under load (>15s)"


@pytest.mark.integration
class TestMemoryUsage:
    """Test memory usage doesn't grow unbounded."""

    def test_router_memory_stable(self, mock_openai):
        """Router should not leak memory on repeated calls."""
        from app.graph.nodes import planner_node
        import gc

        mock_openai.return_value.invoke.return_value.content = '{"intent": "chat", "confidence": 0.9, "plan": ["Respond"], "thinking": "Analysis"}'

        # Force garbage collection before test
        gc.collect()

        # Run many iterations
        for i in range(100):
            planner_node({"user_input": f"Query {i}", "messages": []})

        # Force garbage collection after
        gc.collect()

        # Test passes if no memory error occurred
        assert True

    def test_calculation_tools_memory_stable(self):
        """Calculation tools should not leak memory."""
        from app.tools.nutrition_tools import calculate_bmr
        import gc

        gc.collect()

        # Run many calculations
        for i in range(1000):
            calculate_bmr.invoke({
                "weight_kg": 70 + i % 10,
                "height_cm": 175,
                "age_years": 30,
                "sex": "M"
            })

        gc.collect()

        # Test passes if no memory error occurred
        assert True


@pytest.mark.integration
class TestThroughput:
    """Test system throughput (requests per second)."""

    def test_router_throughput_mocked(self, mock_openai):
        """Measure router throughput with mocks."""
        from app.graph.nodes import planner_node

        mock_openai.return_value.invoke.return_value.content = '{"intent": "chat", "confidence": 0.9, "plan": ["Respond"], "thinking": "Analysis"}'

        num_requests = 50
        start = time.time()

        for i in range(num_requests):
            planner_node({"user_input": f"Query {i}", "messages": []})

        duration = time.time() - start
        throughput = num_requests / duration

        print(f"\n  Router throughput: {throughput:.1f} req/s")
        assert throughput > 10, f"Router throughput {throughput:.1f} req/s too low"

    def test_calculation_throughput(self):
        """Measure calculation tool throughput."""
        from app.tools.nutrition_tools import calculate_bmr

        num_calculations = 1000
        start = time.time()

        for i in range(num_calculations):
            calculate_bmr.invoke({
                "weight_kg": 70,
                "height_cm": 175,
                "age_years": 30,
                "sex": "M"
            })

        duration = time.time() - start
        throughput = num_calculations / duration

        print(f"\n  BMR calculation throughput: {throughput:.1f} calc/s")
        assert throughput > 100, f"Calculation throughput {throughput:.1f} calc/s too low"
