"""
app/tools/nutrition_tools.py

Nutritional calculation tools for the NutritionAgent.

PHILOSOPHY:
- Deterministic calculations based on validated scientific formulas
- Real nutritional data from USDA FoodData Central (PostgreSQL)
- Zero fallbacks or invented data
- Scientific documentation with references

ARCHITECTURE:
- PostgreSQL → Foods and meals (database.py)
- Pinecone → Scientific papers (ScienceAgent)

AVAILABLE TOOLS:
1. calculate_bmr - Basal Metabolic Rate (Mifflin-St Jeor, 1990)
2. calculate_tdee - Total Daily Energy Expenditure
3. calculate_bmi - Body Mass Index (WHO)
4. calculate_macros - Macronutrient Distribution
5. get_food_nutrition - Nutritional info from USDA database
6. estimate_meal_from_description - Estimate meal calories
7. add_meal - Log meal with estimated macros

REFERENCES:
- Mifflin MD et al. (1990). Am J Clin Nutr. 51(2):241-7
- WHO (2000). Obesity: preventing and managing the global epidemic
- USDA FoodData Central (2024). fdc.nal.usda.gov
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple
from langchain_core.tools import tool

from app.runtime.request_context import get_user_id, writes_allowed, get_memory_manager


# ============================================================
# DATABASE HELPER (PostgreSQL)
# ============================================================

_db_instance = None

def _get_foods_db():
    """
    Gets the PostgreSQL database instance.
    Replaces the old FoodsDB (SQLite).
    """
    global _db_instance
    if _db_instance is None:
        try:
            from app.data.database import get_db
            _db_instance = get_db()
        except ImportError:
            try:
                from data.database import get_db
                _db_instance = get_db()
            except ImportError:
                raise ImportError("database.py not found")
    return _db_instance


class DatabaseNotFoundError(Exception):
    """Database not found."""
    pass


class DatabaseEmptyError(Exception):
    """Database is empty."""
    pass


# ============================================================
# SCIENTIFIC CONSTANTS
# ============================================================

# Physical activity factors (revised Harris-Benedict)
ACTIVITY_FACTORS = {
    "sedentary": (1.2, "Little or no exercise, desk work"),
    "sedentario": (1.2, "Little or no exercise, desk work"),
    "light": (1.375, "Light exercise 1-3 days/week"),
    "leve": (1.375, "Light exercise 1-3 days/week"),
    "moderate": (1.55, "Moderate exercise 3-5 days/week"),
    "moderado": (1.55, "Moderate exercise 3-5 days/week"),
    "active": (1.725, "Intense exercise 6-7 days/week"),
    "ativo": (1.725, "Intense exercise 6-7 days/week"),
    "very_active": (1.9, "Very intense exercise, heavy physical work"),
    "muito_ativo": (1.9, "Very intense exercise, heavy physical work"),
}

# BMI Classification (WHO, 2000)
BMI_CATEGORIES = [
    (16.0, "Severe thinness", "🔴", "Urgent medical consultation recommended"),
    (17.0, "Moderate thinness", "🟠", "Medical consultation recommended"),
    (18.5, "Mild thinness", "🟡", "Consider increasing caloric intake"),
    (25.0, "Normal weight", "🟢", "Maintain healthy habits"),
    (30.0, "Pre-obesity", "🟡", "Attention to diet and exercise"),
    (35.0, "Obesity class I", "🟠", "Professional consultation recommended"),
    (40.0, "Obesity class II", "🔴", "Medical consultation recommended"),
    (float('inf'), "Obesity class III", "🔴", "Urgent medical consultation"),
]

# Macro distribution by goal
MACRO_DISTRIBUTIONS = {
    "lose_weight": {
        "calories_adjustment": -500,
        "protein": 0.30,
        "carbs": 0.35,
        "fat": 0.35,
        "description": "High protein to preserve muscle mass in caloric deficit",
    },
    "perder_peso": {
        "calories_adjustment": -500,
        "protein": 0.30,
        "carbs": 0.35,
        "fat": 0.35,
        "description": "High protein to preserve muscle mass in caloric deficit",
    },
    "maintain": {
        "calories_adjustment": 0,
        "protein": 0.25,
        "carbs": 0.45,
        "fat": 0.30,
        "description": "Balanced distribution for maintenance",
    },
    "manter": {
        "calories_adjustment": 0,
        "protein": 0.25,
        "carbs": 0.45,
        "fat": 0.30,
        "description": "Balanced distribution for maintenance",
    },
    "gain_muscle": {
        "calories_adjustment": 300,
        "protein": 0.30,
        "carbs": 0.45,
        "fat": 0.25,
        "description": "Moderate surplus with high protein for hypertrophy",
    },
    "ganhar_massa": {
        "calories_adjustment": 300,
        "protein": 0.30,
        "carbs": 0.45,
        "fat": 0.25,
        "description": "Moderate surplus with high protein for hypertrophy",
    },
}

# Diet-specific macro distributions (override goal-based when diet is specified)
DIET_MACRO_DISTRIBUTIONS = {
    "carnivore": {
        "protein": 0.35,
        "carbs": 0.00,  # Zero carbs for carnivore
        "fat": 0.65,
        "description": "Carnivore diet: High fat, high protein, zero carbohydrates. All calories from animal sources.",
        "food_sources": {
            "protein": "Beef, pork, lamb, chicken, fish, eggs, organ meats, bacon",
            "carbs": "(Not applicable - carnivore diet excludes carbohydrates)",
            "fat": "Animal fats, butter, ghee, fatty cuts of meat, egg yolks, bone marrow"
        }
    },
    "keto": {
        "protein": 0.25,
        "carbs": 0.05,  # Very low carbs (5%)
        "fat": 0.70,
        "description": "Ketogenic diet: Very high fat, moderate protein, very low carbohydrates to maintain ketosis.",
        "food_sources": {
            "protein": "Meat, fish, eggs, cheese, nuts",
            "carbs": "Leafy greens, avocado, berries (in moderation)",
            "fat": "Olive oil, coconut oil, butter, avocado, nuts, fatty fish"
        }
    },
    "vegan": {
        "protein": 0.20,
        "carbs": 0.55,
        "fat": 0.25,
        "description": "Vegan diet: Plant-based protein sources, higher carbohydrates from whole foods.",
        "food_sources": {
            "protein": "Tofu, tempeh, legumes, lentils, seitan, edamame, quinoa",
            "carbs": "Whole grains, fruits, vegetables, legumes, potatoes",
            "fat": "Olive oil, nuts, seeds, avocado, coconut"
        }
    },
    "vegetarian": {
        "protein": 0.22,
        "carbs": 0.50,
        "fat": 0.28,
        "description": "Vegetarian diet: Plant-based with dairy and eggs for complete protein.",
        "food_sources": {
            "protein": "Eggs, dairy, legumes, tofu, tempeh, quinoa",
            "carbs": "Whole grains, fruits, vegetables, legumes",
            "fat": "Olive oil, nuts, seeds, cheese, eggs"
        }
    },
    "paleo": {
        "protein": 0.30,
        "carbs": 0.30,
        "fat": 0.40,
        "description": "Paleo diet: Focus on whole foods, moderate carbs from vegetables and fruits.",
        "food_sources": {
            "protein": "Grass-fed meat, fish, eggs, poultry",
            "carbs": "Vegetables, fruits, sweet potatoes",
            "fat": "Olive oil, coconut oil, nuts, avocado"
        }
    },
    "mediterranean": {
        "protein": 0.20,
        "carbs": 0.45,
        "fat": 0.35,
        "description": "Mediterranean diet: Balanced approach with healthy fats and whole grains.",
        "food_sources": {
            "protein": "Fish, poultry, legumes, eggs, moderate dairy",
            "carbs": "Whole grains, vegetables, fruits, legumes",
            "fat": "Olive oil, nuts, fatty fish, avocado"
        }
    },
    "animal-based": {
        "protein": 0.30,
        "carbs": 0.15,
        "fat": 0.55,
        "description": "Animal-Based diet: Prioritizes nutrient-dense animal foods with some fruit, honey, and raw dairy.",
        "food_sources": {
            "protein": "Beef, bison, lamb, organ meats, eggs, raw dairy",
            "carbs": "Fruit, honey, raw dairy, seasonal berries",
            "fat": "Tallow, butter, ghee, bone marrow, egg yolks, fatty meat cuts"
        }
    },
    "ancestral": {
        "protein": 0.25,
        "carbs": 0.35,
        "fat": 0.40,
        "description": "Ancestral diet: Traditional whole foods, organ meats, fermented foods, nose-to-tail eating.",
        "food_sources": {
            "protein": "Grass-fed meat, organ meats, wild fish, eggs, bone broth",
            "carbs": "Root vegetables, seasonal fruits, soaked grains, fermented foods",
            "fat": "Animal fats, butter, ghee, coconut oil, olive oil"
        }
    },
    "pescatarian": {
        "protein": 0.25,
        "carbs": 0.45,
        "fat": 0.30,
        "description": "Pescatarian diet: Plant-based with fish and seafood as primary animal protein.",
        "food_sources": {
            "protein": "Fish, shrimp, mussels, eggs, legumes, tofu",
            "carbs": "Whole grains, vegetables, fruits, legumes",
            "fat": "Olive oil, fatty fish (salmon, sardines), nuts, avocado"
        }
    },
    "gluten-free": {
        "protein": 0.25,
        "carbs": 0.45,
        "fat": 0.30,
        "description": "Gluten-Free diet: Balanced macros, avoids wheat, barley, and rye.",
        "food_sources": {
            "protein": "Meat, fish, eggs, legumes, dairy",
            "carbs": "Rice, potatoes, quinoa, oats (certified GF), fruits, vegetables",
            "fat": "Olive oil, butter, nuts, avocado, coconut oil"
        }
    },
    "dairy-free": {
        "protein": 0.25,
        "carbs": 0.45,
        "fat": 0.30,
        "description": "Dairy-Free diet: Balanced macros, excludes all dairy products.",
        "food_sources": {
            "protein": "Meat, fish, eggs, legumes, tofu, tempeh",
            "carbs": "Whole grains, fruits, vegetables, legumes, potatoes",
            "fat": "Olive oil, coconut oil, avocado, nuts, seeds"
        }
    },
    "low-carb": {
        "protein": 0.30,
        "carbs": 0.20,
        "fat": 0.50,
        "description": "Low-Carb diet: Reduced carbohydrates with higher fat and protein intake.",
        "food_sources": {
            "protein": "Meat, fish, eggs, cheese, Greek yogurt",
            "carbs": "Non-starchy vegetables, berries, nuts",
            "fat": "Olive oil, butter, avocado, nuts, cheese, coconut oil"
        }
    }
}

# Validation limits
VALIDATION_LIMITS = {
    "weight_kg": (20, 500),
    "height_cm": (50, 300),
    "age_years": (1, 120),
    "calories": (500, 10000),
    "grams": (1, 5000),
}


# ============================================================
# AUXILIARY FUNCTIONS
# ============================================================

def _validate_input(value: float, field: str) -> Tuple[bool, str]:
    """Validates a numeric input."""
    if field not in VALIDATION_LIMITS:
        return True, ""
    
    min_val, max_val = VALIDATION_LIMITS[field]
    
    if value < min_val or value > max_val:
        return False, f"Value of {field} must be between {min_val} and {max_val}"
    
    return True, ""


def _get_bmi_category(bmi: float) -> Tuple[str, str, str]:
    """Returns category, emoji and advice for a BMI value."""
    for threshold, category, emoji, advice in BMI_CATEGORIES:
        if bmi < threshold:
            return category, emoji, advice
    return BMI_CATEGORIES[-1][1:4]


def _format_number(value: float, decimals: int = 1) -> str:
    """Formats number removing unnecessary decimals."""
    if decimals == 0:
        return f"{value:.0f}"
    formatted = f"{value:.{decimals}f}"
    return formatted.rstrip('0').rstrip('.')


# ============================================================
# TOOL 1: CALCULATE BMR
# ============================================================

@tool
def calculate_bmr(
    weight_kg: float,
    height_cm: float,
    age_years: int,
    sex: str
) -> str:
    """
    Calculates the Basal Metabolic Rate (BMR) using the Mifflin-St Jeor formula.
    
    BMR represents the energy spent by the body at absolute rest to 
    maintain vital functions (breathing, circulation, temperature).
    
    Args:
        weight_kg: Body weight in kilograms (e.g., 70)
        height_cm: Height in centimeters (e.g., 175)
        age_years: Age in complete years (e.g., 30)
        sex: Biological sex - "M" (male) or "F" (female)
    
    Returns:
        Calculated BMR with scientific explanation
    
    Reference:
        Mifflin MD, St Jeor ST, Hill LA, Scott BJ, Daugherty SA, Koh YO.
        A new predictive equation for resting energy expenditure in healthy individuals.
        Am J Clin Nutr. 1990 Feb;51(2):241-7.
    """
    # Validations
    valid, msg = _validate_input(weight_kg, "weight_kg")
    if not valid:
        return f"❌ Error: {msg}"
    
    valid, msg = _validate_input(height_cm, "height_cm")
    if not valid:
        return f"❌ Error: {msg}"
    
    valid, msg = _validate_input(age_years, "age_years")
    if not valid:
        return f"❌ Error: {msg}"
    
    sex = sex.upper().strip()
    if sex in ("MALE", "MASCULINO", "HOMEM", "M"):
        sex = "M"
    elif sex in ("FEMALE", "FEMININO", "MULHER", "F"):
        sex = "F"
    
    if sex not in ("M", "F"):
        return """❌ Error: Sex must be "M" (male) or "F" (female).

