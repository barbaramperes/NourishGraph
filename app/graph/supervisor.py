"""
app/graph/supervisor.py

LangGraph Supervisor Pattern Implementation

The Supervisor is an LLM-based orchestrator that:
1. Analyzes the user query
2. Decides which agent(s) to call
3. Can call multiple agents sequentially
4. Synthesizes the final response

This is more flexible than static routing because the supervisor
can dynamically choose agents based on conversation context.

Based on:
- LangGraph Supervisor (LangChain, 2024)
- Multi-Agent Collaboration Patterns
- Hierarchical Agent Teams

Reference: https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/
"""

from __future__ import annotations

from typing import Dict, Any, List, Literal, Optional, Annotated
import operator
import json
import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# Import existing agents
from app.agents.science_agent import get_science_agent
from app.agents.nutrition_agent import get_nutrition_agent
from app.agents.profile_agent import get_profile_agent
from app.agents.chat_agent import get_chat_agent
from app.agents.meal_planner_agent import get_meal_planner_agent


# ============================================================
# SUPERVISOR STATE
# ============================================================

class SupervisorState(BaseModel):
    """State for supervisor workflow."""
    
    class Config:
        arbitrary_types_allowed = True
    
    # Messages with proper annotation for LangGraph
    messages: List[BaseMessage] = Field(default_factory=list)
    
    # User context
    user_input: str = ""
    user_profile: Dict[str, Any] = Field(default_factory=dict)
    
    # Supervisor decisions
    next_agent: Optional[str] = None
    agents_called: List[str] = Field(default_factory=list)
    agent_outputs: Dict[str, str] = Field(default_factory=dict)
    
    # Final output
    final_response: Optional[str] = None
    tools_used: List[str] = Field(default_factory=list)
    sources: List[Dict] = Field(default_factory=list)
    intent: str = "chat"
    confidence: float = 0.7
    
    # Control
    iteration: int = 0
    max_iterations: int = 3


# ============================================================
# SUPERVISOR ROUTING SCHEMA
# ============================================================

class SupervisorDecision(BaseModel):
    """Supervisor's decision on which agent to call next."""
    
    next: Literal["science", "nutrition", "profile", "meal_planner", "chat", "FINISH"] = Field(
        description="The next agent to call, or FINISH if the task is complete"
    )
    reasoning: str = Field(
        description="Brief explanation of why this agent was chosen"
    )


# ============================================================
# SUPERVISOR NODE
# ============================================================

SUPERVISOR_SYSTEM_PROMPT = """You are a supervisor managing a team of specialized nutrition AI agents.

Your team members:
1. **science** - Searches scientific papers for evidence-based information about nutrients, supplements, health conditions
2. **nutrition** - Calculates BMR, TDEE, macros, looks up food nutrition data, provides diet advice
3. **profile** - Saves/updates user profile information (weight, height, age, goals, diet preferences)
4. **meal_planner** - Creates personalized meal plans based on user's nutritional needs
5. **chat** - General conversation, greetings, clarifications

Your job is to:
1. Analyze the user's question
2. Decide which agent should handle it
3. If the task needs multiple agents, call them one at a time
4. When the response is complete, output FINISH

ROUTING GUIDELINES:
- Questions about health effects, benefits, studies, "what does research say" → science
- Questions about "how many calories", BMR, TDEE, macros → nutrition  
- Questions about food suggestions for goals → nutrition
- "Should I take supplements", "what vitamins should I take", practical nutrition advice → nutrition
- "I weigh X", "I'm X years old", "my goal is" → profile
- "Create a meal plan", "weekly menu" → meal_planner
- Greetings, thanks, unclear questions → chat
- Questions specifically about scientific studies, papers, evidence → science

IMPORTANT:
- "Should I take vitamin X?" = nutrition (practical advice)
- "What does research say about vitamin X?" = science (research review)
- If an agent has already been called and provided a good answer, choose FINISH
- Don't call the same agent twice unless needed
- For complex questions, you might need science first, then nutrition
- Always prioritize user experience - don't over-complicate simple questions

Current agents already called: {agents_called}
Agent outputs so far: {agent_outputs}
"""


def create_supervisor_chain():
    """Create the supervisor LLM chain."""
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Use structured output for reliable routing
    supervisor_chain = llm.with_structured_output(SupervisorDecision)
    
    return supervisor_chain


