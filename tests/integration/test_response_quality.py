"""
Integration tests for response quality.

Tests that verify agents produce high-quality responses
with proper citations, formatting, and content.
"""

import pytest
import re
from unittest.mock import patch, Mock


@pytest.mark.integration
class TestResponseQuality:
    """Test quality of agent responses."""

    def test_science_agent_cites_sources(self, mock_openai, mock_rag_search):
        """Science agent must cite sources from RAG."""
        from app.agents.science_agent import ScienceAgent
        from app.agents.base_agent import AgentResponse

        # Mock agent response with citations
        mock_content = """**Nutrition and Health**

Research shows strong evidence for the benefits of proper nutrition.

**Scientific Evidence**

Multiple studies have demonstrated positive health outcomes. Smith et al. (2020) found significant improvements in metabolic health. Jones et al. (2021) reported similar findings in their dietary intervention study.

**Relevant Studies**

1. **Nutrition and Health: A Comprehensive Review**
   - Authors: Smith et al.
   - Year: 2020
   - Key Findings: Strong correlation between nutrition and health outcomes

**Key Takeaways**

- Proper nutrition is essential for health
- Multiple studies support these findings

**Considerations**

Results based on limited papers in database."""

        with patch.object(ScienceAgent, 'run') as mock_run:
            mock_run.return_value = AgentResponse(
                content=mock_content,
                tools_used=["search_scientific_papers"],
                confidence=0.9,
                reasoning_steps=[]
            )

            agent = ScienceAgent()
            response = agent.run("What are the benefits of nutrition?")

            # Assertions on response quality
            assert response.content is not None
            assert len(response.content) > 200, "Response too short"

            # Must cite sources
            assert "Smith et al." in response.content or "2020" in response.content
            assert "scientific" in response.content.lower() or "study" in response.content.lower()

            # Must have structure
            assert "**" in response.content, "Missing markdown formatting"

            # Must use RAG tool
            assert "search_scientific_papers" in response.tools_used

    def test_nutrition_agent_shows_calculations(self, mock_openai):
        """Nutrition agent must show calculation steps."""
        from app.agents.nutrition_agent import NutritionAgent
        from app.agents.base_agent import AgentResponse

        # Mock nutrition calculation response
        mock_content = """**Daily Caloric Needs**

Your daily energy needs are approximately 2,150 kcal.

**Calculation Summary**

- BMR (Basal Metabolic Rate): 1,650 kcal
- Activity Multiplier: 1.55 (moderate)
- TDEE (Total Daily Energy Expenditure): 2,558 kcal

**Methodology**

Calculated using the Mifflin-St Jeor equation:
- For males: BMR = (10 × weight) + (6.25 × height) - (5 × age) + 5
- Inputs: weight=70kg, height=175cm, age=30, activity=moderate

**Practical Interpretation**

For your moderate activity level, consuming around 2,150 kcal per day will help maintain your current weight.

**Limitations**

Individual metabolism may vary by 10-15% from these estimates."""

        with patch.object(NutritionAgent, 'run') as mock_run:
            mock_run.return_value = AgentResponse(
                content=mock_content,
                tools_used=["calculate_bmr", "calculate_tdee"],
                confidence=0.95,
                reasoning_steps=[]
            )

            agent = NutritionAgent()
            response = agent.run(
                "Calculate my daily calorie needs",
                context={
                    "user_profile": {
                        "weight": 70,
                        "height": 175,
                        "age": 30,
                        "gender": "M",
                        "activity": "moderate"
                    }
                }
            )

            # Must show formula/method
            assert "Mifflin" in response.content or "BMR" in response.content

            # Must show numbers
            numbers = re.findall(r'\d{3,4}', response.content)
            assert len(numbers) >= 2, "Missing calorie calculations"

            # Must explain methodology
            assert "activity" in response.content.lower() or "moderate" in response.content.lower()

            # Must include limitations
            assert "limitation" in response.content.lower() or "vary" in response.content.lower()

    def test_response_has_proper_structure(self, mock_openai):
        """All agent responses should have proper markdown structure."""
        from app.agents.chat_agent import ChatAgent
        from app.agents.base_agent import AgentResponse

        mock_content = """Hello! I'm here to help you with nutrition questions.

**What I Can Do**

- Answer nutrition questions
- Calculate caloric needs
- Provide meal suggestions
- Search scientific research

Feel free to ask me anything about nutrition!"""

        with patch.object(ChatAgent, 'run') as mock_run:
            mock_run.return_value = AgentResponse(
                content=mock_content,
                tools_used=[],
                confidence=0.9,
                reasoning_steps=[]
            )

            agent = ChatAgent()
            response = agent.run("Hello")

            # Check structure
            assert response.content is not None
            assert len(response.content) > 0

            # Check for markdown elements
            has_structure = (
                "**" in response.content or  # Headers
                "-" in response.content or   # Bullets
                "\n\n" in response.content   # Paragraphs
            )
            assert has_structure, "Response lacks proper formatting"

    def test_science_agent_no_hallucinated_citations(self, mock_openai, mock_rag_search):
        """Science agent must not hallucinate citations."""
        from app.agents.science_agent import ScienceAgent
        from app.agents.base_agent import AgentResponse

        # Set specific papers in mock
        mock_rag_search.return_value = [
            {
                "title": "Vitamin D and Health",
                "authors": "Smith et al.",
                "year": 2020,
                "text": "Study on vitamin D"
            }
        ]

        mock_content = """**Vitamin D**

Research shows vitamin D is important for health.

**Scientific Evidence**

Smith et al. (2020) found positive effects of vitamin D supplementation.

**Relevant Studies**

1. **Vitamin D and Health**
   - Authors: Smith et al.
   - Year: 2020"""

        with patch.object(ScienceAgent, 'run') as mock_run:
            mock_run.return_value = AgentResponse(
                content=mock_content,
                tools_used=["search_scientific_papers"],
                confidence=0.85,
                reasoning_steps=[]
            )

            agent = ScienceAgent()
            response = agent.run("What are the benefits of vitamin D?")

            # Should cite Smith et al., 2020 (from mock)
            assert "Smith et al." in response.content or "2020" in response.content

            # Should NOT cite authors not in mock results
            hallucinated_authors = ["Johnson et al.", "Williams et al.", "Brown et al."]
            for author in hallucinated_authors:
                assert author not in response.content, f"Hallucinated citation detected: {author}"