The Mifflin-St Jeor formula uses different coefficients for each sex 
due to differences in average body composition."""
    
    # Mifflin-St Jeor Calculation (1990)
    # Men: BMR = (10 × weight) + (6.25 × height) - (5 × age) + 5
    # Women: BMR = (10 × weight) + (6.25 × height) - (5 × age) - 161
    
    if sex == "M":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age_years) + 5
        sex_label = "male"
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age_years) - 161
        sex_label = "female"
    
    # Ensure minimum safe value
    bmr = max(bmr, 800)
    
    return f"""## Basal Metabolic Rate (BMR)

### Result: {bmr:.0f} kcal/day

Your body spends approximately **{bmr:.0f} calories per day** just to 
maintain vital functions at absolute rest.

### Data used
| Parameter | Value |
|-----------|-------|
| Weight | {weight_kg} kg |
| Height | {height_cm} cm |
| Age | {age_years} years |
| Sex | {sex_label} |

### Formula
**Mifflin-St Jeor (1990)** - considered the most accurate for healthy adults.

### Limitations
- Does not consider body composition (% fat vs muscle)
- Athletes or very muscular people may have higher BMR
- People with certain medical conditions may have variations

### Next step
Use `calculate_tdee` with BMR of {bmr:.0f} to calculate total daily expenditure.

