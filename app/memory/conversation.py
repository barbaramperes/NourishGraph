"""
NourishGraph Conversation Memory

Stores and manages conversation history for context persistence.
Based on: SAGE framework (Liang et al., 2025)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from collections import deque
import json


@dataclass
class Message:
    """A single message in conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    intent: Optional[str] = None
    tools_used: Optional[List[str]] = None
    safety_level: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "intent": self.intent,
            "tools_used": self.tools_used,
            "safety_level": self.safety_level,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            intent=data.get("intent"),
            tools_used=data.get("tools_used"),
            safety_level=data.get("safety_level"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConversationSummary:
    """Summary of a conversation for long-term storage."""
    session_id: str
    start_time: datetime
    end_time: datetime
    message_count: int
    topics: List[str]
    key_points: List[str]
    user_goals_mentioned: List[str]
    foods_discussed: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "message_count": self.message_count,
            "topics": self.topics,
            "key_points": self.key_points,
            "user_goals_mentioned": self.user_goals_mentioned,
            "foods_discussed": self.foods_discussed,
        }


class ConversationMemory:
    """
    Manages conversation history with sliding window and summarization.
    
    Features:
    - Short-term memory: Last N messages (configurable)
    - Long-term memory: Summaries of past conversations
    - Context retrieval: Get relevant past context
    
    Based on: SAGE framework for coherent agent conversations
    """
    
    def __init__(
        self,
        max_messages: int = 20,
        max_context_tokens: int = 2000,
        user_id: int = 1
    ):
        self.user_id = user_id
        self.max_messages = max_messages
        self.max_context_tokens = max_context_tokens
        
        # Short-term memory (current session)
        self.messages: deque = deque(maxlen=max_messages)
        
        # Long-term memory (summaries)
        self.summaries: List[ConversationSummary] = []
        
        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start = datetime.now()
    
    def add_message(
        self,
        role: str,
        content: str,
        intent: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
        safety_level: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Message:
        """Add a message to conversation history."""
        message = Message(
            role=role,
            content=content,
            intent=intent,
            tools_used=tools_used,
            safety_level=safety_level,
            metadata=metadata or {}
        )
        self.messages.append(message)
        return message
    
    def get_context(self, max_messages: Optional[int] = None) -> List[Dict]:
        """
        Get recent conversation context for LLM.
        
        Returns:
            List of message dictionaries for context
        """
        n = max_messages or self.max_messages
        recent = list(self.messages)[-n:]
        return [
            {"role": m.role, "content": m.content}
            for m in recent
        ]
    
    def get_context_string(self, max_messages: int = 5) -> str:
        """
        Get conversation context as a formatted string.
        
        Useful for including in prompts.
        """
        recent = list(self.messages)[-max_messages:]
        if not recent:
            return "No previous conversation."
        
        lines = ["Previous conversation:"]
        for m in recent:
            prefix = "User" if m.role == "user" else "Assistant"
            # Truncate long messages
            content = m.content[:200] + "..." if len(m.content) > 200 else m.content
            lines.append(f"- {prefix}: {content}")
        
        return "\n".join(lines)
    
    def get_recent_topics(self) -> List[str]:
        """Extract topics from recent conversation."""
        topics = set()
        
        for msg in self.messages:
            if msg.intent:
                topics.add(msg.intent)
            
            # Simple topic extraction from content
            content_lower = msg.content.lower()
            if any(w in content_lower for w in ['calorie', 'kcal', 'energy']):
                topics.add('calories')
            if any(w in content_lower for w in ['protein', 'amino']):
                topics.add('protein')
            if any(w in content_lower for w in ['weight', 'lose', 'gain']):
                topics.add('weight_management')
            if any(w in content_lower for w in ['meal', 'breakfast', 'lunch', 'dinner']):
                topics.add('meals')
            if any(w in content_lower for w in ['recipe', 'cook', 'prepare']):
                topics.add('recipes')
            if any(w in content_lower for w in ['vitamin', 'mineral', 'nutrient']):
                topics.add('micronutrients')
        
        return list(topics)
    
    def get_mentioned_foods(self) -> List[str]:
        """Extract foods mentioned in conversation."""
        # This would ideally use NER, but simple keyword matching for now
        foods = set()
        common_foods = [
            'banana', 'apple', 'chicken', 'rice', 'bread', 'egg', 'milk',
            'beef', 'fish', 'salmon', 'broccoli', 'spinach', 'oatmeal',
            'yogurt', 'cheese', 'pasta', 'potato', 'avocado', 'nuts'
        ]
        
        for msg in self.messages:
            content_lower = msg.content.lower()
            for food in common_foods:
                if food in content_lower:
                    foods.add(food)
        
        return list(foods)
    
    def create_summary(self) -> ConversationSummary:
        """Create a summary of the current conversation."""
        return ConversationSummary(
            session_id=self.session_id,
            start_time=self.session_start,
            end_time=datetime.now(),
            message_count=len(self.messages),
            topics=self.get_recent_topics(),
            key_points=self._extract_key_points(),
            user_goals_mentioned=self._extract_goals(),
            foods_discussed=self.get_mentioned_foods(),
        )
    
    def _extract_key_points(self) -> List[str]:
        """Extract key points from conversation."""
        key_points = []
        
        for msg in self.messages:
            if msg.role == "assistant" and msg.intent:
                # Summarize assistant responses by intent
                if msg.intent == "nutrition":
                    key_points.append(f"Nutrition info provided")
                elif msg.intent == "science":
                    key_points.append(f"Scientific evidence shared")
                elif msg.intent == "meal_log":
                    key_points.append(f"Meal logged")
        
        return key_points[:5]  # Limit to 5 key points
    
    def _extract_goals(self) -> List[str]:
        """Extract user goals mentioned in conversation."""
        goals = []
        goal_keywords = {
            'lose weight': 'weight_loss',
            'gain muscle': 'muscle_gain',
            'eat healthy': 'healthy_eating',
            'more energy': 'energy',
            'better sleep': 'sleep',
            'reduce sugar': 'reduce_sugar',
        }
        
        for msg in self.messages:
            if msg.role == "user":
                content_lower = msg.content.lower()
                for phrase, goal in goal_keywords.items():
                    if phrase in content_lower:
                        goals.append(goal)
        
        return list(set(goals))
    
    def clear(self):
        """Clear current session memory."""
        # Save summary before clearing
        if self.messages:
            self.summaries.append(self.create_summary())
        
        self.messages.clear()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start = datetime.now()
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        return {
            "session_id": self.session_id,
            "session_start": self.session_start.isoformat(),
            "current_messages": len(self.messages),
            "max_messages": self.max_messages,
            "past_sessions": len(self.summaries),
            "topics_discussed": self.get_recent_topics(),
        }
    
    def to_json(self) -> str:
        """Export memory as JSON."""
        return json.dumps({
            "session_id": self.session_id,
            "messages": [m.to_dict() for m in self.messages],
            "summaries": [s.to_dict() for s in self.summaries],
        }, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ConversationMemory":
        """Load memory from JSON."""
        data = json.loads(json_str)
        memory = cls()
        memory.session_id = data.get("session_id", memory.session_id)
        
        for msg_data in data.get("messages", []):
            memory.messages.append(Message.from_dict(msg_data))
        
        return memory