def supervisor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supervisor node that decides which agent to call next.
    
    Uses structured output to reliably route to agents.
    """
    messages = state.get("messages", [])
    user_input = state.get("user_input", "")
    agents_called = state.get("agents_called", [])
    agent_outputs = state.get("agent_outputs", {})
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    
    print(f"   📊 Supervisor iteration {iteration}/{max_iterations}, agents_called: {agents_called}")
    
    # Safety check - prevent infinite loops
    if iteration >= max_iterations:
        print(f"   ⚠️ Max iterations reached, forcing FINISH")
        return {
            "next_agent": "FINISH",
            "iteration": iteration + 1
        }
    
    # If we already called an agent and got output, we're done
    if len(agent_outputs) > 0:
        print(f"   ✅ Agent(s) provided output, finishing")
        return {
            "next_agent": "FINISH",
            "iteration": iteration + 1
        }
    
    # Format agent outputs for context
    outputs_summary = ""
    for agent, output in agent_outputs.items():
        # Truncate long outputs
        truncated = output[:500] + "..." if len(output) > 500 else output
        outputs_summary += f"\n[{agent}]: {truncated}\n"
    
    # Create supervisor prompt
    system_prompt = SUPERVISOR_SYSTEM_PROMPT.format(
        agents_called=", ".join(agents_called) if agents_called else "none",
        agent_outputs=outputs_summary if outputs_summary else "none yet"
    )
    
    # Add user profile context to help with routing
    user_profile = state.get("user_profile", {})
    profile_summary = ""
    if user_profile:
        profile_parts = []
        for k, v in user_profile.items():
            if v and k not in ('id', 'password_hash', 'created_at', 'updated_at', 'email'):
                profile_parts.append(f"{k}={v}")
        if profile_parts:
            profile_summary = f"\n\nUser profile: {', '.join(profile_parts)}"
    
    # Get supervisor decision
    supervisor_chain = create_supervisor_chain()
    
    supervisor_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User question: {user_input}{profile_summary}\n\nDecide which agent should handle this next, or FINISH if complete.")
    ]
    
    try:
        decision = supervisor_chain.invoke(supervisor_messages)
        print(f"   🎯 Supervisor: {decision.next} (reason: {decision.reasoning})")
        
        return {
            "next_agent": decision.next,
            "iteration": iteration + 1
        }
    except Exception as e:
        print(f"   ⚠️ Supervisor error: {e}, defaulting to chat")
        return {
            "next_agent": "chat",
            "iteration": iteration + 1
        }


# ============================================================
# AGENT WRAPPER NODES
# ============================================================

def science_worker_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute science agent and return results."""
    user_input = state.get("user_input", "")
    user_profile = state.get("user_profile", {})
    agents_called = state.get("agents_called", [])
    agent_outputs = state.get("agent_outputs", {})
    tools_used = state.get("tools_used", [])
    
    print("   🔬 Science Agent working...")
    
    agent = get_science_agent()
    result = agent.run(user_input, context={"user_profile": user_profile})
    
    # Extract sources if available
    sources = []
    try:
        from app.tools.search_tools import get_last_search_results
        sources = get_last_search_results()
    except:
        pass
    
    return {
        "agents_called": agents_called + ["science"],
        "agent_outputs": {**agent_outputs, "science": result.content},
        "tools_used": tools_used + (result.tools_used or []),
        "sources": sources,
        "intent": "science"
    }


def nutrition_worker_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute nutrition agent and return results."""
    user_input = state.get("user_input", "")
    user_profile = state.get("user_profile", {})
    agents_called = state.get("agents_called", [])
    agent_outputs = state.get("agent_outputs", {})
    tools_used = state.get("tools_used", [])
    
    print("   🥗 Nutrition Agent working...")
    
    agent = get_nutrition_agent()
    result = agent.run(user_input, context={"user_profile": user_profile})
    
    return {
        "agents_called": agents_called + ["nutrition"],
        "agent_outputs": {**agent_outputs, "nutrition": result.content},
        "tools_used": tools_used + (result.tools_used or []),
        "intent": "nutrition"
    }


def profile_worker_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute profile agent and return results."""
    user_input = state.get("user_input", "")
    user_profile = state.get("user_profile", {})
    agents_called = state.get("agents_called", [])
    agent_outputs = state.get("agent_outputs", {})
    tools_used = state.get("tools_used", [])
    
    print("   👤 Profile Agent working...")
    
    agent = get_profile_agent()
    result = agent.run(user_input, context={"user_profile": user_profile})
    
    return {
        "agents_called": agents_called + ["profile"],
        "agent_outputs": {**agent_outputs, "profile": result.content},
        "tools_used": tools_used + (result.tools_used or []),
        "intent": "profile"
    }