---
*Ref: Mifflin MD et al. (1990). Am J Clin Nutr. 51(2):241-7*"""


# ============================================================
# TOOL 2: CALCULATE TDEE
# ============================================================

@tool
def calculate_tdee(bmr: float, activity_level: str) -> str:
    """
    Calculates the Total Daily Energy Expenditure (TDEE).
    
    TDEE represents the total calories burned per day, including 
    physical activity and thermogenesis.
    
    Args:
        bmr: Basal Metabolic Rate in kcal (use calculate_bmr first)
        activity_level: Physical activity level:
            - "sedentary": Little/no exercise
            - "light": Exercise 1-3 days/week
            - "moderate": Exercise 3-5 days/week
            - "active": Exercise 6-7 days/week
            - "very_active": Intense daily exercise
    
    Returns:
        Calculated TDEE with caloric goals
    """
    # Validate BMR
    valid, msg = _validate_input(bmr, "calories")
    if not valid:
        return f"❌ Error: Invalid BMR. {msg}"
    
    # Normalize activity level
    activity_normalized = activity_level.lower().strip().replace(" ", "_").replace("-", "_")
    
    if activity_normalized not in ACTIVITY_FACTORS:
        levels_list = "\n".join([
            f"   • **{k}**: {v[1]}" 
            for k, v in ACTIVITY_FACTORS.items() 
            if "á" not in k  # Avoid duplicates with accent
        ])
        return f"""❌ Error: Activity level not recognized.

