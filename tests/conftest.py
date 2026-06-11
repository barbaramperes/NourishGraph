"""
Pytest configuration and shared fixtures for NourishGraph testing.

This module provides:
- Golden dataset loading
- System initialization
- LLM-as-Judge configuration
- Safety dataset loading
- Metric helpers
"""

import pytest
import json
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line("markers", "integration: Integration tests for RAG and multi-agent")
    config.addinivalue_line("markers", "e2e: End-to-end pipeline tests")
    config.addinivalue_line("markers", "safety: Safety and adversarial tests")
    config.addinivalue_line("markers", "ablation: Ablation study tests")
    config.addinivalue_line("markers", "baseline: Baseline comparison tests")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers."""
    # Skip slow tests unless explicitly requested
    if not config.getoption("--runslow", default=False):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run slow tests"
    )
    parser.addoption(
        "--model",
        action="store",
        default="gpt-4o-mini",
        help="LLM model to use for testing"
    )


# ============================================================================
# FIXTURES - DATASETS
# ============================================================================

@pytest.fixture(scope="session")
def golden_dataset() -> Dict[str, Any]:
    """Load the golden dataset for evaluation."""
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    
    if not dataset_path.exists():
        pytest.skip("Golden dataset not found")
    
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def test_cases(golden_dataset) -> List[Dict[str, Any]]:
    """Extract test cases from golden dataset."""
    return golden_dataset.get("test_cases", [])


@pytest.fixture(scope="session")
def safety_test_cases(test_cases) -> List[Dict[str, Any]]:
    """Extract safety-related test cases."""
    return [tc for tc in test_cases if tc.get("category") == "safety"]


@pytest.fixture(scope="session")
def nutrition_test_cases(test_cases) -> List[Dict[str, Any]]:
    """Extract nutrition-related test cases."""
    return [tc for tc in test_cases if tc.get("category") == "nutrition_basic"]


@pytest.fixture(scope="session")
def science_test_cases(test_cases) -> List[Dict[str, Any]]:
    """Extract science query test cases."""
    return [tc for tc in test_cases if tc.get("category") == "science_query"]


@pytest.fixture(scope="session")
def meal_planning_test_cases(test_cases) -> List[Dict[str, Any]]:
    """Extract meal planning test cases."""
    return [tc for tc in test_cases if tc.get("category") == "meal_planning"]


@pytest.fixture(scope="session")
def adversarial_prompts() -> List[Dict[str, Any]]:
    """Load adversarial prompts for safety testing."""
    prompts_path = Path(__file__).parent / "safety" / "adversarial_prompts.json"
    
    if not prompts_path.exists():
        return []
    
    with open(prompts_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Return the prompts list, not the whole JSON
        return data.get("prompts", [])


# ============================================================================
# FIXTURES - SYSTEM COMPONENTS
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def nourishgraph():
    """Initialize NourishGraph system for testing."""
    try:
        from app.graph.graph import create_graph
        graph = create_graph()
        # Compile the graph to get a runnable with invoke() method
        compiled_graph = graph.compile()
        return compiled_graph
    except ImportError as e:
        pytest.skip(f"Could not import NourishGraph: {e}")
    except Exception as e:
        pytest.skip(f"Could not create graph: {e}")


@pytest.fixture(scope="session")
def router():
    """Initialize the router component."""
    try:
        from app.agents.router import IntentRouter
        return IntentRouter()
    except ImportError:
        pytest.skip("Router not available")


@pytest.fixture(scope="session")
def safety_checker():
    """Initialize the safety checker component."""
    try:
        from app.safety.safety_checker import SafetyChecker
        return SafetyChecker()
    except ImportError:
        pytest.skip("Safety checker not available")


@pytest.fixture(scope="session")
def nutrition_agent():
    """Initialize the nutrition agent."""
    try:
        from app.agents.nutrition_agent import NutritionAgent
        return NutritionAgent()
    except ImportError:
        pytest.skip("Nutrition agent not available")


@pytest.fixture(scope="session")
def science_agent():
    """Initialize the science agent."""
    try:
        from app.agents.science_agent import ScienceAgent
        return ScienceAgent()
    except ImportError:
        pytest.skip("Science agent not available")


@pytest.fixture(scope="session")
def rag_system():
    """Initialize the RAG system (returns the module with hybrid search functions)."""
    try:
        from app import rag_hybrid
        # Return the module itself - it has hybrid_search, get_stats, etc.
        return rag_hybrid
    except ImportError:
        pytest.skip("RAG system not available")


# ============================================================================
# FIXTURES - LLM JUDGE
# ============================================================================

@pytest.fixture(scope="session")
def llm_judge(request):
    """Initialize LLM-as-Judge evaluator."""
    model = request.config.getoption("--model")
    
    try:
        from deepeval.models import GPTModel
        return GPTModel(model=model)
    except ImportError:
        pytest.skip("DeepEval not available")


@pytest.fixture(scope="session")
def evaluator_config() -> Dict[str, Any]:
    """Configuration for evaluation metrics."""
    return {
        "answer_relevancy_threshold": 0.70,
        "faithfulness_threshold": 0.75,
        "task_completion_threshold": 0.80,
        "safety_recall_threshold": 0.95,
        "routing_accuracy_threshold": 0.85,
        "context_precision_threshold": 0.70,
        "context_recall_threshold": 0.70,
    }


# ============================================================================
# FIXTURES - HELPERS
# ============================================================================

@pytest.fixture
def mock_user_context() -> Dict[str, Any]:
    """Create a mock user context for testing."""
    return {
        "user_id": 1,
        "name": "Test User",
        "age": 30,
        "weight": 70,
        "height": 175,
        "goal": "weight_loss",
        "dietary_restrictions": [],
        "allergies": [],
        "activity_level": "moderate",
    }


@pytest.fixture
def mock_conversation_history() -> List[Dict[str, str]]:
    """Create mock conversation history."""
    return [
        {"role": "user", "content": "Hi, I want to eat healthier"},
        {"role": "assistant", "content": "Great! I can help you with that. What are your main nutrition goals?"},
        {"role": "user", "content": "I want to lose weight and have more energy"},
    ]


@pytest.fixture
def test_report_path(tmp_path) -> Path:
    """Create a temporary path for test reports."""
    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


# ============================================================================
# FIXTURES - METRICS
# ============================================================================

@pytest.fixture
def metrics_collector():
    """Create a metrics collector for test results."""
    
    class MetricsCollector:
        def __init__(self):
            self.results = []
            self.start_time = datetime.now()
        
        def add_result(self, test_id: str, category: str, passed: bool, 
                       metrics: Dict[str, float], details: Optional[str] = None):
            self.results.append({
                "test_id": test_id,
                "category": category,
                "passed": passed,
                "metrics": metrics,
                "details": details,
                "timestamp": datetime.now().isoformat()
            })
        
        def get_summary(self) -> Dict[str, Any]:
            total = len(self.results)
            passed = sum(1 for r in self.results if r["passed"])
            
            by_category = {}
            for r in self.results:
                cat = r["category"]
                if cat not in by_category:
                    by_category[cat] = {"total": 0, "passed": 0}
                by_category[cat]["total"] += 1
                if r["passed"]:
                    by_category[cat]["passed"] += 1
            
            return {
                "total_tests": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": passed / total if total > 0 else 0,
                "by_category": by_category,
                "duration": (datetime.now() - self.start_time).total_seconds()
            }
        
        def save_report(self, path: Path):
            report = {
                "summary": self.get_summary(),
                "results": self.results,
                "generated_at": datetime.now().isoformat()
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
    
    return MetricsCollector()


# ============================================================================
# ASYNC HELPERS
# ============================================================================

@pytest.fixture
def run_async():
    """Helper to run async functions in sync tests."""
    def _run(coro):
        return asyncio.get_event_loop().run_until_complete(coro)
    return _run


# ============================================================================
# MOCKING FIXTURES
# ============================================================================

@pytest.fixture
def mock_openai():
    """Mock OpenAI ChatOpenAI for testing without API key."""
    with patch('langchain_openai.ChatOpenAI') as mock_llm_class:
        mock_instance = MagicMock()

        # Default response for router/planner
        mock_instance.invoke.return_value = Mock(
            content='{"intent": "chat", "confidence": 0.9, "plan": ["Step 1: Respond"], "thinking": "User is asking a general question"}'
        )

        mock_llm_class.return_value = mock_instance
        yield mock_llm_class
        # Cleanup after test
        mock_llm_class.reset_mock()
        mock_instance.reset_mock()


@pytest.fixture
def mock_rag_search():
    """Mock RAG hybrid search for testing without Pinecone."""
    with patch('app.rag_hybrid.hybrid_search') as mock_search:
        # Default: return 2 mock papers
        mock_search.return_value = [
            {
                "id": "paper1",
                "title": "Nutrition and Health: A Comprehensive Review",
                "authors": "Smith et al.",
                "year": 2020,
                "text": "This study examines the relationship between nutrition and health outcomes.",
                "score": 0.95
            },
            {
                "id": "paper2",
                "title": "Dietary Interventions for Weight Management",
                "authors": "Jones et al.",
                "year": 2021,
                "text": "We investigated the effectiveness of various dietary interventions.",
                "score": 0.88
            }
        ]
        yield mock_search


@pytest.fixture
def mock_search_tools():
    """Mock search tools to avoid RAG calls."""
    with patch('app.tools.search_tools.clear_last_search_results'):
        with patch('app.tools.search_tools.get_last_search_results') as mock_get:
            mock_get.return_value = [
                {
                    "title": "Mock Paper 1",
                    "authors": "Test et al.",
                    "year": 2022,
                    "abstract": "Mock abstract content"
                }
            ]
            yield mock_get


# ============================================================================
# ENVIRONMENT CHECK (Disabled - individual tests handle this)
# ============================================================================

# Note: Environment checking is now done at the individual test level
# using @pytest.mark.skipif(not has_api_key(), reason="...")
# This allows structure/file tests to pass without API key.

