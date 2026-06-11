"""
NourishGraph Memory Manager

Unified interface for memory operations.
Combines conversation memory and session context for pending actions.
"""

from typing import Dict, List, Optional, Any

from .conversation import ConversationMemory, Message
from .session import SessionContext, get_session_context


class MemoryManager:
    """
    Unified memory management for NourishGraph.
    
    Combines:
    - ConversationMemory: Chat history
    - SessionContext: Current session state and pending actions
    
    Based on: SAGE framework (Liang et al., 2025)
    """
    
    def __init__(self, user_id: int = 1):
        self.user_id = user_id
        
        # Initialize memory components
        self.conversation = ConversationMemory(user_id=user_id)
        self.session = get_session_context(user_id)
    
    def add_message(
        self,
        role: str,
        content: str,
        intent: Optional[str] = None,
        tools_used: Optional[List[str]] = None
    ):
        """
        Add a message to conversation memory.
        
        Args:
            role: 'user' or 'assistant'
            content: The message content
            intent: Detected intent
            tools_used: List of tools used (for assistant messages)
        """
        self.conversation.add_message(
            role=role,
            content=content,
            intent=intent,
            tools_used=tools_used
        )
        self.session.increment_messages(role)
        if intent:
            self.session.add_topic(intent)
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get unified context for LLM.
        
        Returns:
            Dictionary with conversation context
        """
        return {
            "conversation_history": self.conversation.get_context(max_messages=10),
            "conversation_context": self.conversation.get_context_string(max_messages=5),
            "session": self.session.to_dict(),
            "session_summary": self.session.get_context_summary(),
            "recent_topics": self.conversation.get_recent_topics(),
            "mentioned_foods": self.conversation.get_mentioned_foods(),
        }
    
    def get_prompt_context(self) -> str:
        """
        Get formatted context string for prompts.
        
        Returns:
            String to include in LLM prompts
        """
        parts = []
        
        # Conversation history
        conv_context = self.conversation.get_context_string(max_messages=3)
        if conv_context and conv_context != "No previous conversation.":
            parts.append(conv_context)
        
        # Session context
        session_summary = self.session.get_context_summary()
        if session_summary and session_summary != "New session":
            parts.append(f"Session context: {session_summary}")
        
        return "\n\n".join(parts) if parts else ""
    
    # ============================================================
    # PENDING ACTIONS (for confirm/cancel flow)
    # ============================================================
    
    def set_pending_meal(self, meal_data: Dict):
        """Set a pending meal for confirmation."""
        self.session.set_pending_meal(meal_data)
    
    def get_pending_meal(self) -> Optional[Dict]:
        """Get pending meal without clearing."""
        return self.session.pending_meal_log
    
    def confirm_pending_meal(self) -> Optional[Dict]:
        """Confirm and clear pending meal."""
        return self.session.clear_pending_meal()

    def set_pending_profile_update(self, update: Dict):
        """Set a pending profile update for confirmation."""
        self.session.set_pending_profile_update(update)

    def get_pending_profile_update(self) -> Optional[Dict]:
        """Get pending profile update without clearing."""
        return self.session.pending_profile_update

    def confirm_pending_profile_update(self) -> Optional[Dict]:
        """Confirm and clear pending profile update."""
        return self.session.clear_pending_profile_update()
    
    # ============================================================
    # SESSION MANAGEMENT
    # ============================================================
    
    def new_session(self):
        """Start a new session (clear short-term memory)."""
        self.conversation.clear()
        self.session.reset()
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        return {
            "conversation": self.conversation.get_stats(),
            "session": self.session.to_dict(),
        }


# Global memory manager storage
_memory_managers: Dict[int, MemoryManager] = {}


def get_memory_manager(user_id: int = 1) -> MemoryManager:
    """
    Get or create memory manager for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        MemoryManager for the user
    """
    if user_id not in _memory_managers:
        _memory_managers[user_id] = MemoryManager(user_id=user_id)
    
    return _memory_managers[user_id]


def clear_user_memory(user_id: int = 1):
    """Clear all memory for a user."""
    if user_id in _memory_managers:
        _memory_managers[user_id].new_session()