### Valid levels:
{levels_list}"""
    
    factor, description = ACTIVITY_FACTORS[activity_normalized]
    tdee = bmr * factor
    
    # Calculate goals
    maintain = tdee
    lose_moderate = max(tdee - 500, 1200)  # Moderate deficit, safe minimum
    lose_aggressive = max(tdee - 750, 1200)  # Aggressive deficit
    gain_lean = tdee + 250  # Conservative surplus
    gain_bulk = tdee + 500  # Moderate surplus
    
    return f"""## Total Daily Energy Expenditure (TDEE)

### Result: {tdee:.0f} kcal/day

With a **{activity_normalized}** activity level, you burn approximately 
**{tdee:.0f} calories per day**.

### Calculation
| Component | Value |
|-----------|-------|
| Base BMR | {bmr:.0f} kcal |
| Activity factor | ×{factor} |
| **TDEE** | **{tdee:.0f} kcal** |

### Caloric Goals

| Goal | Calories/day | Adjustment |
|------|-------------|------------|
| 🔴 Lose weight (aggressive) | {lose_aggressive:.0f} kcal | -750 kcal |
| 🟠 Lose weight (moderate) | {lose_moderate:.0f} kcal | -500 kcal |
| 🟢 Maintain weight | {maintain:.0f} kcal | — |
| 🔵 Gain muscle (lean) | {gain_lean:.0f} kcal | +250 kcal |
| 🟣 Gain muscle (bulk) | {gain_bulk:.0f} kcal | +500 kcal |

### Recommendations
- **Weight loss**: 500 kcal deficit ≈ 0.5 kg/week
- **Muscle gain**: 250-500 kcal surplus with strength training
- Adjust after 2-4 weeks based on actual results

### Next step
Use `calculate_macros` with TDEE of {tdee:.0f} for macronutrient distribution."""


# ============================================================
# TOOL 3: CALCULATE BMI
# ============================================================

@tool
def calculate_bmi(weight_kg: float, height_cm: float) -> str:
    """
    Calculates the Body Mass Index (BMI) with WHO classification.
    
    BMI is a measure of body composition based on the weight/height² ratio.
    
    Args:
        weight_kg: Body weight in kilograms (e.g., 70)
        height_cm: Height in centimeters (e.g., 175)
    
    Returns:
        Calculated BMI with classification and recommendations
    
    Reference:
        WHO (2000). Obesity: preventing and managing the global epidemic.
        WHO Technical Report Series 894.
    """
    # Validations
    valid, msg = _validate_input(weight_kg, "weight_kg")
    if not valid:
        return f"❌ Error: {msg}"
    
    valid, msg = _validate_input(height_cm, "height_cm")
    if not valid:
        return f"❌ Error: {msg}"
    
    # Calculation
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)
    
    # Classification
    category, emoji, advice = _get_bmi_category(bmi)
    
    # Reference weight (BMI = 22, middle of normal range)
    ideal_weight = 22 * (height_m ** 2)
    weight_diff = weight_kg - ideal_weight
    
    # Healthy weight range (BMI 18.5-25)
    weight_min = 18.5 * (height_m ** 2)
    weight_max = 25 * (height_m ** 2)
    
    return f"""## Body Mass Index (BMI)

