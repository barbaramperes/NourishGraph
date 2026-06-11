"""
app/agents/chat_agent.py

Chat Agent

Responsible for:
- General conversations about nutrition
- Responses when specific tools are not needed
- Greetings and social interactions
- General nutritional education

This agent does NOT use tools, only the LLM directly.
It's the fallback when the question doesn't require scientific research,
calculations, or profile management.

Important: For nutrition/medical questions, redirects to specialized agents.
"""

from __future__ import annotations

from typing import List, Dict, Any

from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base_agent import BaseAgent, AgentResponse, TaskType


class ChatAgent(BaseAgent):
    """
    General conversation agent about nutrition.
    
    Acts as a controlled fallback that:
    - Handles greetings and social interactions
    - Provides general nutrition education
    - Redirects specific queries to appropriate agents
    
    Does NOT handle:
    - Medical/clinical questions (redirect to professional)
    - Specific calculations (redirect to NutritionAgent)
    - Scientific claims (redirect to ScienceAgent)
    """
    
    def __init__(self):
        super().__init__(
            name="ChatAgent",
            description="General nutrition conversation and education",
            model="gpt-4o-mini",
            task_type=TaskType.CONVERSATION,
            max_iterations=1,
        )
    
    def get_system_prompt(self) -> str:
        return """You are a knowledgeable nutrition assistant for general guidance.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESPONSE FORMAT:

## [Topic/Answer]

[Direct answer in 2-3 sentences. Be specific and actionable.]

### Why This Matters

[Brief explanation of the reasoning - 2-3 sentences. Explain WHY, not just WHAT.]

### In Practice

• [Actionable recommendation 1]
• [Actionable recommendation 2]

*Note: [Brief caveat about individual variation if relevant]*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STYLE RULES:
• Be educational: explain reasoning
• Be balanced: avoid absolute claims
• Be practical: focus on actionable advice
• Be concise: 150-250 words maximum
• NO emojis
• NO "feel free to ask" or similar phrases
• NO excessive hedging

SCOPE LIMITS:
• Specific calculations → defer to system (it will route automatically)
• Scientific literature → defer to system (it will route automatically)
• Medication dosages, prescriptions, diagnosis → recommend healthcare provider
• Eating disorders → recommend professional support
• Supplement questions (even when medication is mentioned) → ANSWER the nutrition question, then add a brief note to consult their doctor about interactions. Do NOT refuse to answer.

AMBIGUOUS QUERIES — IMPORTANT:
If the user's question is vague or could apply to many topics (not clearly about nutrition/food/health):
• Do NOT guess or try to answer with loosely related nutrition info
• Ask for clarification by connecting to nutrition: "Could you clarify your question? For example, are you asking about [nutrition-related interpretation]? I'm here to help with nutrition, diet, and healthy eating!"
• Examples of ambiguous queries and how to handle them:
  - "How does extraction affect quality?" → "Are you asking about food extraction methods (like cold-pressed oils, juice extraction, or coffee extraction)? I'd be happy to explain how different processing methods affect nutritional quality!"
  - "What are the best practices?" → "Are you asking about best practices for nutrition, meal planning, or healthy eating? Let me know and I'll help!"
  - "How does processing work?" → "Are you asking about food processing and how it affects nutrients? I can explain that!"

OFF-TOPIC / OUT OF SCOPE — CRITICAL:
You are EXCLUSIVELY a nutrition and health assistant. If the user asks about ANY topic NOT related to nutrition, food, diet, health, fitness, supplements, or wellness:
• Do NOT answer the off-topic question
• Politely redirect: acknowledge their question briefly, then say you're specialized in nutrition and offer to help with that instead
• Example: "That's an interesting question, but I'm specialized in nutrition and healthy eating! I'd love to help you with meal suggestions, dietary advice, or nutritional information. What can I help you with?"
• This applies to: sports predictions, politics, entertainment, coding, math, geography, history, jokes, trivia, creative writing, and ANY other non-nutrition topic

Keep responses informative, practical, and direct."""
    
    def get_tools(self) -> List[BaseTool]:
        """ChatAgent does not use tools."""
        return []
    
    def _should_redirect(self, user_input: str) -> tuple[bool, str]:
        """Check if query should be redirected to a specialized agent."""
        lower = user_input.lower()
        
        # Calculation triggers
        calc_triggers = [
            "calculate", "how many calories", "what's my bmr",
            "what's my tdee", "macro", "how much protein"
        ]
        if any(t in lower for t in calc_triggers):
            return True, "calculation"
        
        # Science triggers
        science_triggers = [
            "studies", "research", "evidence", "scientific",
            "what does research say", "according to science"
        ]
        if any(t in lower for t in science_triggers):
            return True, "science"
        
        # Profile triggers
        profile_triggers = [
            "i weigh", "i'm", "my age", "save my",
            "update my profile", "i ate", "log meal"
        ]
        if any(t in lower for t in profile_triggers):
            return True, "profile"
        
        return False, ""
    
    def run(self, user_input: str, context: dict = None) -> AgentResponse:
        """Execute the chat agent with redirect detection."""
        context = context or {}
        user_profile = context.get("user_profile", {})
        
        # Check for redirect
        should_redirect, redirect_type = self._should_redirect(user_input)
        if should_redirect:
            # Add hint for router to pick up
            return AgentResponse(
                content=f"[REDIRECT:{redirect_type}] This query would be better handled by a specialized agent.",
                metadata={"redirect_suggested": redirect_type},
                confidence=0.5,  # Low confidence signals potential routing issue
            )
        
        # Build personalized context
        personal_context = ""
        if user_profile:
            parts = []
            if user_profile.get("name"):
                parts.append(f"Name: {user_profile['name']}")
            if user_profile.get("goal"):
                parts.append(f"Goal: {user_profile['goal']}")
            if parts:
                personal_context = f"\n\n[User context: {', '.join(parts)}]"
        
        # Add conversation history for follow-up awareness
        conversation_context = ""
        if context.get("conversation_summary"):
            conversation_context = f"\n\n[Previous conversation:\n{context['conversation_summary']}]"
        
        # System prompt with context
        system_prompt = self.get_system_prompt()
        if personal_context:
            system_prompt += personal_context
        
        # Generate response with conversation context
        full_input = user_input
        if conversation_context:
            full_input = f"{user_input}{conversation_context}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=full_input)
        ]
        
        response = self.llm.invoke(messages)
        
        return AgentResponse(
            content=response.content,
            tools_used=[],
            reasoning_steps=["Direct response without tools"],
            confidence=0.75,
            metadata={"agent_type": "chat"}
        )


# ============================================================
# HELPER FUNCTION FOR LANGGRAPH
# ============================================================

_chat_agent = None

def get_chat_agent() -> ChatAgent:
    """Returns singleton ChatAgent instance."""
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent()
    return _chat_agent


def run_chat_agent(user_input: str, context: dict = None) -> AgentResponse:
    """Helper function para executar o agente."""
    agent = get_chat_agent()
    return agent.run(user_input, context)