def meal_planner_worker_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute meal planner agent and return results."""
    user_input = state.get("user_input", "")
    user_profile = state.get("user_profile", {})
    agents_called = state.get("agents_called", [])
    agent_outputs = state.get("agent_outputs", {})
    tools_used = state.get("tools_used", [])
    
    print("   🍽️ Meal Planner Agent working...")
    
    agent = get_meal_planner_agent()
    result = agent.run(user_input, context={"user_profile": user_profile})
    
    return {
        "agents_called": agents_called + ["meal_planner"],
        "agent_outputs": {**agent_outputs, "meal_planner": result.content},
        "tools_used": tools_used + (result.tools_used or []),
        "intent": "meal_planner"
    }


def chat_worker_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute chat agent and return results."""
    user_input = state.get("user_input", "")
    user_profile = state.get("user_profile", {})
    agents_called = state.get("agents_called", [])
    agent_outputs = state.get("agent_outputs", {})
    tools_used = state.get("tools_used", [])
    
    print("   💬 Chat Agent working...")
    
    agent = get_chat_agent()
    result = agent.run(user_input, context={"user_profile": user_profile})
    
    return {
        "agents_called": agents_called + ["chat"],
        "agent_outputs": {**agent_outputs, "chat": result.content},
        "tools_used": tools_used + (result.tools_used or []),
        "intent": "chat"
    }


# ============================================================
# SYNTHESIZER NODE
# ============================================================

def synthesizer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine outputs from multiple agents into a coherent response.
    
    If only one agent was called, return its output directly.
    If multiple agents were called, synthesize their outputs.
    """
    agent_outputs = state.get("agent_outputs", {})
    agents_called = state.get("agents_called", [])
    user_input = state.get("user_input", "")
    sources = state.get("sources", [])
    
    # Single agent - return directly
    if len(agent_outputs) == 1:
        agent_name = list(agent_outputs.keys())[0]
        return {
            "final_response": agent_outputs[agent_name],
            "intent": agent_name
        }
    
    # Multiple agents - synthesize
    if len(agent_outputs) > 1:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        
        synthesis_prompt = f"""You are synthesizing responses from multiple AI agents into one coherent answer.

User question: {user_input}

Agent responses:
"""
        for agent, output in agent_outputs.items():
            synthesis_prompt += f"\n### {agent.upper()} AGENT:\n{output}\n"
        
        synthesis_prompt += """
Combine these responses into a single, well-structured answer that:
1. Avoids repetition
2. Maintains all important information
3. Has a logical flow
4. Uses proper markdown formatting

Do NOT mention that multiple agents were used. Present as one unified response."""
        
        response = llm.invoke([HumanMessage(content=synthesis_prompt)])
        
        return {
            "final_response": response.content,
            "intent": agents_called[0] if agents_called else "chat"
        }
    
    # No outputs - fallback
    return {
        "final_response": "I'm not sure how to help with that. Could you rephrase your question?",
        "intent": "chat"
    }


# ============================================================
# ROUTING FUNCTION
# ============================================================

def route_supervisor(state: Dict[str, Any]) -> str:
    """Route based on supervisor's decision."""
    next_agent = state.get("next_agent", "FINISH")
    
    if next_agent == "FINISH":
        return "synthesizer"
    
    return next_agent


# ============================================================
# CREATE SUPERVISOR GRAPH
# ============================================================

def create_supervisor_graph():
    """
    Create the supervisor-based multi-agent graph.
    
    Architecture:
    
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                ┌──►│ SUPERVISOR  │◄──┐
                │   └──────┬──────┘   │
                │          │          │
                │    ┌─────┴─────┐    │
                │    ▼     ▼     ▼    │
                │ ┌─────┐┌─────┐┌─────┐
                │ │Sci  ││Nutr ││Prof │
                │ └──┬──┘└──┬──┘└──┬──┘
                │    │     │      │   │
                │    └─────┴──────┘   │
                │          │          │
                └──────────┴──────────┘
                           │
                    (when FINISH)
                           ▼
                    ┌─────────────┐
                    │ SYNTHESIZER │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │     END     │
                    └─────────────┘
    """
    
    # Use dict-based state for LangGraph
    workflow = StateGraph(dict)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("science", science_worker_node)
    workflow.add_node("nutrition", nutrition_worker_node)
    workflow.add_node("profile", profile_worker_node)
    workflow.add_node("meal_planner", meal_planner_worker_node)
    workflow.add_node("chat", chat_worker_node)
    workflow.add_node("synthesizer", synthesizer_node)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Add conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "science": "science",
            "nutrition": "nutrition",
            "profile": "profile",
            "meal_planner": "meal_planner",
            "chat": "chat",
            "synthesizer": "synthesizer"
        }
    )
    
    # All agents loop back to supervisor
    for agent in ["science", "nutrition", "profile", "meal_planner", "chat"]:
        workflow.add_edge(agent, "supervisor")
    
    # Synthesizer ends the workflow
    workflow.add_edge("synthesizer", END)
    
    return workflow.compile()


