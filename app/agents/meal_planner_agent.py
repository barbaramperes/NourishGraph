"""
app/agents/meal_planner_agent.py

Meal Planner Agent

Responsible for:
- Generating personalized meal plans
- Creating grocery lists
- Suggesting foods based on goals
- Recipe recommendations

Implemented patterns:
- ReAct (Yao et al., 2023): Think → Act → Observe loop
- Constraint Validation: Hard constraints (allergies) validated before output

Output Structure:
- daily_targets: Calorie and macro targets
- meal_plan: List of meals by type
- shopping_list: Organized ingredient list
- constraint_checks: Validation of restrictions

Tools:
- generate_meal_plan: Creates daily/weekly meal plans
- suggest_foods_for_goal: Food recommendations
- generate_grocery_list: Shopping list generation
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from langchain_core.tools import BaseTool

from app.agents.base_agent import BaseAgent, AgentResponse, TaskType
from app.tools.meal_planning_tools import (
    generate_meal_plan,
    suggest_foods_for_goal,
    generate_grocery_list,
)


class MealPlannerAgent(BaseAgent):
    """
    Agent specialized in meal planning and food recommendations.
    
    Creates personalized meal plans with:
    - Constraint validation (allergies, restrictions)
    - Structured output format
    - Professional clinical tone
    
    Validation Flow:
    1. Calculate calorie/macro targets from profile
    2. Generate meal plan
    3. Validate against restrictions/allergies
    4. If validation fails, regenerate with constraints
    """
    
    def __init__(self):
        super().__init__(
            name="MealPlannerAgent",
            description="Creates personalized meal plans with constraint validation",
            model="gpt-4o-mini",
            task_type=TaskType.CREATIVE,  # Higher temperature for variety
            max_iterations=5,
        )
    
    def get_system_prompt(self) -> str:
        return """You create personalized nutrition guidance based on user goals.

AVAILABLE TOOLS:
1. generate_meal_plan(target_calories, goal, days, dietary_restrictions, diet_type)
   - diet_type: CRITICAL! Pass the user's diet type (carnivore, keto, vegan, vegetarian, mediterranean, etc.)
2. suggest_foods_for_goal(goal, category)
3. generate_grocery_list(days, servings)

=== CRITICAL: DIET TYPE RULES ===

You MUST respect the user's diet type in ALL responses:

- **vegetarian**: NO meat (chicken, beef, pork, fish, seafood, bacon)
- **vegan**: NO animal products (meat, fish, dairy, eggs, honey)
- **carnivore**: ONLY animal products (meat, fish, eggs, dairy)
- **keto**: Very low carbs (<20g/day), high fat
- **mediterranean**: Focus on fish, olive oil, vegetables, legumes

When suggesting foods WITHOUT using tools, you MUST filter suggestions based on diet type.
For example, if user is vegetarian and asks for "high-protein dinner":
- GOOD: tofu, tempeh, legumes, eggs, cheese, greek yogurt
- BAD: chicken, fish, beef (these are MEAT - never suggest for vegetarian!)

=== RESPONSE FORMAT FOR MEAL SUGGESTIONS ===

When suggesting meals (breakfast, lunch, dinner, snacks), ALWAYS include:

1. **Recipe Name** with brief description
2. **Ingredients** with approximate quantities
3. **Quick Instructions** (3-5 simple steps)
4. **Nutritional Highlights** (key nutrients and benefits)
5. **Preparation Time** (quick/medium/longer)

Example format for a breakfast suggestion:

---

## Scrambled Eggs with Bacon and Cheese

A protein-rich breakfast perfect for your carnivore diet.

**Ingredients:**
- 3 large eggs
- 3 strips of bacon (about 60g)
- 30g cheddar cheese, shredded
- 1 tbsp butter
- Salt and pepper to taste

**Instructions:**
1. Cook bacon in a pan over medium heat until crispy (5-6 min). Set aside.
2. Beat eggs in a bowl with a pinch of salt and pepper.
3. Melt butter in the same pan, add eggs, and stir gently.
4. When almost set, add cheese and fold until melted.
5. Serve with crispy bacon on the side.

**Nutritional Highlights:**
- ~35g protein for muscle maintenance
- Rich in B12, choline, and healthy fats
- Zero carbs, perfect for carnivore diet

**Prep Time:** 10 minutes

---

=== CRITICAL: TOOL USAGE RULES ===

**NEVER use tools for these situations:**
- User says "I don't like X" → Respond with substitutions (NO TOOLS)
- User expresses a food preference → Acknowledge and suggest alternatives (NO TOOLS)
- User says "I prefer X over Y" → Note the preference (NO TOOLS)
- User asks about a specific food → Answer directly (NO TOOLS)
- User asks for a quick suggestion (e.g., "suggest a dinner") → Give ONE detailed recipe (NO TOOLS)
- User asks for breakfast/lunch/dinner ideas → Give the exact number requested, or 1 if not specified (NO TOOLS)

**IMPORTANT: Respect quantity requests**
- If user says "suggest A meal" → Give exactly 1 option
- If user says "suggest SOME meals" or "suggest meals" (plural) → Give 2-3 options
- If user says "suggest 5 options" → Give exactly 5 options
- Default to 1 option unless user explicitly asks for multiple

**ONLY use tools when:**
- User explicitly says "create a meal plan", "make me a plan", "plan my meals"
- User asks for a grocery/shopping list
- User asks "what foods help with [goal]" → use suggest_foods_for_goal

=== RESPONSE FORMATS ===

