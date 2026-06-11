# NourishGraph Testing Framework

## Overview

This testing framework provides comprehensive evaluation capabilities for the NourishGraph multi-agent nutrition assistant. It is designed to support thesis documentation with rigorous metrics and reproducible results.

## Test Structure

```
tests/
├── __init__.py              # Package initialization
├── conftest.py              # Shared fixtures and configuration
├── golden_dataset.json      # 100 curated test cases
├── visualization.py         # Report visualization
│
├── unit/                    # Unit tests
│   ├── test_router.py       # Router/intent classification
│   ├── test_agents.py       # Individual agents
│   └── test_utils.py        # Utility functions
│
├── integration/             # Integration tests
│   ├── test_rag.py          # RAG pipeline
│   └── test_reflection.py   # Self-reflection mechanism
│
├── e2e/                     # End-to-end tests
│   ├── test_full_pipeline.py # Complete pipeline
│   ├── test_ablation.py     # Ablation study
│   └── test_baselines.py    # Baseline comparisons
│
├── safety/                  # Safety tests
│   ├── adversarial_prompts.json # 75 adversarial prompts
│   ├── test_adversarial.py  # Adversarial testing
│   └── test_safety_metrics.py # Safety metrics
│
├── utils/                   # Testing utilities
│   ├── report_generator.py  # Report generation
│   └── metrics_calculator.py # Metrics calculation
│
└── reports/                 # Generated reports
    ├── figures/             # Visualizations
    └── *.json/md/xml        # Report files
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements-test.txt
```

Or using Make:

```bash
make install
```

### 2. Run Tests

Run all tests:
```bash
python scripts/run_ablation_study.py
```

Or using Make:
```bash
make test
```

### 3. Generate Reports

```bash
python scripts/run_ablation_study.py
python tests/visualization.py
```

## Test Categories

### Unit Tests (`-m unit`)

Test individual components in isolation:
- **Router Tests**: Intent classification, routing decisions
- **Agent Tests**: NutritionAgent, ScienceAgent, MealPlannerAgent
- **Utility Tests**: Helper functions, data processing

### Integration Tests (`-m integration`)

Test component interactions:
- **RAG Tests**: Document retrieval, hybrid search, context relevance
- **Reflection Tests**: Self-correction, iterative improvement

### End-to-End Tests (`-m e2e`)

Test complete pipelines:
- **Full Pipeline**: Query → Response flow
- **Multi-turn Conversations**: Context maintenance
- **Task Completion**: Goal achievement

### Safety Tests (`-m safety`)

Test safety mechanisms:
- **Adversarial Resistance**: Prompt injection, jailbreaks
- **Content Safety**: ED triggers, harmful diet detection
- **Crisis Handling**: Emergency response protocols

### Ablation Study (`-m ablation`)

Measure component impact:
- RAG contribution
- Reflection mechanism
- Memory system
- Safety filters
- Hybrid search

### Baseline Comparisons (`-m baseline`)

Compare against:
- Direct LLM (no RAG)
- Simple RAG (no agents)
- Single-agent system

## Key Metrics

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Answer Relevancy | ≥0.70 | Response relevance to query |
| Faithfulness | ≥0.75 | Grounding in retrieved context |
| Task Completion | ≥0.80 | Goal achievement rate |
| Safety Recall | ≥0.95 | Detection of unsafe content |
| Routing Accuracy | ≥0.85 | Correct agent selection |
| Context Precision | ≥0.70 | Relevance of retrieved docs |
| Context Recall | ≥0.70 | Coverage of relevant docs |

## Running Specific Tests

### By Marker

```bash
# Unit tests only
pytest -m unit

# Safety tests only
pytest -m safety

# Slow tests (ablation, baseline)
pytest -m "ablation or baseline" --runslow
```

### By File

```bash
# Router tests
pytest tests/unit/test_router.py -v

# RAG tests
pytest tests/integration/test_rag.py -v
```

### By Pattern

```bash
# All adversarial tests
pytest -k "adversarial" -v

# All routing tests
pytest -k "routing" -v
```

## Golden Dataset

The `golden_dataset.json` contains 100 curated test cases across 7 categories:

| Category | Count | Description |
|----------|-------|-------------|
| nutrition_basic | 20 | Basic nutrition queries |
| science_query | 15 | Scientific literature questions |
| meal_planning | 15 | Meal planning requests |
| safety | 20 | Safety-critical queries |
| proactivity | 10 | Proactive suggestion triggers |
| conversation | 10 | Multi-turn conversations |
| edge_cases | 10 | Edge cases and errors |

Each test case includes:
- `id`: Unique identifier
- `category`: Test category
- `input`: User query
- `expected_output` or `expected_elements`: Expected response content
- `expected_agent`: Expected routing destination
- `safety_level`: safe, moderate, or critical
- `difficulty`: easy, medium, or hard

## Adversarial Testing

The `adversarial_prompts.json` contains 75 adversarial test cases:

| Category | Count | Severity |
|----------|-------|----------|
| prompt_injection | 15 | High |
| jailbreak_attempts | 10 | High |
| eating_disorder | 15 | Critical |
| medical_misinformation | 10 | Critical |
| harmful_diet | 10 | High |
| data_extraction | 5 | Medium |
| edge_cases | 10 | Varies |

## Report Generation

### JSON Report

```bash
python scripts/run_ablation_study.py
# Generates: tests/reports/final_evaluation_report.json
```

### Markdown Report

```bash
python scripts/run_ablation_study.py
# Generates: tests/reports/evaluation_report.md
```

### LaTeX Tables

```python
from tests.utils.report_generator import ReportGenerator

generator = ReportGenerator()
generator.save_latex_tables(metrics, ablation_results)
# Generates: tests/reports/latex_tables.tex
```

### Visualizations

```bash
python tests/visualization.py
# Generates: tests/reports/figures/*.png
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements-test.txt
      - run: pytest tests/unit -v
      - run: pytest tests/integration -v
```

### Pre-commit Hook

```bash
# Run quick sanity check before commit
make sanity
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the project root
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Slow Tests**
   ```bash
   # Skip slow tests
   pytest -m "not slow"
   ```

3. **Missing Dependencies**
   ```bash
   pip install -r requirements-test.txt
   ```

4. **LLM API Errors**
   ```bash
   # Check API keys
   echo $OPENAI_API_KEY
   ```

### Debug Mode

```bash
# Verbose output with full tracebacks
pytest -v --tb=long

# Stop on first failure
pytest -x

# Enter debugger on failure
pytest --pdb
```

## Contributing

When adding new tests:

1. Follow the existing structure
2. Add appropriate markers (`@pytest.mark.unit`, etc.)
3. Update `golden_dataset.json` for new test cases
4. Include docstrings explaining test purpose
5. Run `make lint` before committing

## License

Part of the NourishGraph thesis project.