# ============================================================
# RUN SUPERVISOR
# ============================================================

# Compiled graph (singleton)
_supervisor_graph = None

def get_supervisor_graph():
    """Get or create the supervisor graph."""
    global _supervisor_graph
    if _supervisor_graph is None:
        _supervisor_graph = create_supervisor_graph()
    return _supervisor_graph


def run_supervisor(
    user_input: str,
    user_profile: Dict = None,
    chat_history: List[Dict] = None
) -> Dict[str, Any]:
    """
    Run the supervisor-based multi-agent system.
    
    Simplified version: Supervisor decides once, executes the agent, returns.
    
    Args:
        user_input: User's question
        user_profile: User profile data
        chat_history: Previous conversation messages
    
    Returns:
        Dict with final_response, intent, tools_used, sources, etc.
    """
    print(f"🎯 Supervisor processing: {user_input[:50]}...")
    
    # Step 1: Get supervisor decision
    supervisor_chain = create_supervisor_chain()
    
    system_prompt = SUPERVISOR_SYSTEM_PROMPT.format(
        agents_called="none",
        agent_outputs="none yet"
    )
    
    supervisor_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User question: {user_input}\n\nDecide which agent should handle this.")
    ]
    
    try:
        decision = supervisor_chain.invoke(supervisor_messages)
        agent_to_call = decision.next
        print(f"   🎯 Supervisor chose: {agent_to_call} (reason: {decision.reasoning})")
    except Exception as e:
        print(f"   ⚠️ Supervisor error: {e}, defaulting to chat")
        agent_to_call = "chat"
    
    if agent_to_call == "FINISH":
        agent_to_call = "chat"
    
    # Step 2: Execute the chosen agent
    context = {"user_profile": user_profile or {}}
    sources = []
    
    if agent_to_call == "science":
        print("   🔬 Science Agent working...")
        # Clear previous search results before running
        try:
            from app.tools.search_tools import clear_last_search_results, get_last_search_results
            clear_last_search_results()
        except ImportError:
            pass
        
        agent = get_science_agent()
        result = agent.run(user_input, context=context)
        
        # Get sources from the global search results (set by search_scientific_papers tool)
        try:
            from app.tools.search_tools import get_last_search_results
            sources = get_last_search_results() or []
            print(f"   📚 Sources found: {len(sources)} papers")
            if sources:
                print(f"   📄 First source: {sources[0].get('title', 'Unknown')[:50]}")
        except Exception as e:
            print(f"   ⚠️ Error getting sources: {e}")
            sources = []
    elif agent_to_call == "nutrition":
        print("   🥗 Nutrition Agent working...")
        agent = get_nutrition_agent()
        result = agent.run(user_input, context=context)
    elif agent_to_call == "profile":
        print("   👤 Profile Agent working...")
        agent = get_profile_agent()
        result = agent.run(user_input, context=context)
    elif agent_to_call == "meal_planner":
        print("   🍽️ Meal Planner Agent working...")
        agent = get_meal_planner_agent()
        result = agent.run(user_input, context=context)
    else:
        print("   💬 Chat Agent working...")
        agent = get_chat_agent()
        result = agent.run(user_input, context=context)
    
    print(f"   ✅ Agent completed: {agent_to_call}")
    
    # Step 3: Return result in same format as standard graph
    # The API expects sources in result["context"]["papers"]
    return {
        "final_response": result.content,
        "intent": agent_to_call,
        "tools_used": result.tools_used or [],
        "sources": sources,  # Keep for backward compatibility
        "context": {
            "papers": sources,  # API extracts from here
            "source": f"{agent_to_call}_agent",
            "used_rag": agent_to_call == "science" and len(sources) > 0
        },
        "confidence": result.confidence,
        "agents_called": [agent_to_call]
    }


# ============================================================
# FEATURE FLAG
# ============================================================

def is_supervisor_enabled() -> bool:
    """Check if supervisor mode is enabled via environment variable."""
    return os.getenv("USE_SUPERVISOR", "false").lower() == "true"