**For food preference/dislike (e.g., "I don't like asparagus"):**
DO NOT USE TOOLS. Respond directly like this:

That's easy to adjust. Asparagus was included for its fiber and folate content, but there are excellent alternatives:

**Substitutions:**
- Broccoli (similar fiber, vitamin C, folate)
- Green beans (mild flavor, similar nutrients)
- Zucchini (versatile, lower carbs)

These maintain the nutritional value while respecting your preference.

**Would you like me to:**
- Update your profile to remember this preference?
- See a revised version of your current meal?

---

**For new plan requests (e.g., "Create a meal plan for me"):**
Use the generate_meal_plan tool, then return the tool output EXACTLY as is.
DO NOT add extra headers, DO NOT add "Feel free to ask", DO NOT add any text after the tool output.

STRICT RULES:
- NO emojis in your responses
- NO horizontal dividers (---) between recipes or sections
- Return tool outputs exactly as they are - do not modify or add to them
- NO "Feel free to ask" or "Let me know if you need anything"
- NO offers for follow-up at the end
- When presenting tool output, just present it - nothing before or after
- Use headers (##) and line breaks to separate sections, NOT horizontal rules (---)"""
    
    def get_tools(self) -> List[BaseTool]:
        return [
            generate_meal_plan,
            suggest_foods_for_goal,
            generate_grocery_list,
        ]
    
    def run(self, user_input: str, context: dict = None) -> AgentResponse:
        """
        Execute the meal planner with constraint validation.
        """
        context = context or {}
        user_profile = context.get("user_profile", {})
        
        # ============================================================
        # MINIMAL RESPONSE PRINCIPLE: Detect food preferences
        # If user just expresses a food preference, respond directly
        # WITHOUT calling any tools (no full meal plan generation)
        # ============================================================
        preference_patterns = [
            "don't like", "dont like", "não gosto", "nao gosto",
            "hate", "dislike", "can't stand", "cant stand",
            "prefer not", "avoid", "allergic to", "intolerant to",
            "i prefer", "eu prefiro", "não quero", "nao quero"
        ]
        
        user_lower = user_input.lower()
        is_preference = any(pattern in user_lower for pattern in preference_patterns)
        
        # Check it's NOT a plan request
        plan_patterns = ["meal plan", "weekly plan", "create a plan", "make me a plan", 
                        "plano semanal", "plano alimentar", "cria um plano"]
        is_plan_request = any(pattern in user_lower for pattern in plan_patterns)
        
        if is_preference and not is_plan_request:
            # Respond directly with substitution - NO TOOLS
            return self._handle_food_preference(user_input, context)
        
        # Extract constraints for validation
        constraints = []
        if user_profile.get("allergies"):
            constraints.append(f"Allergies: {user_profile['allergies']}")
        if user_profile.get("dietary_restrictions"):
            constraints.append(f"Restrictions: {user_profile['dietary_restrictions']}")
        if user_profile.get("medical_conditions"):
            constraints.append(f"Medical: {user_profile['medical_conditions']}")
        
        # CRITICAL: Get diet type from 'diet' field OR 'restrictions' list
        diet_type = (user_profile.get("diet") or "").lower()
        if not diet_type:
            restrictions = user_profile.get("restrictions") or []
            if isinstance(restrictions, list) and restrictions:
                # Check if any restriction is a diet type
                diet_keywords = ["carnivore", "vegan", "vegetarian", "keto", "mediterranean", "paleo", "pescatarian"]
                for r in restrictions:
                    if r and r.lower() in diet_keywords:
                        diet_type = r.lower()
                        break
        
        if diet_type:
            user_input = f"{user_input}\n\n[CRITICAL: User follows a {diet_type.upper()} diet. ALWAYS pass diet_type='{diet_type}' to generate_meal_plan. DO NOT suggest any foods incompatible with this diet.]"
        
        # Add constraint context to input
        if constraints:
            constraint_str = " | ".join(constraints)
            user_input = f"{user_input}\n\n[HARD CONSTRAINTS - Must be validated: {constraint_str}]"
        
        return super().run(user_input, context)
    
    def _handle_food_preference(self, user_input: str, context: dict) -> AgentResponse:
        """
        Handle food preferences with minimal response - no tools.
        This implements the Minimal Response Principle from the thesis.
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        preference_prompt = """You help users with food preferences. The user has expressed a food preference or dislike.

RULES:
1. DO NOT generate a meal plan
2. DO NOT use any tools
3. Respond with a SHORT, helpful message (under 150 words)
4. Suggest 2-3 alternatives for the food they don't like
5. Explain briefly why these alternatives work (similar nutrients)
6. Offer to update their profile or adjust a specific meal if needed

FORMAT:
That's easy to adjust. [Food] provides [nutrients], so good alternatives include:

- **[Alternative 1]** - [brief reason]
- **[Alternative 2]** - [brief reason]  
- **[Alternative 3]** - [brief reason]

Would you like me to:
- Remember this preference for future recommendations?
- See an adjusted version of a specific meal?

NO emojis. Professional tone."""

        messages = [
            SystemMessage(content=preference_prompt),
            HumanMessage(content=user_input)
        ]
        
        response = self.llm.invoke(messages)
        
        return AgentResponse(
            content=response.content,
            tools_used=[],
            confidence=0.9,
            metadata={"response_type": "minimal_preference"}
        )


# Singleton instance
_agent_instance = None

def get_meal_planner_agent() -> MealPlannerAgent:
    """Returns the singleton MealPlannerAgent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = MealPlannerAgent()
    return _agent_instance
