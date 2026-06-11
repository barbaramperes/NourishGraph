"""
NourishGraph Session Context

Maintains context within a user session for coherent conversations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


@dataclass
class SessionContext:
    """
    Maintains context for a single user session.
    
    Tracks:
    - Current conversation topic
    - Active goals being discussed
    - Foods mentioned
    - Pending actions/follow-ups
    """
    
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    # Current state
    current_topic: Optional[str] = None
    current_intent: Optional[str] = None
    
    # Conversation tracking
    topics_discussed: List[str] = field(default_factory=list)
    foods_mentioned: List[str] = field(default_factory=list)
    goals_mentioned: List[str] = field(default_factory=list)
    
    # Pending items
    pending_meal_log: Optional[Dict] = None  # Meal waiting to be confirmed
    pending_profile_update: Optional[Dict] = None  # Profile update waiting to be confirmed
    pending_question: Optional[str] = None   # Follow-up question waiting
    
    # Session metrics
    message_count: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired due to inactivity."""
        elapsed = datetime.now() - self.last_activity
        return elapsed > timedelta(minutes=timeout_minutes)
    
    def add_topic(self, topic: str):
        """Add a discussed topic."""
        if topic and topic not in self.topics_discussed:
            self.topics_discussed.append(topic)
        self.current_topic = topic
        self.update_activity()
    
    def add_food(self, food: str):
        """Add a mentioned food."""
        if food and food.lower() not in [f.lower() for f in self.foods_mentioned]:
            self.foods_mentioned.append(food)
        self.update_activity()
    
    def add_goal(self, goal: str):
        """Add a mentioned goal."""
        if goal and goal not in self.goals_mentioned:
            self.goals_mentioned.append(goal)
        self.update_activity()
    
    def set_pending_meal(self, meal_data: Dict):
        """Set a pending meal log awaiting confirmation."""
        self.pending_meal_log = meal_data
        self.update_activity()
    
    def clear_pending_meal(self) -> Optional[Dict]:
        """Clear and return pending meal."""
        meal = self.pending_meal_log
        self.pending_meal_log = None
        return meal

    def set_pending_profile_update(self, update: Dict):
        """Set a pending profile update awaiting confirmation."""
        self.pending_profile_update = update
        self.update_activity()

    def clear_pending_profile_update(self) -> Optional[Dict]:
        """Clear and return pending profile update."""
        update = self.pending_profile_update
        self.pending_profile_update = None
        return update
    
    def increment_messages(self, role: str):
        """Increment message counters."""
        self.message_count += 1
        if role == "user":
            self.user_messages += 1
        else:
            self.assistant_messages += 1
        self.update_activity()
    
    def get_context_summary(self) -> str:
        """Get a summary of current session context."""
        parts = []
        
        if self.current_topic:
            parts.append(f"Current topic: {self.current_topic}")
        
        if self.topics_discussed:
            parts.append(f"Discussed: {', '.join(self.topics_discussed[-5:])}")
        
        if self.foods_mentioned:
            parts.append(f"Foods mentioned: {', '.join(self.foods_mentioned[-5:])}")
        
        if self.goals_mentioned:
            parts.append(f"Goals: {', '.join(self.goals_mentioned)}")
        
        if self.pending_meal_log:
            parts.append(f"Pending meal to log: {self.pending_meal_log.get('description', 'unknown')}")
        
        return " | ".join(parts) if parts else "New session"
    
    def to_dict(self) -> Dict:
        """Export session as dictionary."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "current_topic": self.current_topic,
            "current_intent": self.current_intent,
            "topics_discussed": self.topics_discussed,
            "foods_mentioned": self.foods_mentioned,
            "goals_mentioned": self.goals_mentioned,
            "message_count": self.message_count,
            "has_pending_meal": self.pending_meal_log is not None,
            "has_pending_profile_update": self.pending_profile_update is not None,
        }
    
    def reset(self):
        """Reset session (start new conversation)."""
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.now()
        self.last_activity = datetime.now()
        self.current_topic = None
        self.current_intent = None
        self.topics_discussed = []
        self.foods_mentioned = []
        self.goals_mentioned = []
        self.pending_meal_log = None
        self.pending_profile_update = None
        self.pending_question = None
        self.message_count = 0
        self.user_messages = 0
        self.assistant_messages = 0


# Global session storage (in production, use Redis or database)
_sessions: Dict[int, SessionContext] = {}


def get_session_context(user_id: int = 1) -> SessionContext:
    """
    Get or create session context for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        SessionContext for the user
    """
    if user_id not in _sessions:
        _sessions[user_id] = SessionContext()
    
    session = _sessions[user_id]
    
    # Check for expiry
    if session.is_expired():
        session.reset()
    
    return session


def clear_session(user_id: int = 1):
    """Clear session for a user."""
    if user_id in _sessions:
        _sessions[user_id].reset()