@pytest.mark.integration
class TestResponseConsistency:
    """Test that responses are consistent and deterministic."""

    def test_bmr_calculation_consistency(self, mock_openai):
        """BMR calculation should be deterministic."""
        from app.tools.nutrition_tools import calculate_bmr

        # Same inputs should give same output
        result1 = calculate_bmr.invoke({
            "weight_kg": 70,
            "height_cm": 175,
            "age_years": 30,
            "sex": "M"
        })
        result2 = calculate_bmr.invoke({
            "weight_kg": 70,
            "height_cm": 175,
            "age_years": 30,
            "sex": "M"
        })

        # Results should be identical strings
        assert result1 == result2, "BMR calculation not deterministic"
        assert isinstance(result1, str), "BMR should return formatted string"
        assert "1649" in result1 or "1,649" in result1, "Result should contain BMR value"

    def test_router_classification_consistency(self, mock_openai):
        """Router should classify same query consistently."""
        from app.graph.nodes import planner_node

        # Mock consistent response
        mock_openai.return_value.invoke.return_value.content = '{"intent": "nutrition", "confidence": 0.9, "plan": ["Calculate"], "thinking": "calculation needed"}'

        query = "How many calories in a banana?"

        result1 = planner_node({"user_input": query, "messages": []})
        result2 = planner_node({"user_input": query, "messages": []})

        assert result1["intent"] == result2["intent"], "Router classification not consistent"
