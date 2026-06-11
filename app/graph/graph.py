"""
app/graph/graph.py

LangGraph principal do NourishGraph.

Implementa uma state machine com os seguintes nós:
1. Planner (Chain-of-Thought)
2. Router (Classificação)
3. Agents (Science, Nutrition, Profile, Chat, MealPlanner, Analysis) - cada um com ReAct
4. Reflection (Auto-avaliação)
5. Synthesizer (Resposta final)

Arquitetura baseada em:
- LangGraph (LangChain, 2024)
- ReAct (Yao et al., 2023)
- Chain-of-Thought (Wei et al., 2022)
- Reflexion (Shinn et al., 2023)
"""

from __future__ import annotations

from typing import Dict, Any, List

from langgraph.graph import StateGraph, END

from app.graph.state import AgentState, create_initial_state
from app.graph.checkpointer import get_checkpointer, get_thread_config
from app.graph.nodes import (
    query_analysis_node,
    route_after_analysis,
    meta_query_node,
    off_topic_response_node,
    clarification_node,
    planner_node,
    router_node,
    route_to_agent,
    science_agent_node,
    nutrition_agent_node,
    profile_agent_node,
    chat_agent_node,
    meal_planner_agent_node,
    medical_blocked_node,
    reflection_node,
    synthesizer_node,
)


