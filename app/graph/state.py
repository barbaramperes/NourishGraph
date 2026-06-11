"""
app/graph/state.py

LangGraph agent shared state.
All nodes read and write to this state.

Based on:
- LangGraph State Management
- TypedDict for type safety
"""

from __future__ import annotations

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """
    Shared state between all graph nodes.
    
    Attributes:
        messages: Message history (user + assistant)
        user_input: Original user question
        intent: Classified intent (science/nutrition/profile/chat)
        plan: Action plan created by Planner
        context: Additional context (papers, data, etc.)
        tools_used: List of tools used
        agent_outputs: Outputs from each agent
        reflection: Response self-evaluation
        final_response: Final response to user
        confidence: Confidence level (0-1)
        user_profile: User profile
        error: Error message if any
    """
    
    # Messages (with reducer for automatic append)
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Input
    user_input: str
    
    # Routing
    intent: Optional[str]  # "science" | "nutrition" | "profile" | "chat"
    
    # Planning (Chain-of-Thought)
    plan: Optional[str]
    
    # Context from tools/RAG
    context: Dict[str, Any]
    
    # Tracking
    tools_used: List[str]
    agent_outputs: Dict[str, str]
    
    # Reflection
    reflection: Optional[str]
    reflection_details: Optional[Dict[str, Any]]
    confidence: float
    
    # Output
    final_response: Optional[str]
    quality_score: float
    feedback_applied: bool
    
    # User data
    user_profile: Dict[str, Any]
    
    # Extra metadata (from medical_blocked etc.)
    agent_output: Optional[str]
    metadata: Optional[Dict[str, Any]]
    
    # Error handling
    error: Optional[str]


def create_initial_state(user_input: str, user_profile: Dict = None, chat_history: List[Dict] = None) -> AgentState:
    """
    Creates initial state for a new conversation.
    
    Args:
        user_input: User question
        user_profile: User profile (optional)
        chat_history: Previous messages for context (optional)
    
    Returns:
        Initial AgentState
    """
    from langchain_core.messages import HumanMessage, AIMessage
    
    # Convert chat history to LangChain messages
    messages = []
    if chat_history:
        for msg in chat_history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
    
    return AgentState(
        messages=messages,
        user_input=user_input,
        intent=None,
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
        error=None
    )


# Possible intents
class Intent:
    SCIENCE = "science"          # Questions about studies/evidence
    NUTRITION = "nutrition"      # Questions about calories/foods
    PROFILE = "profile"          # Profile/meals management
    CHAT = "chat"               # General nutrition conversation
    MEAL_PLANNER = "meal_planner"  # Meal planning and suggestions
    
    ALL = [SCIENCE, NUTRITION, PROFILE, CHAT, MEAL_PLANNER]