### Result: {bmi:.1f} kg/m²

{emoji} **WHO Classification:** {category}

### Data
| Parameter | Value |
|-----------|-------|
| Current weight | {weight_kg} kg |
| Height | {height_cm} cm |
| BMI | {bmi:.1f} kg/m² |

### Reference for your height ({height_cm} cm)
| Metric | Value |
|--------|-------|
| Healthy range | {weight_min:.1f} - {weight_max:.1f} kg |
| Reference weight (BMI 22) | {ideal_weight:.1f} kg |
| Current difference | {weight_diff:+.1f} kg |

### Complete WHO Classification
| BMI | Category |
|-----|----------|
| < 18.5 | Underweight |
| 18.5 - 24.9 | **Normal weight** |
| 25.0 - 29.9 | Pre-obesity |
| ≥ 30.0 | Obesity |

### Recommendation
{advice}

### BMI Limitations
- Does not distinguish muscle mass from fat
- Athletes may have "high" BMI with low fat
- Does not consider body fat distribution
- Less accurate in elderly and children

---
*Ref: WHO Technical Report Series 894 (2000)*"""


# ============================================================
# TOOL 4: CALCULATE MACROS
# ============================================================

@tool
def calculate_macros(tdee: float, goal: str, diet_type: str = "") -> str:
    """
    Calculates the ideal macronutrient distribution based on goal AND diet type.
    
    Distributes calories between protein, carbohydrates and fat 
    according to the nutritional goal and specific diet.
    
    Args:
        tdee: Total Daily Energy Expenditure in kcal
        goal: Nutritional goal:
            - "lose_weight": Caloric deficit, high protein
            - "maintain": Balanced maintenance
            - "gain_muscle": Surplus for hypertrophy
        diet_type: Optional diet type that overrides macro distribution:
            - "carnivore": High fat, high protein, zero carbs
            - "keto": Very high fat, moderate protein, very low carbs
            - "vegan": Plant-based
            - "vegetarian": Plant-based with dairy/eggs
            - "paleo": Whole foods focused
            - "mediterranean": Balanced with healthy fats
            - "animal-based": Prioritizes animal foods, allows fruit/honey
            - "ancestral": Traditional whole foods, nose-to-tail
            - "pescatarian": Plant-based with fish/seafood
            - "gluten-free": Balanced, avoids gluten grains
            - "dairy-free": Balanced, excludes dairy
            - "low-carb": Reduced carbohydrates
    
    Returns:
        Macronutrient distribution in grams and percentages
    """
    # Validate TDEE
    valid, msg = _validate_input(tdee, "calories")
    if not valid:
        return f"❌ Error: Invalid TDEE. {msg}"
    
    # Normalize goal
    goal_normalized = goal.lower().strip().replace(" ", "_").replace("-", "_")
    
    if goal_normalized not in MACRO_DISTRIBUTIONS:
        goals_list = ", ".join(MACRO_DISTRIBUTIONS.keys())
        return f"""❌ Error: Goal not recognized.

### Valid goals:
{goals_list}

**Example:** `calculate_macros(2000, "lose_weight")`"""
    
    # Get base config from goal
    base_config = MACRO_DISTRIBUTIONS[goal_normalized]
    
    # Calculate target calories based on goal
    target_calories = tdee + base_config["calories_adjustment"]
    target_calories = max(target_calories, 1200)  # Safe minimum
    
    # Check if diet type overrides macro distribution
    diet_normalized = diet_type.lower().strip() if diet_type else ""
    
    if diet_normalized in DIET_MACRO_DISTRIBUTIONS:
        # Use diet-specific macros
        diet_config = DIET_MACRO_DISTRIBUTIONS[diet_normalized]
        protein_pct = diet_config["protein"]
        carbs_pct = diet_config["carbs"]
        fat_pct = diet_config["fat"]
        description = diet_config["description"]
        food_sources = diet_config.get("food_sources", {})
        diet_note = f"\n\n**Diet Type:** {diet_normalized.title()}"
    else:
        # Use goal-based macros
        protein_pct = base_config["protein"]
        carbs_pct = base_config["carbs"]
        fat_pct = base_config["fat"]
        description = base_config["description"]
        food_sources = {
            "protein": "Chicken, fish, eggs, dairy, beef, pork, lamb",
            "carbs": "Rice, pasta, whole grain bread, oats, potato, fruit",
            "fat": "Olive oil, avocado, nuts, fatty fish, butter"
        }
        diet_note = ""
    
    # Calculate macros in grams
    protein_kcal = target_calories * protein_pct
    carbs_kcal = target_calories * carbs_pct
    fat_kcal = target_calories * fat_pct
    
    protein_g = protein_kcal / 4  # 4 kcal/g
    carbs_g = carbs_kcal / 4      # 4 kcal/g
    fat_g = fat_kcal / 9          # 9 kcal/g
    
    # Format percentages
    prot_pct = int(protein_pct * 100)
    carb_pct = int(carbs_pct * 100)
    fat_pct_display = int(fat_pct * 100)
    
    # Build carbs row (hide if zero for carnivore)
    if carbs_pct == 0:
        carbs_row = f"| 🍚 **Carbohydrates** | 0g | 0 kcal | 0% |"
        carbs_per_meal = "0g (not applicable)"
    else:
        carbs_row = f"| 🍚 **Carbohydrates** | {carbs_g:.0f}g | {carbs_kcal:.0f} kcal | {carb_pct}% |"
        carbs_per_meal = f"~{carbs_g/4:.0f}g"
    
    return f"""## Macronutrient Distribution{diet_note}

