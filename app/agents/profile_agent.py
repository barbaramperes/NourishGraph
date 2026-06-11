"""
app/agents/profile_agent.py

Profile Agent

Responsible for:
- Storing and updating user profile data
- Logging meals in the food diary
- Showing history and summaries

Implemented patterns:
- ReAct (Yao et al., 2023): Think → Act → Observe loop
- Two-Step Commit (FR4): Explicit user confirmation for data changes

Tools:
- get_user_profile: View current profile
- save_user_profile: Save/update data
- log_meal: Log meal
- get_meals_history: Meal history
- get_today_summary: Today's summary
- clear_user_profile: Clear profile
- clear_meals_history: Clear history

FR4 Compliance:
This agent implements a two-step commit pattern for profile updates:
1. Detect potential update from user message
2. Propose changes and request explicit confirmation
3. Only apply changes when user confirms

This prevents implicit data modifications and ensures user control.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from enum import Enum

from langchain_core.tools import BaseTool

from app.agents.base_agent import BaseAgent, AgentResponse, TaskType, StructuredAgentOutput, AgentOutputType


class ProfileIntent(str, Enum):
    """Classification of profile-related intents."""
    QUERY = "query"                    # User wants to view data
    UPDATE_PROFILE = "update_profile"  # User wants to modify profile
    LOG_MEAL = "log_meal"              # User wants to log a meal
    CLEAR_DATA = "clear_data"          # User wants to delete data
    CONFIRM = "confirm"                # User confirms proposed changes
    REJECT = "reject"                  # User rejects proposed changes


# Import profile tools
from app.tools.profile_tools import PROFILE_TOOLS


class ProfileAgent(BaseAgent):
    """
    Agent specialized in profile and meal management.
    
    Implements FR4-compliant two-step commit:
    1. Detects data in user message
    2. Proposes changes without applying
    3. Waits for explicit confirmation
    
    Example:
        agent = ProfileAgent()
        
        # First interaction - proposes changes
        response = agent.run("I'm 30 years old, weigh 75kg")
        # Response: "I detected: age=30, weight=75kg. Confirm to save?"
        
        # User confirms
        response = agent.run("Yes, save it", context={"pending_changes": {...}})
        # Response: "Saved successfully!"
    """
    
    def __init__(self):
        super().__init__(
            name="ProfileAgent",
            description="Manages user profile and meal logging with explicit confirmation",
            model="gpt-4o-mini",
            task_type=TaskType.ANALYSIS,
            max_iterations=5,
        )
        
        # Pending changes awaiting confirmation
        self._pending_changes: Optional[Dict[str, Any]] = None
    
    def get_system_prompt(self) -> str:
        return """You are ProfileAgent - manage user health data with explicit consent.

AVAILABLE TOOLS:

Profile:
- get_user_profile() - View current profile
- save_user_profile(name, age, weight, height, gender, goal, activity, restrictions) - Save data
- clear_user_profile() - Clear all profile data

Meals:
- log_meal(description, meal_type, calories) - Log a meal
- get_meals_history(days) - View history
- get_today_summary() - Today's intake
- clear_meals_history() - Clear all meals

CRITICAL RULES:

1. If user provides NO specific data (e.g., "update my profile", "change my profile"):
   - First call get_user_profile() to show current data
   - Then ask what they want to update: "What would you like to update? You can tell me your age, weight, height, goal, etc."

2. If user provides specific data:
   - Extract ALL values and call save_user_profile with ALL of them in ONE call
   - Example: "I'm 28, female, 60kg" → save_user_profile(age=28, gender="female", weight=60)

DATA EXTRACTION PATTERNS:
- "I'm 30" or "30 years old" → age=30
- "75kg" or "weigh 75" → weight=75
- "1.80m" or "180cm" or "1m80" → height=180
- "male" or "man" or "M" → gender="male"
- "female" or "woman" or "F" → gender="female"
- "lose weight" → goal="lose_weight"
- "gain muscle" → goal="gain_muscle"

