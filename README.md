# NourishGraph

> **Architectural Governance for Safe and Evidence-Grounded Agentic AI in Nutrition — Master's Thesis, NOVA IMS**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-FF6B35?style=flat-square)](https://www.langchain.com/langgraph)
[![License](https://img.shields.io/badge/License-Academic-blue?style=flat-square)]()

---

## Overview

**NourishGraph** is an intelligent nutrition assistant that demonstrates multi-agent orchestration with LangGraph. The system provides personalized nutritional guidance grounded in scientific literature through a hybrid Retrieval-Augmented Generation (RAG) architecture, with healthcare-specific safety guardrails.

### Research Context

Developed as part of a **Master's thesis in Information Management at NOVA IMS** (Universidade Nova de Lisboa), exploring:

- **Agentic AI patterns** for health assistance
- **Multi-agent orchestration** with LangGraph (supervisor + specialized agents)
- **Hybrid RAG** (dense + sparse retrieval) over a scientific evidence corpus
- **Safety guardrails** for healthcare-adjacent applications
- **Evidence grading** (A/B/C/D classification by study type)

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Agent System** | 5 specialized agents plus intent classifier and citation validator, orchestrated by LangGraph |
| **Scientific RAG** | 88 peer-reviewed papers indexed with hybrid search (dense + sparse embeddings, Weighted Score Fusion, α = 0.7) |
| **Evidence Grading** | A/B/C/D classification based on study type |
| **Citation Validation** | Generated claims checked against retrieved sources |
| **Safety Guardrails** | Medical query blocking, input/output filtering, safety metrics |
| **Personalization** | BMR/TDEE calculations, dietary preferences, meal logging |
| **Real-time Streaming** | SSE-based response streaming |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                  │
│                      React + Vite + Zustand                         │
│                                                                     │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│   │  Chat   │  │Dashboard│  │  Meals  │  │ Profile │  │Settings │ │
│   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘ │
└────────┼────────────┼────────────┼────────────┼────────────┼───────┘
         │            │            │            │            │
         └────────────┴────────────┴────────────┴────────────┘
                                   │
                          REST API / SSE Streaming
                                   │
┌──────────────────────────────────┴──────────────────────────────────┐
│                            BACKEND                                  │
│                       FastAPI + LangGraph                           │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    INTENT CLASSIFIER                        │    │
│  │              (Safety check + Query routing)                 │    │
│  └─────────────────────────┬──────────────────────────────────┘    │
│                            │                                        │
│  ┌─────────────────────────┴──────────────────────────────────┐    │
│  │                   LANGGRAPH ORCHESTRATOR                    │    │
│  │                                                             │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │    │
│  │  │ Science  │  │Nutrition │  │ Profile  │  │   Meal   │   │    │
│  │  │  Agent   │  │  Agent   │  │  Agent   │  │ Planner  │   │    │
│  │  │  (RAG)   │  │  (Calc)  │  │  (CRUD)  │  │(Creative)│   │    │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │    │
│  │       │             │             │             │          │    │
│  └───────┴─────────────┴─────────────┴─────────────┴──────────┘    │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐    │
│  │   Safety    │  │   Memory    │  │     Chat Agent          │    │
│  │ Guardrails  │  │   Manager   │  │   (General queries)     │    │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    Pinecone     │  │   PostgreSQL    │  │     OpenAI      │
│   (88 papers)   │  │  (Users/Foods)  │  │  (GPT-4o-mini)  │
│  Hybrid Search  │  │   USDA Foods    │  │ Function Call   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Agents

| Agent | Role | Tools | Temperature |
|-------|------|-------|-------------|
| **ScienceAgent** | Scientific paper retrieval, evidence grading | `search_scientific_papers` | 0.1 |
| **NutritionAgent** | BMR, TDEE, macro calculations | `calculate_bmr`, `calculate_tdee` | 0.1 |
| **ProfileAgent** | User profile & meal management | `get_profile`, `save_profile`, `log_meal` | 0.2 |
| **MealPlannerAgent** | Personalized meal suggestions | `generate_meal_plan` | 0.6 |
| **ChatAgent** | General nutrition conversation | — | 0.5 |

A dedicated **CitationValidator** verifies that claims in generated answers are supported by the retrieved sources before they reach the user.

### Evidence Grading System

| Level | Description | Example |
|-------|-------------|---------|
| **A** | Multiple RCTs, meta-analyses | Cochrane systematic reviews |
| **B** | Single RCT, cohort studies | Well-designed prospective studies |
| **C** | Observational, case-control | Cross-sectional studies |
| **D** | Expert opinion, limited data | Case reports, theoretical |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite 5, Zustand, TailwindCSS, Lucide Icons |
| **Backend** | FastAPI, LangGraph, LangChain, Pydantic |
| **Database** | PostgreSQL (Neon), 1,086 USDA foods |
| **Vector Store** | Pinecone — 88 papers, hybrid dense–sparse search (WSF) |
| **LLM** | OpenAI GPT-4o-mini |
| **Auth** | JWT + Google Sign-In |
| **Hosting** | Railway |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (or [Neon](https://neon.tech) free tier)
- API keys: OpenAI, Pinecone

### Installation

```bash
# Clone repository
git clone https://github.com/barbaramperes/NourishGraph.git
cd NourishGraph

# Backend setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/base.txt

# Frontend setup
cd frontend && npm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

> **Note on the RAG corpus:** the 88 scientific papers are **not redistributed** in this
> repository for copyright reasons. See [`papers/README.md`](papers/README.md) for
> instructions on rebuilding the Pinecone index from your own licensed copies.

### Running

```bash
# Terminal 1 — Backend
source .venv/bin/activate
uvicorn app.api:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

### Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Create account |
| POST | `/auth/login` | Login (returns JWT) |
| POST | `/auth/google` | Google Sign-In |
| GET | `/auth/me` | Current user |
| POST | `/auth/forgot-password` | Request password reset |
| POST | `/auth/reset-password` | Reset password |

### Chat & Memory
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Send message to agent system |
| POST | `/chat/stream` | Streaming response (SSE) |
| GET | `/conversations` | List conversations |
| GET | `/history` | Conversation history |
| POST | `/memory/clear` | Clear conversation memory |

### Profile & Meals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST/DELETE | `/profile` | User profile |
| GET/POST/DELETE | `/meals` | Meal logging |
| GET | `/foods/search?q=` | Search USDA foods |
| GET | `/foods/nutrition` | Nutrition lookup |

### Observability & Safety
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service status |
| GET | `/stats` | System statistics |
| GET | `/metrics` | Runtime metrics |
| GET | `/safety/metrics` | Safety guardrail metrics |
| GET | `/safety/report` | Safety evaluation report |

Full interactive documentation at `/docs` (Swagger UI).

---

## Testing

The test suite is organized by level:

```
tests/
├── unit/           # Agents, routing, query analysis, security
├── integration/    # LangGraph workflow, RAG, reflection, response quality
├── e2e/            # Full pipeline, ablation, baselines
├── performance/    # Latency and LangGraph performance
├── safety/         # Adversarial prompts, safety metrics
└── golden_dataset.json
```

```bash
# Run all tests
pytest tests/ -v

# Run a specific level
pytest tests/unit -v
pytest tests/safety -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

---

## Safety & Guardrails

The system includes healthcare-specific safety measures with tracked metrics.

### Medical Query Blocking
Queries about medication dosages, drug interactions, and medical treatments are **blocked**:

```
# Blocked queries (examples):
"What is the correct insulin dosage?"  → Blocked
"Should I stop taking metformin?"      → Blocked
"Can I mix aspirin with warfarin?"     → Blocked
```

### Safe Nutrition Queries
Nutrition questions are processed normally:

```
# Allowed queries (examples):
"What foods are high in protein?"      → Processed
"How many calories should I eat?"      → Processed
"What does research say about fiber?"  → Processed with RAG
```

Adversarial robustness is evaluated with a dedicated prompt set (`tests/safety/adversarial_prompts.json`).

---

## Project Structure

```
NourishGraph/
├── app/
│   ├── api.py                 # FastAPI endpoints
│   ├── agents/                # Specialized agents
│   │   ├── base_agent.py      # ReAct pattern base class
│   │   ├── science_agent.py   # RAG + evidence grading
│   │   ├── nutrition_agent.py # BMR/TDEE calculations
│   │   ├── profile_agent.py   # User management
│   │   ├── meal_planner_agent.py
│   │   ├── chat_agent.py
│   │   ├── citation_validator.py
│   │   └── classifier.py      # Intent + safety routing
│   ├── graph/                 # LangGraph workflow (nodes, state, supervisor)
│   ├── rag/                   # Hybrid RAG components
│   ├── tools/                 # Agent tools
│   ├── data/                  # Database access + paper metadata
│   ├── memory/                # Conversation memory
│   ├── safety/                # Guardrails + safety metrics
│   ├── observability/         # Tracing
│   └── services/              # Email service
├── frontend/
│   └── src/
│       ├── components/        # React components
│       ├── pages/             # Route pages
│       └── stores/            # Zustand state
├── papers/                    # RAG corpus (not redistributed — see papers/README.md)
├── scripts/                   # Indexing, benchmarks, DB setup, ablation study
└── tests/                     # Unit / integration / e2e / performance / safety
```

---

## Environment Variables

```env
# Required
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=...
AUTH_SECRET_KEY=...

# Optional
USDA_API_KEY=...           # USDA FoodData Central lookups
COHERE_API_KEY=...         # Reranking fallback
RESEND_API_KEY=...         # Transactional email (password reset)
HYBRID_ALPHA=0.7           # Dense vs sparse retrieval weight
LLM_MODEL=gpt-4o-mini
```

See [`.env.example`](.env.example) for the complete annotated list.

---

## Scientific References

### Diet-Specific Macro Distributions

| Diet | Protein | Carbs | Fat | Reference |
|------|---------|-------|-----|-----------|
| Keto | 25% | 5% | 70% | Paoli et al. (2013) |
| Mediterranean | 20% | 45% | 35% | Keys et al. (1986) |
| Balanced | 25% | 45% | 30% | USDA Guidelines (2020-2025) |

### Key Publications

1. **Paoli, A. et al.** (2013). Beyond weight loss: therapeutic uses of ketogenic diets. *European Journal of Clinical Nutrition*
2. **Keys, A. et al.** (1986). The Seven Countries Study. *American Journal of Epidemiology*
3. **USDA** (2020). Dietary Guidelines for Americans 2020-2025

---

## Author

**Bárbara Peres**
*Master's Thesis — Information Management, NOVA IMS (Universidade Nova de Lisboa)*
*Architectural Governance for Safe and Evidence-Grounded Agentic AI in Nutrition*

[![GitHub](https://img.shields.io/badge/GitHub-barbaramperes-181717?style=flat-square&logo=github)](https://github.com/barbaramperes)

---

## License

Academic project. © 2025–2026 Bárbara Peres. All rights reserved.
