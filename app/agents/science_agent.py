"""
app/agents/science_agent.py

Science Agent

Responsible for:
- Searching scientific papers using Hybrid Search (RAG)
- Responding based on scientific evidence
- Citing sources correctly with evidence grading

Data Sources:
- Pinecone: 88 papers indexed from PubMed/OpenAlex (5366 chunks)
- BM25: Local sparse search over paper chunks

Implemented patterns:
- ReAct (Yao et al., 2023): Think → Act → Observe loop
- RAG (Lewis et al., 2020): Retrieval-Augmented Generation
- Hybrid Search: Dense (semantic) + Sparse (BM25)
- Evidence Grading: A/B/C/D classification

Output Structure:
- evidence_strength: Classification of evidence quality
- citations: List of papers with proper attribution
- uncertainties: Explicit acknowledgment of limitations
- conflicts: Contradictory findings noted

Tools:
- search_scientific_papers: Hybrid search in Pinecone + BM25
- get_paper_details: Details of a specific paper
"""

from __future__ import annotations

from typing import List

from langchain_core.tools import BaseTool

from app.agents.base_agent import BaseAgent, AgentResponse, TaskType, EvidenceLevel
from app.tools.search_tools import SEARCH_TOOLS


class ScienceAgent(BaseAgent):
    """
    Agent specialized in scientific evidence with evidence grading.
    
    Uses Hybrid Search (Dense + BM25) to find relevant papers
    and grades evidence according to established criteria.
    
    Evidence Levels:
    - A (High): Multiple RCTs, meta-analyses, systematic reviews
    - B (Moderate): Single RCT, well-designed cohort studies
    - C (Low): Observational studies, case-control studies
    - D (Very Low): Case reports, expert opinion, limited data
    - N (None): No evidence found in database
    """
    
    def __init__(self):
        super().__init__(
            name="ScienceAgent",
            description="Searches and grades scientific evidence on nutrition",
            model="gpt-4o-mini",
            task_type=TaskType.ANALYSIS,  # Low temperature for accuracy
            max_iterations=3,  # Reduced for faster, more consistent responses
        )
    
    def get_system_prompt(self) -> str:
        return """You are a scientific evidence synthesizer specializing in nutrition research.

WORKFLOW:
1. Use search_scientific_papers to find relevant studies
2. Analyze the papers returned - extract ALL specific data from the Key Findings
3. Synthesize findings into a structured response WITH SPECIFIC DATA

CRITICAL RULES:
• ONLY cite papers returned by the search tool - NEVER invent citations
• EXTRACT ALL NUMBERS from papers: percentages, sample sizes, p-values, confidence intervals
• Quote specific findings directly when they contain data
• Be honest about evidence limitations
• DO NOT include a "Sources" section - sources are shown separately in the UI

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESPONSE FORMAT:

## Quick Answer

[2-3 sentences with the KEY TAKEAWAY. Include the most important number/statistic. Be direct.]

## What the Research Shows

NUMBER each paper like this:

**1. [First Author] et al. ([Year])** - "[Paper Title]"

This study [type: RCT/review/meta-analysis/observational] examined [what] in [population, sample size]. 

Key findings:
- [Finding 1 with specific numbers: "X% reduction in Y (p=Z)"]
- [Finding 2 with specific numbers]
- [Mechanism or explanation if provided]

**2. [First Author] et al. ([Year])** - "[Paper Title]"

[Continue with same format...]

## Practical Takeaways

• [Actionable point 1 - be specific about doses, timing, or frequency if mentioned]
• [Actionable point 2]
• [Who benefits most / who should be cautious]

## Evidence Gaps

[What we still don't know / limitations of current research]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STYLE:
- Use **bold** for paper numbers and author names
- Use bullet points for key findings
- Include ALL numbers from the papers
- DO NOT use --- separators between papers
- Be thorough but concise
- NO emojis
- NO "feel free to ask"
- Academic but accessible"""
    
    def get_tools(self) -> List[BaseTool]:
        return SEARCH_TOOLS
    
    def run(self, user_input: str, context: dict = None) -> AgentResponse:
        """
        Execute the science agent with evidence grading.
        """
        lower_input = user_input.lower()
        
        # Terms that indicate scientific research
        science_triggers = [
            "studies", "evidence", "papers", "articles",
            "research", "scientific", "investigation",
            "what does research say", "according to science"
        ]
        
        # If no explicit science context, add it
        if not any(t in lower_input for t in science_triggers):
            user_input = f"Search scientific studies and provide evidence-graded response about: {user_input}"
        
        return super().run(user_input, context)


# ============================================================
# HELPER FUNCTION FOR LANGGRAPH USE
# ============================================================

# Global instance (singleton)
_science_agent = None

def get_science_agent() -> ScienceAgent:
    """Returns singleton instance of ScienceAgent."""
    global _science_agent
    if _science_agent is None:
        _science_agent = ScienceAgent()
    return _science_agent


def run_science_agent(user_input: str, context: dict = None) -> AgentResponse:
    """Helper function to execute the agent."""
    agent = get_science_agent()
    return agent.run(user_input, context)