def create_graph() -> StateGraph:
    """
    Cria o grafo do agente NourishGraph.
    
    Estrutura:
    
                    ┌─────────┐
                    │  START  │
                    └────┬────┘
                         │
                         ▼
                ┌────────────────┐
                │ Query Analysis │  ← LLM pre-classification
                └───────┬────────┘
                        │
          ┌─────────────┼──────────────┬──────────────┐
          │             │              │              │
          ▼             ▼              ▼              │
     ┌────────┐  ┌───────────┐ ┌──────────────┐      │
     │  Meta  │  │ Off-Topic │ │Clarification │      │
     │ Query  │  │ Response  │ │    Node      │      │
     └───┬────┘  └─────┬─────┘ └──────┬───────┘      │
         │             │              │               │
         └─────────────┼──────────────┘               │
                       │                              │
                       ▼                              ▼
                 ┌───────────┐                  ┌─────────┐
                 │Synthesizer│                  │ Planner │
                 └─────┬─────┘                  └────┬────┘
                       │                             │
                       ▼                             ▼
                   ┌───────┐                   ┌─────────┐
                   │  END  │                   │ Router  │
                   └───────┘                   └────┬────┘
                                                    │
                                      ┌─────────────┼──────────┐
                                      ▼             ▼          ▼
                                 ┌─────────┐  ┌─────────┐ ┌────────┐
                                 │ Science │  │Nutrition│ │  Chat  │
                                 └────┬────┘  └────┬────┘ └───┬────┘
                                      └────────────┼──────────┘
                                                   ▼
                                             ┌──────────┐
                                             │Reflection│
                                             └────┬─────┘
                                                  ▼
                                            ┌───────────┐
                                            │Synthesizer│
                                            └─────┬─────┘
                                                  ▼
                                              ┌───────┐
                                              │  END  │
                                              └───────┘
    
    Returns:
        StateGraph compilado
    """
    
    # Criar grafo
    workflow = StateGraph(AgentState)
    
    # ============================================================
    # ADICIONAR NÓS
    # ============================================================
    
    # PRE-PROCESSING: Query Analysis (LLM-based)
    workflow.add_node("query_analysis", query_analysis_node)
    workflow.add_node("meta_query", meta_query_node)
    workflow.add_node("off_topic_response", off_topic_response_node)
    workflow.add_node("clarification", clarification_node)
    
    # MAIN PIPELINE
    workflow.add_node("planner", planner_node)
    workflow.add_node("router", router_node)
    workflow.add_node("science", science_agent_node)
    workflow.add_node("nutrition", nutrition_agent_node)
    workflow.add_node("profile", profile_agent_node)
    workflow.add_node("chat", chat_agent_node)
    workflow.add_node("meal_planner", meal_planner_agent_node)
    workflow.add_node("medical_blocked", medical_blocked_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("synthesizer", synthesizer_node)
    
    # ============================================================
    # DEFINIR EDGES (Conexões)
    # ============================================================
    
    # Start → Query Analysis (LLM pre-classification)
    workflow.set_entry_point("query_analysis")
    
    # Query Analysis → conditional routing
    workflow.add_conditional_edges(
        "query_analysis",
        route_after_analysis,
        {
            "meta_query": "meta_query",
            "off_topic_response": "off_topic_response",
            "clarification": "clarification",
            "planner": "planner",
        }
    )
    
    # Pre-processing nodes → Synthesizer (skip main pipeline)
    workflow.add_edge("meta_query", "synthesizer")
    workflow.add_edge("off_topic_response", "synthesizer")
    workflow.add_edge("clarification", "synthesizer")
    
    # Planner → Router
    workflow.add_edge("planner", "router")
    
    # Router → Agent (conditional)
    workflow.add_conditional_edges(
        "router",
        route_to_agent,
        {
            "science": "science",
            "nutrition": "nutrition",
            "profile": "profile",
            "chat": "chat",
            "meal_planner": "meal_planner",
            "medical_blocked": "medical_blocked",
        }
    )
    
    # Agents → Reflection
    workflow.add_edge("science", "reflection")
    workflow.add_edge("nutrition", "reflection")
    workflow.add_edge("profile", "reflection")
    workflow.add_edge("chat", "reflection")
    workflow.add_edge("meal_planner", "reflection")
    workflow.add_edge("medical_blocked", "synthesizer")
    
    # Reflection → Synthesizer
    workflow.add_edge("reflection", "synthesizer")
    
    # Synthesizer → END
    workflow.add_edge("synthesizer", END)
    
    return workflow


def compile_graph():
    """
    Compila o grafo para execução.
    
    Includes checkpointer for conversation persistence.
    
    Returns:
        Grafo compilado pronto para .invoke()
    """
    workflow = create_graph()
    checkpointer = get_checkpointer()
    return workflow.compile(checkpointer=checkpointer)


# Compiled graph for global use
compiled_graph = compile_graph()


def run_agent(user_input: str, user_profile: Dict = None, chat_history: List[Dict] = None, user_id: int = None) -> Dict[str, Any]:
    """
    Executes the agent with a user question.
    
    Args:
        user_input: User question
        user_profile: User profile (optional)
        chat_history: Previous conversation messages for context (optional)
        user_id: User ID for conversation persistence (optional)
    
    Returns:
        Final state with the response
    
    Example:
        result = run_agent("What do studies say about fasting?", user_id=1)
        print(result["final_response"])
    """
    # Create initial state with conversation history
    initial_state = create_initial_state(user_input, user_profile, chat_history)
    
    # Always use a thread config - use anonymous thread if no user_id
    # This is required because the checkpointer needs a thread_id
    if user_id:
        config = get_thread_config(user_id)
    else:
        # Use a temporary anonymous thread for testing/CLI usage
        import uuid
        config = {"configurable": {"thread_id": f"anon-{uuid.uuid4().hex[:8]}"}}
    
    final_state = compiled_graph.invoke(initial_state, config)
    
    return final_state


def run_agent_with_streaming(user_input: str, user_profile: Dict = None, chat_history: List[Dict] = None, user_id: int = None):
    """
    Executes the agent with streaming (shows progress).
    
    Yields graph events as they are executed, allowing for progressive
    display of responses and real-time feedback.
    
    Args:
        user_input: User question
        user_profile: User profile (optional)
        chat_history: Previous conversation messages (optional)
        user_id: User ID for persistence (optional)
    
    Yields:
        Dict with node name as key and state as value
    
    Example:
        for event in run_agent_with_streaming("Question?"):
            for node_name, state in event.items():
                print(f"{node_name}: {state.get('intent')}")
    """
    initial_state = create_initial_state(user_input, user_profile, chat_history)
    
    # Always use a thread config - use anonymous thread if no user_id
    if user_id:
        config = get_thread_config(user_id)
    else:
        import uuid
        config = {"configurable": {"thread_id": f"anon-{uuid.uuid4().hex[:8]}"}}
    
    for event in compiled_graph.stream(initial_state, config):
        yield event