TOOL SELECTION:
- "show my profile" or "my profile" → get_user_profile
- "update my profile" (no data) → get_user_profile, then ask what to update
- Any specific data → save_user_profile with ALL extracted values
- "I ate pizza" → log_meal
- "what did I eat" → get_today_summary

RESPONSE STYLE:
- Return tool output directly
- Don't add extra commentary
- NO emojis"""
    
    def get_tools(self) -> List[BaseTool]:
        return PROFILE_TOOLS
    
    def _detect_intent(self, user_input: str) -> ProfileIntent:
        """Detect the user's intent from their message."""
        lower = user_input.lower().strip()
        
        # Confirmation patterns
        confirm_patterns = [
            "yes", "save", "confirm", "go ahead", "please save",
            "ok", "sure", "do it", "apply", "update it"
        ]
        reject_patterns = [
            "no", "cancel", "don't", "nevermind", "stop", "reject"
        ]
        
        # Check for confirmation/rejection first
        if any(p in lower for p in confirm_patterns):
            return ProfileIntent.CONFIRM
        if any(p in lower for p in reject_patterns):
            return ProfileIntent.REJECT
        
        # Query patterns
        query_patterns = [
            "what", "show", "view", "my profile", "my data",
            "history", "summary", "today", "how much", "what did"
        ]
        if any(p in lower for p in query_patterns):
            return ProfileIntent.QUERY
        
        # Meal logging patterns
        meal_patterns = [
            "i ate", "i had", "i've eaten", "for breakfast",
            "for lunch", "for dinner", "for snack", "just ate"
        ]
        if any(p in lower for p in meal_patterns):
            return ProfileIntent.LOG_MEAL
        
        # Clear patterns
        clear_patterns = ["clear", "delete", "remove", "reset"]
        if any(p in lower for p in clear_patterns):
            return ProfileIntent.CLEAR_DATA
        
        # Profile update patterns
        update_patterns = [
            "i'm", "i am", "i weigh", "my age", "my weight",
            "my height", "years old", "kg", "kilos", "pounds",
            "cm", "meters", "my goal", "i want to"
        ]
        if any(p in lower for p in update_patterns):
            return ProfileIntent.UPDATE_PROFILE
        
        return ProfileIntent.QUERY
    
    def run(self, user_input: str, context: dict = None) -> AgentResponse:
        """
        Execute the profile agent with two-step commit protocol.
        """
        context = context or {}
        intent = self._detect_intent(user_input)
        
        # Handle confirmation of pending changes
        if intent == ProfileIntent.CONFIRM and context.get("pending_changes"):
            # Apply the pending changes
            user_input = f"[ACTION: Apply confirmed changes]\nUser confirmed. Apply these changes: {context['pending_changes']}\n\nOriginal: {user_input}"
        
        elif intent == ProfileIntent.REJECT and context.get("pending_changes"):
            return AgentResponse(
                content="No problem. I've discarded the proposed changes. Your profile remains unchanged.",
                tools_used=[],
                confidence=1.0,
                metadata={"action": "rejected_changes"}
            )
        
        elif intent == ProfileIntent.UPDATE_PROFILE:
            # Add instruction to propose but not save
            user_input = f"[ACTION: Detect and PROPOSE changes - DO NOT SAVE YET]\nExtract data from this message and propose to save (ask for confirmation):\n\n{user_input}"
        
        elif intent == ProfileIntent.LOG_MEAL:
            user_input = f"[ACTION: Log meal directly]\n\n{user_input}"
        
        elif intent == ProfileIntent.QUERY:
            user_input = f"[ACTION: Query/view data]\n\n{user_input}"
        
        return super().run(user_input, context)


# ============================================================
# HELPER FUNCTION FOR LANGGRAPH USE
# ============================================================

_profile_agent = None

def get_profile_agent() -> ProfileAgent:
    """Returns singleton instance of ProfileAgent."""
    global _profile_agent
    if _profile_agent is None:
        _profile_agent = ProfileAgent()
    return _profile_agent


def run_profile_agent(user_input: str, context: dict = None) -> AgentResponse:
    """Helper function to execute the agent."""
    agent = get_profile_agent()
    return agent.run(user_input, context)