### Goal: {goal_normalized.replace("_", " ").title()}
{description}

### Target Calories: {target_calories:.0f} kcal/day
{"(deficit of " + str(abs(base_config['calories_adjustment'])) + " kcal)" if base_config['calories_adjustment'] < 0 else "(surplus of " + str(base_config['calories_adjustment']) + " kcal)" if base_config['calories_adjustment'] > 0 else "(maintenance)"}

### Daily Distribution

| Macro | Grams | Calories | % |
|-------|-------|----------|---|
| 🥩 **Protein** | {protein_g:.0f}g | {protein_kcal:.0f} kcal | {prot_pct}% |
{carbs_row}
| 🥑 **Fat** | {fat_g:.0f}g | {fat_kcal:.0f} kcal | {fat_pct_display}% |
| **Total** | — | **{target_calories:.0f} kcal** | 100% |

### Per Meal (assuming 3-4 meals/day)

| Macro | Per meal |
|-------|----------|
| Protein | ~{protein_g/4:.0f}g |
| Carbohydrates | {carbs_per_meal} |
| Fat | ~{fat_g/4:.0f}g |

### Recommended Food Sources

**Protein ({protein_g:.0f}g):**
{food_sources.get('protein', 'Chicken, fish, eggs, dairy, beef, pork, lamb')}

**Carbohydrates ({carbs_g:.0f}g):**
{food_sources.get('carbs', 'Rice, pasta, whole grain bread, oats, potato, fruit')}

**Fat ({fat_g:.0f}g):**
{food_sources.get('fat', 'Olive oil, avocado, nuts, fatty fish, butter')}

### Note
Values calculated based on TDEE of {tdee:.0f} kcal.
Adjust according to results after 2-4 weeks."""


# ============================================================
# TOOL 5: GET FOOD NUTRITION (PostgreSQL)
# ============================================================

@tool
def get_food_nutrition(food_name: str, grams: float = 100.0) -> str:
    """
    Gets nutritional information for a food from the USDA database.
    
    Searches the PostgreSQL database with real data from USDA FoodData Central.
    Supports Portuguese names (automatic translation).
    
    Args:
        food_name: Food name (Portuguese or English)
            Examples: "banana", "chicken", "rice", "chicken breast"
        grams: Amount in grams (default: 100g)
    
    Returns:
        Complete nutritional information for the food
    
    Reference:
        U.S. Department of Agriculture, Agricultural Research Service.
        FoodData Central, 2024. fdc.nal.usda.gov
    """
    # Validate inputs
    if not food_name or not food_name.strip():
        return "❌ Error: Please provide a food name."
    
    if grams <= 0:
        grams = 100.0
    elif grams > 5000:
        return "❌ Error: Maximum allowed amount is 5000g."
    
    # Connect to PostgreSQL database
    try:
        db = _get_foods_db()
    except ImportError:
        return """❌ Error: Database module not found.

### How to fix:
1. Check that file `app/data/database.py` exists
2. Check PostgreSQL connection"""
    except Exception as e:
        return f"""❌ Error connecting to database: {e}

### How to fix:
Check that PostgreSQL is running and credentials are correct."""
    
    # Search food using PostgreSQL
    info = db.get_food_nutrition(food_name, grams)
    
    if info is None:
        # Try suggestions
        results = db.search_foods(food_name, limit=5)
        
        if results:
            suggestions = "\n".join([
                f"   • **{r.name_en}**" + (f" ({r.name_pt})" if r.name_pt else "") + f" - {r.kcal_100g:.0f} kcal/100g"
                for r in results
            ])
            return f"""❌ Could not find exactly "{food_name}".

### Did you mean:
{suggestions}

