"""
app/agents/base_agent.py

Base class for all NourishGraph agents.

Implements the ReAct pattern (Reasoning + Acting):
- Think: The agent reasons about what it needs to do
- Act: Executes a tool
- Observe: Analyzes the result
- Repeat: Until it can respond

Reference: Yao et al., 2023 - "ReAct: Synergizing Reasoning and Acting in Language Models"

Improvements (Thesis aligned):
- Structured AgentOutput schema with Pydantic
- Temperature configuration by task type
- Separation of intermediate_trace vs user_response
- Timeout and retry control
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import Runnable
from langgraph.prebuilt import create_react_agent


# ============================================================
# STRUCTURED OUTPUT SCHEMAS (Thesis FR: Structured Responses)
# ============================================================

class EvidenceLevel(str, Enum):
    """Evidence strength classification for scientific claims."""
    HIGH = "A"      # Multiple RCTs, meta-analyses
    MODERATE = "B"  # Single RCT, cohort studies
    LOW = "C"       # Observational, case studies
    VERY_LOW = "D"  # Expert opinion, limited data
    NONE = "N"      # No evidence found


class AgentOutputType(str, Enum):
    """Classification of agent output types."""
    CALCULATION = "calculation"
    RECOMMENDATION = "recommendation"
    ANALYSIS = "analysis"
    INFORMATION = "information"
    CONFIRMATION = "confirmation"
    CLARIFICATION = "clarification"
    ERROR = "error"


class StructuredAgentOutput(BaseModel):
    """
    Structured output contract for all agents.
    
    Ensures consistent output format across agents for:
    - Validation and testing
    - Synthesis by downstream agents
    - UI rendering
    """
    output_type: AgentOutputType = Field(
        default=AgentOutputType.INFORMATION,
        description="Classification of the response type"
    )
    content: str = Field(
        ...,
        description="Main response content for the user"
    )
    summary: Optional[str] = Field(
        default=None,
        description="One-sentence summary for quick display"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data (calculations, values, etc.)"
    )
    evidence_level: Optional[EvidenceLevel] = Field(
        default=None,
        description="Strength of evidence for scientific claims"
    )
    citations: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Source citations with title, authors, year"
    )
    uncertainties: List[str] = Field(
        default_factory=list,
        description="Explicit acknowledgment of limitations/uncertainties"
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions made in calculations/recommendations"
    )
    needs_confirmation: bool = Field(
        default=False,
        description="Whether user confirmation is needed before action"
    )
    proposed_changes: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Changes proposed but not yet applied (for two-step commit)"
    )
    
    class Config:
        use_enum_values = True


# ============================================================
# TASK TYPE CONFIGURATION (Thesis: Temperature by task)
# ============================================================

class TaskType(str, Enum):
    """Task types with specific LLM configurations."""
    CALCULATION = "calculation"    # BMR, TDEE, macros - needs precision
    DECISION = "decision"          # Routing, classification
    ANALYSIS = "analysis"          # Pattern analysis, deficiency detection
    CONVERSATION = "conversation"  # General chat, education
    SYNTHESIS = "synthesis"        # Combining results, final response
    CREATIVE = "creative"          # Meal planning, suggestions


TASK_CONFIGS: Dict[TaskType, Dict[str, Any]] = {
    TaskType.CALCULATION: {
        "temperature": 0.1,
        "max_tokens": 1500,
        "top_p": 0.9,
    },
    TaskType.DECISION: {
        "temperature": 0.2,
        "max_tokens": 500,
        "top_p": 0.9,
    },
    TaskType.ANALYSIS: {
        "temperature": 0.1,  # Lower for more consistent scientific responses
        "max_tokens": 2000,
        "top_p": 0.9,
    },
    TaskType.CONVERSATION: {
        "temperature": 0.5,
        "max_tokens": 1500,
        "top_p": 0.95,
    },
    TaskType.SYNTHESIS: {
        "temperature": 0.4,
        "max_tokens": 2500,
        "top_p": 0.95,
    },
    TaskType.CREATIVE: {
        "temperature": 0.6,
        "max_tokens": 3000,
        "top_p": 0.95,
    },
}


@dataclass
class AgentResponse:
    """
    Complete response from an agent including trace and output.
    
    Separates:
    - content: Final user-facing content
    - structured_output: Validated structured data
    - intermediate_trace: For logging/debugging (not shown to user)
    """
    # User-facing content
    content: str
    structured_output: Optional[StructuredAgentOutput] = None
    
    # Trace/debugging (not for user display)
    tools_used: List[str] = field(default_factory=list)
    reasoning_steps: List[str] = field(default_factory=list)
    intermediate_trace: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    confidence: float = 0.8
    sources: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    processing_time_ms: Optional[int] = None
    
    # Error handling
    error: Optional[str] = None
    is_fallback: bool = False


class BaseAgent(ABC):
    """
    Abstract base class for ReAct agents.
    
    All agents inherit from this class and implement:
    - get_system_prompt(): Agent-specific system prompt
    - get_tools(): List of available tools
    
    The run() method executes the ReAct loop automatically.
    
    Attributes:
        name: Agent name
        description: Description of what the agent does
        llm: Language model to use
        tools: List of tools
        max_iterations: Maximum ReAct iterations
        task_type: Type of task for LLM configuration
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        model: str = "gpt-4o",
        temperature: Optional[float] = None,
        max_iterations: int = 5,
        task_type: TaskType = TaskType.ANALYSIS,
        timeout_seconds: int = 60,
        max_retries: int = 2,
    ):
        self.name = name
        self.description = description
        self.max_iterations = max_iterations
        self.task_type = task_type
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        
        # Get config based on task type
        config = TASK_CONFIGS.get(task_type, TASK_CONFIGS[TaskType.ANALYSIS])
        
        # Allow override of temperature
        final_temperature = temperature if temperature is not None else config["temperature"]
        
        # LLM with task-specific configuration
        self.llm = ChatOpenAI(
            model=model,
            temperature=final_temperature,
            max_tokens=config.get("max_tokens"),
            request_timeout=timeout_seconds,
        )
        
        # Tools (defined by subclass)
        self.tools = self.get_tools()
        
        # ReAct Agent (LangGraph)
        self._react_agent = self._create_react_agent()
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Returns the system prompt specific to this agent.
        
        Should include:
        - Agent role
        - Specific instructions
        - Expected response format
        """
        pass
    
    @abstractmethod
    def get_tools(self) -> List[BaseTool]:
        """
        Returns the list of tools available for this agent.
        """
        pass
    
    def get_task_type(self) -> TaskType:
        """Returns the task type for this agent."""
        return self.task_type

    def _create_react_agent(self) -> Optional[Runnable]:
        """Creates a ReAct agent using LangGraph."""
        if not self.tools:
            return None
            
        return create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=self.get_system_prompt(),
        )
    
    def run(
        self,
        user_input: str,
        context: Dict[str, Any] = None
    ) -> AgentResponse:
        """
        Executes the agent with the ReAct pattern.
        
        Args:
            user_input: User's question/request
            context: Additional context (profile, history, etc.)
        
        Returns:
            AgentResponse with the response and metadata
        """
        import time
        start_time = time.time()
        
        context = context or {}
        
        # Build full input with context
        full_input = self._build_full_input(user_input, context)
        
        # If no tools, use LLM directly
        if not self._react_agent:
            response = self._run_without_tools(full_input)
            response.processing_time_ms = int((time.time() - start_time) * 1000)
            return response
        
        # Execute ReAct agent with retry logic
        for attempt in range(self.max_retries + 1):
            try:
                result = self._react_agent.invoke({
                    "messages": [HumanMessage(content=full_input)]
                })
                
                response = self._parse_react_result(result)
                response.processing_time_ms = int((time.time() - start_time) * 1000)
                return response
            
            except Exception as e:
                if attempt < self.max_retries:
                    continue
                    
                return AgentResponse(
                    content="I encountered an issue processing your request. Please try again.",
                    confidence=0.0,
                    error=str(e),
                    is_fallback=True,
                    metadata={"error": str(e), "attempts": attempt + 1},
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
    
    def _build_full_input(self, user_input: str, context: Dict[str, Any]) -> str:
        """Builds the full input with context."""
        full_input = user_input
        
        # Add conversation context for follow-ups
        if context.get("conversation_summary"):
            full_input = f"{user_input}\n\n[Previous conversation:\n{context['conversation_summary']}]"
        
        if context.get("user_profile"):
            profile = context["user_profile"]
            profile_str = ", ".join([
                f"{k}: {v}" for k, v in profile.items() 
                if v and k not in ("updated", "id", "created_at")
            ])
            if profile_str:
                full_input = f"{full_input}\n\n[User context: {profile_str}]"
        
        return full_input
    
    def _run_without_tools(self, user_input: str) -> AgentResponse:
        """Executes the agent without tools (LLM only)."""
        messages = [
            SystemMessage(content=self.get_system_prompt()),
            HumanMessage(content=user_input)
        ]
        
        response = self.llm.invoke(messages)
        
        return AgentResponse(
            content=response.content,
            tools_used=[],
            confidence=0.7,
        )
    
    def _parse_react_result(self, result: Dict) -> AgentResponse:
        """Extracts information from the ReAct agent result."""
        messages = result.get("messages", [])
        
        # Last message is the final response
        final_content = ""
        if messages:
            final_message = messages[-1]
            final_content = (
                final_message.content 
                if hasattr(final_message, 'content') 
                else str(final_message)
            )
        
        # Extract tools used and reasoning steps
        tools_used = []
        reasoning_steps = []
        intermediate_trace = []
        
        for msg in messages:
            # Tool calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get('name', 'unknown')
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)
                    intermediate_trace.append({
                        "type": "tool_call",
                        "name": tool_name,
                        "args": tc.get('args', {}),
                        "timestamp": datetime.now().isoformat()
                    })
            
            # Reasoning (assistant messages that are not the final one)
            if hasattr(msg, 'content') and msg.content:
                if msg != messages[-1]:
                    reasoning_steps.append(msg.content[:200])
                    intermediate_trace.append({
                        "type": "reasoning",
                        "content": msg.content[:500],
                        "timestamp": datetime.now().isoformat()
                    })
        
        return AgentResponse(
            content=final_content,
            tools_used=tools_used,
            reasoning_steps=reasoning_steps,
            intermediate_trace=intermediate_trace,
            confidence=0.85 if tools_used else 0.7,
        )
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', tools={len(self.tools)}, task_type={self.task_type.value})"
