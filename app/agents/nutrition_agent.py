"""
app/agents/nutrition_agent.py

Nutrition Agent

Responsible for:
- Calculating BMR (Basal Metabolic Rate)
- Calculating TDEE (Total Daily Energy Expenditure)
- Calculating BMI
- Calculating macronutrient distribution
- Food caloric information
- Meal suggestions

Data Sources:
- PostgreSQL: Foods from USDA FoodData Central

Implemented patterns:
- ReAct (Yao et al., 2023): Think → Act → Observe loop
- Structured Output: inputs_used, formula, results, assumptions

Output Standards:
- Calories: Integer (no decimals)
- Macros: 1 decimal place
- BMI: 1 decimal place
- Units always specified

Tools:
- calculate_bmr: Basal Metabolic Rate (Mifflin-St Jeor)
- calculate_tdee: Total Daily Energy Expenditure
- calculate_bmi: Body Mass Index
- calculate_macros: Macronutrient distribution
- get_food_nutrition: Food caloric info from PostgreSQL (USDA data)
- estimate_meal_from_description: Estimate meal calories
- add_meal: Log meal with estimated macros
"""

from __future__ import annotations

from typing import List, Dict, Any

from langchain_core.tools import BaseTool

from app.agents.base_agent import BaseAgent, AgentResponse, TaskType
from app.tools.nutrition_tools import NUTRITION_TOOLS