### Tip
Use English names for better results (e.g., "chicken breast", "brown rice")."""
        else:
            return f"""❌ Food "{food_name}" not found in database.

### Suggestions:
- Try English names (e.g., "chicken", "rice", "salmon")
- Use generic names (e.g., "banana" instead of "plantain")
- Check spelling"""
    
    # Extract data
    food = info["food"]
    nutrients = info["nutrients"]
    per_100g = info["per_100g"]
    
    # Formatted name
    name_display = food["name_en"]
    if food.get("name_pt"):
        name_display = f"{food['name_en']} ({food['name_pt']})"
    
    # Category
    category = food.get("category", "—")
    
    # Find similar foods
    similar_foods = db.search_foods(food_name, limit=4)
    similar_list = "\n".join([
        f"   • {r.name_en} - {r.kcal_100g:.0f} kcal"
        for r in similar_foods[1:4]  # Exclude the item itself
    ]) if len(similar_foods) > 1 else "   (none found)"
    
    return f"""## {name_display}

**Category:** {category}
**Amount:** {grams:.0f}g

### Nutritional Information

| Nutrient | Per {grams:.0f}g | Per 100g |
|----------|----------|----------|
| 🔥 **Energy** | **{nutrients['kcal']:.0f} kcal** | {per_100g['kcal']:.0f} kcal |
| 🥩 Protein | {nutrients['protein']:.1f}g | {per_100g['protein']:.1f}g |
| 🍚 Carbohydrates | {nutrients['carbs']:.1f}g | {per_100g['carbs']:.1f}g |
| 🥑 Fat | {nutrients['fat']:.1f}g | {per_100g['fat']:.1f}g |

### Related Foods
{similar_list}

---
*Source: USDA FoodData Central*"""


# ============================================================
# HELPER: ESTIMATE MEAL MACROS (internal)
# ============================================================

def _estimate_meal_macros(meal_description: str, grams_total: float = 350.0) -> Optional[Dict[str, Any]]:
    """
    Estimates macros of a meal from the description,
    using ONLY foods present in the PostgreSQL database (USDA).

    - If cannot map to foods → returns None.
    - If successful → returns dict with kcal / protein / carbs / fat.
    """
    if not meal_description or not meal_description.strip():
        return None

    if grams_total <= 0:
        grams_total = 350.0

    try:
        db = _get_foods_db()
    except (ImportError, Exception):
        return None

    # 1) Try using the entire description as a single food
    info = db.get_food_nutrition(meal_description, grams_total)
    if info is not None:
        nutrients = info["nutrients"]
        return {
            "mode": "single",
            "grams_total": grams_total,
            "total_kcal": float(nutrients["kcal"]),
            "protein": float(nutrients["protein"]),
            "carbs": float(nutrients["carbs"]),
            "fat": float(nutrients["fat"]),
            "foods_found": [info["food"]["name_en"]],
            "details": [f'{meal_description} (~{grams_total:.0f}g) mapped as single USDA food.'],
        }

    # 2) Tentar decompor em 2–3 alimentos simples
    tokens = [
        t.strip(",.()")
        for t in meal_description.lower().split()
        if len(t.strip(",.()")) > 2
    ]
    if not tokens:
        return None

    seen = set()
    foods = []
    for tok in tokens:
        results = db.search_foods(tok, limit=1)
        if not results:
            continue
        f = results[0]
        key = f.name_en.lower()
        if key in seen:
            continue
        seen.add(key)
        foods.append(f)
        if len(foods) >= 3:
            break

    if not foods:
        return None

    grams_each = grams_total / len(foods)

    total_kcal = total_p = total_c = total_f = 0.0
    details: List[str] = []
    foods_found: List[str] = []

    for f in foods:
        factor = grams_each / 100.0
        kcal = f.kcal_100g * factor
        p = f.protein_100g * factor
        c = f.carbs_100g * factor
        fat = f.fat_100g * factor

        total_kcal += kcal
        total_p += p
        total_c += c
        total_f += fat

        foods_found.append(f.name_en)
        details.append(
            f"- {f.name_en}: {grams_each:.0f}g → {kcal:.0f} kcal, {p:.1f}g P, {c:.1f}g C, {fat:.1f}g G"
        )

    return {
        "mode": "multi",
        "grams_total": grams_total,
        "total_kcal": total_kcal,
        "protein": total_p,
        "carbs": total_c,
        "fat": total_f,
        "foods_found": foods_found,
        "details": details,
    }


# ============================================================
# TOOL 6: ESTIMATE MEAL FROM DESCRIPTION
# ============================================================

@tool
def estimate_meal_from_description(meal_description: str, grams_total: float = 350.0) -> str:
    """
    Estimates calories and macros of a meal from the description,
    using ONLY the local USDA database.
    
    Does NOT invent: if cannot map, returns an error message.
    
    Args:
        meal_description: Meal description (e.g., "rice with grilled chicken")
        grams_total: Estimated total weight of the meal in grams (default: 350g)
    
    Returns:
        Nutritional estimate based on real USDA data
    """
    est = _estimate_meal_macros(meal_description, grams_total)
    
    if est is None:
        return (
            f"❌ Could not map \"{meal_description}\" to real foods in the database.\n\n"
            "Try describing the meal with simple foods, for example:\n"
            "- \"grilled chicken breast with rice and salad\"\n"
            "- \"yogurt with banana and oats\""
        )

    total_kcal = est["total_kcal"]
    total_p = est["protein"]
    total_c = est["carbs"]
    total_f = est["fat"]
    grams_total = est["grams_total"]
    foods_found = est["foods_found"]
    details = "\n".join(est["details"])

    return f"""## Meal Estimate

