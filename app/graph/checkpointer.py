"""
app/graph/checkpointer.py

In-memory checkpointer for LangGraph state management.

LangGraph requires a checkpointer to compile a StateGraph. MemorySaver keeps
the graph state (node outputs, routing decisions) in process memory for the
duration of each request.

Conversation history persistence is handled separately by the chat_history
table in PostgreSQL (see app/data/database.py — save_chat_message /
get_conversations). The checkpointer is NOT responsible for long-term
conversation storage.

Usage:
    from app.graph.checkpointer import get_checkpointer
    
    checkpointer = get_checkpointer()
    graph = workflow.compile(checkpointer=checkpointer)
    
    config = {"configurable": {"thread_id": f"user_{user_id}"}}
    result = graph.invoke(state, config)
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

# Singleton — one MemorySaver per process
_checkpointer: MemorySaver | None = None


def get_checkpointer() -> MemorySaver:
    """Return the shared MemorySaver instance (created once per process)."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer


def get_thread_config(user_id: int) -> dict:
    """
    Generate thread configuration for a user.
    
    Args:
        user_id: User ID for thread isolation
        
    Returns:
        Config dict for graph.invoke()
    """
    return {
        "configurable": {
            "thread_id": f"user_{user_id}"
        }
    }