class NutritionAgent(BaseAgent):
    """
    Agent specialized in nutritional calculations.
    
    Provides precise calculations with:
    - Explicit inputs and assumptions
    - Formula references
    - Standardized units and rounding
    - Honest handling of missing data
    """
    
    def __init__(self):
        super().__init__(
            name="NutritionAgent",
            description="Calculates nutritional needs with precision and transparency",
            model="gpt-4o-mini",
            task_type=TaskType.CALCULATION,  # Low temperature for precision
            max_iterations=5,
        )
    
    def get_system_prompt(self) -> str:
        return """You provide precise nutritional calculations and dietary guidance.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL RULE:
**ALWAYS use tools for calculations. NEVER calculate values yourself.**
**ONLY report the EXACT values returned by the tools.**
**If a tool returns BMR=1569, you MUST write "1569 kcal" - not any other number.**

AVAILABLE TOOLS:
• calculate_bmr(weight_kg, height_cm, age_years, sex) - Basal Metabolic Rate
• calculate_tdee(bmr, activity_level) - Total Daily Energy Expenditure
• calculate_bmi(weight_kg, height_cm) - Body Mass Index
• calculate_macros(tdee, goal, diet_type) - Macronutrient distribution
• get_food_nutrition(food_name, grams) - USDA food database lookup
• estimate_meal_from_description(meal_description, grams_total) - Estimate meal
• add_meal(description, grams_total) - Log meal to profile

QUERY → TOOL MAPPING:
• "calories in X" → get_food_nutrition
• "my BMR" → calculate_bmr
• "how many calories do I need" → calculate_bmr → calculate_tdee
• "my macros" → calculate_macros (include diet_type!)
• "I ate X" → add_meal

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESPONSE FORMAT FOR CALCULATIONS:

## Your Results

| Metric | Value |
|--------|-------|
| BMR | [EXACT value from tool] kcal/day |
| TDEE | [EXACT value from tool] kcal/day |

## How This Was Calculated

Using the Mifflin-St Jeor equation with your data.

**Inputs used:**
• Weight: [X] kg
• Height: [X] cm
• Age: [X] years
• Activity: [level]

## What This Means For You

[2-3 sentences of practical interpretation]

## Important Notes

These are estimates. Monitor your progress and adjust as needed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DIET-AWARE RULES:
• ALWAYS pass diet_type to calculate_macros() when user has a specific diet
• Never recommend foods incompatible with user's diet

FORMATTING RULES:
• Use ONLY the exact numbers from tool outputs
• Calories: integers (2150)
• Macros: 1 decimal (156.5g)
• NO emojis
• Concise: aim for 150-250 words

PROFILE RULES (MANDATORY - FOLLOW EXACTLY):
• The user's profile data is appended to their message with their goal and pre-calculated calorie target.
• ALWAYS use the profile data. NEVER ask the user for information already in their profile.
• When a GOAL and CALORIE TARGET are provided, give advice ONLY for that specific goal.
• DO NOT present multiple scenarios (lose/gain/maintain). The user already chose their goal.
• If goal=lose_weight → advise caloric deficit ONLY
• If goal=gain_muscle → advise caloric surplus ONLY  
• If goal=maintain → advise maintenance ONLY
• NEVER ask "what is your goal?" or "what are you aiming for?" - the goal is already set.
• Only ask for data if it is truly ABSENT from the profile (no value at all).

RESPONSE RELEVANCE RULES:
• ONLY include BMR/TDEE/calorie data when the user's question is specifically about calories, weight goals, macros, or meal planning.
• For general nutrition questions (e.g. food benefits, vitamins, supplements) answer the question directly WITHOUT adding calorie calculations.
• Do NOT include the "Your Results" table or calorie targets unless the user asked about them.
• Match your response to what was asked - do not add unsolicited calorie information.

SUPPLEMENT + MEDICATION QUERIES:
• When users ask about taking supplements with medication, PROVIDE HELPFUL nutritional information about the supplement.
• Share evidence-based benefits, typical dosages, and food sources of the nutrient.
• Add a brief note recommending they consult their doctor about potential interactions.
• Do NOT refuse to answer or say "I can't provide medication advice" — the question is about NUTRITION, not medication.
• Example: Omega-3 fatty acids are beneficial for heart health... Always check with your doctor about potential interactions with your specific medication.
"""
    
    def get_tools(self) -> List[BaseTool]:
        return NUTRITION_TOOLS
    
    def run(self, user_input: str, context: dict = None) -> AgentResponse:
        """
        Execute the nutrition agent with profile context.
        """
        context = context or {}
        user_profile = context.get("user_profile", {})
        
        # Build structured profile data
        profile_data = []
        for field, label in [
            ("weight", "weight_kg"),
            ("height", "height_cm"),
            ("age", "age_years"),
            ("gender", "sex"),
            ("sex", "sex"),
            ("activity", "activity_level"),
            ("goal", "goal"),
            ("diet", "diet_type")  # Include diet type for macro calculations
        ]:
            value = user_profile.get(field)
            if value:
                profile_data.append(f"{label}={value}")
        
        # Pre-calculate BMR/TDEE for consistency
        # Only inject calorie data when the query is actually about calories/weight/diet
        import re
        CALORIE_QUERY = re.compile(
            r'(?:calori\w*|cal[oó]ri\w*|kcal|bmr|tdee|metaboli\w*|energy\s*(?:expenditure|intake|needs)|'
            r'how\s+many\s+calories|quant[ao]s?\s+caloria\w*|'
            r'macros?\b|weight\s*(?:loss|gain|goal)|'
            r'lose\s+weight|gain\s+(?:weight|muscle)|perder\s+peso|ganhar\s+(?:peso|m[uú]sculo)|'
            r'diet\s*(?:plan|target)|meal\s*plan|plano\s*(?:alimentar|de\s*refei)|'
            r'daily\s*(?:intake|target|goal|needs)|'
            r'how\s+much\s+should\s+i\s+eat|quanto\s+devo\s+comer|'
            r'surplus|deficit|maintenance|manuten[çc][aã]o)',
            re.IGNORECASE
        )
        is_calorie_query = bool(CALORIE_QUERY.search(user_input))
        
        pre_calc = ""
        weight = user_profile.get("weight")
        height = user_profile.get("height")
        age = user_profile.get("age")
        gender = user_profile.get("gender") or user_profile.get("sex")
        activity = user_profile.get("activity", "moderate")
        
        if weight and height and age and is_calorie_query:
            is_male = gender and str(gender).upper().startswith("M")
            bmr_base = 10 * weight + 6.25 * height - 5 * age
            bmr_raw = bmr_base + 5 if is_male else bmr_base - 161
            
            activity_multipliers = {
                "sedentary": 1.2, "light": 1.375, "moderate": 1.55,
                "active": 1.725, "very_active": 1.9, "extreme": 1.9
            }
            multiplier = activity_multipliers.get(activity, 1.55)
            tdee_raw = bmr_raw * multiplier
            
            # Round display values (BMR, TDEE) for the prompt
            bmr = round(bmr_raw)
            tdee = round(tdee_raw)
            
            # Calculate goal-specific calorie target — single round at the end
            # to match frontend calculateCalorieGoal() and avoid 1-kcal drift
            goal = user_profile.get("goal", "")
            if goal == "lose_weight":
                calorie_target = round(tdee_raw - 500)
                goal_text = f"CALORIE TARGET for WEIGHT LOSS: {calorie_target} kcal/day (500 kcal deficit from TDEE)"
            elif goal == "gain_muscle":
                calorie_target = round(tdee_raw + 300)
                goal_text = f"CALORIE TARGET for MUSCLE GAIN: {calorie_target} kcal/day (300 kcal surplus over TDEE)"
            elif goal == "maintain":
                calorie_target = round(tdee_raw)
                goal_text = f"CALORIE TARGET for MAINTENANCE: {calorie_target} kcal/day (equal to TDEE)"
            else:
                calorie_target = round(tdee_raw)
                goal_text = f"CALORIE TARGET: {calorie_target} kcal/day"
            
            pre_calc = f"\n\n**PRE-CALCULATED VALUES (use these exact numbers):** BMR={bmr} kcal/day, TDEE={tdee} kcal/day, {goal_text}"
        
        # Add special instruction for diet-aware calculations
        diet_type = (user_profile.get("diet") or "").lower()
        diet_instruction = ""
        if diet_type:
            diet_instruction = f"\n\n**IMPORTANT:** User follows a {diet_type.upper()} diet. When calculating macros, ALWAYS pass diet_type='{diet_type}' to calculate_macros() to get the correct macro distribution for their diet."
        
        if profile_data:
            # Make goal extra prominent so the LLM cannot miss it
            # But only for calorie-related queries
            goal = user_profile.get("goal", "")
            goal_instruction = ""
            if goal and is_calorie_query:
                goal_labels = {
                    "lose_weight": "LOSE WEIGHT (caloric deficit)",
                    "gain_muscle": "GAIN MUSCLE (caloric surplus)",
                    "maintain": "MAINTAIN WEIGHT"
                }
                goal_label = goal_labels.get(goal, goal)
                goal_instruction = f"\n\n⚠️ USER'S GOAL IS: {goal_label}. Tailor ALL advice to this goal ONLY. Do NOT present other scenarios."
            
            user_input = f"{user_input}\n\n[User profile: {', '.join(profile_data)}]{pre_calc}{diet_instruction}{goal_instruction}"
        
        return super().run(user_input, context)


# ============================================================
# HELPER FUNCTION FOR LANGGRAPH USE
# ============================================================

_nutrition_agent = None

def get_nutrition_agent() -> NutritionAgent:
    """Returns singleton instance of NutritionAgent."""
    global _nutrition_agent
    if _nutrition_agent is None:
        _nutrition_agent = NutritionAgent()
    return _nutrition_agent


def run_nutrition_agent(user_input: str, context: dict = None) -> AgentResponse:
    """Helper function to execute the agent."""
    agent = get_nutrition_agent()
    return agent.run(user_input, context)