**Description:** {meal_description}
**Estimated weight:** ~{grams_total:.0f}g

### Estimated Nutritional Information

| Nutrient | Amount |
|----------|--------|
| 🔥 **Calories** | **{total_kcal:.0f} kcal** |
| 🥩 Protein | {total_p:.1f}g |
| 🍚 Carbohydrates | {total_c:.1f}g |
| 🥑 Fat | {total_f:.1f}g |

### Foods identified
{", ".join(foods_found)}

### Details
{details}

⚠️ *These values are an estimate based on USDA foods. 
Adjust according to actual portions consumed.*"""


# ============================================================
# TOOL 7: ADD MEAL (log meal with estimated macros)
# ============================================================

@tool
def add_meal(description: str, grams_total: float = 350.0) -> dict:
    """
    Logs a meal in the PostgreSQL database with estimated calories and macros
    from the description, using ONLY foods from the database.

    - If cannot estimate → returns {"error": "..."} and does NOT save anything.
    - If successful → calls db.log_meal(...) with calories/protein/carbs/fat filled.
    
    Args:
        description: Meal description (e.g., "rice with chicken")
        grams_total: Estimated total weight in grams (default: 350g)
    
    Returns:
        Dictionary with logged meal data or error
    """
    # Estimate macros
    est = _estimate_meal_macros(description, grams_total)
    
    if est is None:
        return {
            "error": (
                "Could not estimate calories/macros for this meal "
                "based on the food database. "
                "Please describe the meal with simpler foods "
                "or log manually."
            )
        }

    total_kcal = int(round(est["total_kcal"]))
    total_p = round(est["protein"], 1)
    total_c = round(est["carbs"], 1)
    total_f = round(est["fat"], 1)

    # Import database
    try:
        from app.data.database import get_db
    except ImportError as e:
        return {"error": f"Error importing database module: {e}"}

    try:
        db = get_db()
    except Exception as e:
        return {"error": f"Error getting PostgreSQL database connection: {e}"}

    payload = {
        "description": description,
        "calories": total_kcal,
        "protein": total_p,
        "carbs": total_c,
        "fat": total_f,
        "fiber": None,
        "notes": f"Automatic estimate: {', '.join(est['foods_found'])}",
    }

    if not writes_allowed():
        mm = get_memory_manager()
        if mm:
            mm.set_pending_meal(payload)
        return {
            "pending_confirmation": True,
            "action": "log_meal",
            "proposed": payload,
            "message": "Meal is ready to be logged. Reply CONFIRM to save or CANCEL to discard.",
        }

    # Log meal (allowed)
    try:
        meal = db.log_meal(user_id=get_user_id(), **payload)

        data = meal.to_dict()
        data["estimation_grams"] = grams_total
        data["estimation_details"] = est["details"]
        data["foods_found"] = est["foods_found"]
        return data
        
    except Exception as e:
        return {"error": f"Error logging meal: {e}"}


# ============================================================
# TOOLS LIST FOR EXPORT
# ============================================================

NUTRITION_TOOLS = [
    calculate_bmr,
    calculate_tdee,
    calculate_bmi,
    calculate_macros,
    get_food_nutrition,
    estimate_meal_from_description,
    add_meal,
]


# ============================================================
# INFO AND DIAGNOSTICS
# ============================================================

def get_nutrition_tools_info() -> Dict[str, Any]:
    """
    Returns information about tools and database status.
    
    Useful for diagnostics and documentation.
    """
    info = {
        "tools": [t.name for t in NUTRITION_TOOLS],
        "tools_count": len(NUTRITION_TOOLS),
        "database": None,
    }
    
    try:
        db = _get_foods_db()
        stats = db.get_stats()
        info["database"] = {
            "status": "ok",
            "type": "PostgreSQL",
            "total_foods": stats.get("total_foods", 0),
            "total_meals": stats.get("total_meals", 0),
            "source": "USDA FoodData Central",
        }
    except Exception as e:
        info["database"] = {
            "status": "error",
            "error": str(e),
        }
    
    return info
    print("\n" + "="*60)