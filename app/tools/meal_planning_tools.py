"""
app/tools/meal_planning_tools.py

Meal Planning and Nutrition Analysis Tools.

AVAILABLE TOOLS:
1. generate_meal_plan - Creates a personalized meal plan
2. get_nutrition_summary - Analyzes user's nutrition history
3. identify_deficiencies - Identifies nutritional gaps
4. suggest_foods_for_goal - Suggests foods based on goal
5. calculate_weekly_average - Calculates weekly nutrition averages

REFERENCES:
- Dietary Guidelines for Americans 2020-2025
- WHO Healthy Diet Guidelines
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from datetime import datetime, timedelta
import random


# ============================================================
# DATABASE HELPER
# ============================================================

_db_instance = None

def _get_db():
    """Gets the PostgreSQL database instance."""
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


# ============================================================
# NUTRITIONAL CONSTANTS
# ============================================================

# Daily recommended intake (general adults)
DAILY_RECOMMENDED = {
    "protein_g": 50,  # 0.8g/kg for 62.5kg average
    "carbs_g": 275,
    "fat_g": 65,
    "fiber_g": 28,
    "sodium_mg": 2300,
    "sugar_g": 50,  # max
}

# Food categories with examples
FOOD_CATEGORIES = {
    "proteins": {
        "foods": ["chicken breast", "salmon", "eggs", "greek yogurt", "tofu", "lean beef", "turkey", "tuna", "cottage cheese", "lentils"],
        "importance": "Muscle maintenance, satiety, metabolism"
    },
    "vegetables": {
        "foods": ["broccoli", "spinach", "carrots", "bell peppers", "tomatoes", "zucchini", "asparagus", "kale", "cauliflower", "green beans"],
        "importance": "Vitamins, minerals, fiber, antioxidants"
    },
    "fruits": {
        "foods": ["apple", "banana", "berries", "orange", "grapes", "kiwi", "mango", "pear", "peach", "watermelon"],
        "importance": "Natural sugars, vitamins, hydration"
    },
    "grains": {
        "foods": ["brown rice", "quinoa", "oats", "whole wheat bread", "pasta", "barley", "bulgur", "couscous", "buckwheat", "millet"],
        "importance": "Complex carbs, sustained energy, fiber"
    },
    "dairy": {
        "foods": ["milk", "cheese", "yogurt", "cottage cheese", "kefir"],
        "importance": "Calcium, protein, probiotics"
    },
    "healthy_fats": {
        "foods": ["avocado", "olive oil", "nuts", "seeds", "fatty fish"],
        "importance": "Brain health, hormone production, satiety"
    }
}

# Meal templates by goal
MEAL_TEMPLATES = {
    "lose_weight": {
        "breakfast": {"calories": 300, "protein_ratio": 0.30},
        "lunch": {"calories": 400, "protein_ratio": 0.30},
        "dinner": {"calories": 350, "protein_ratio": 0.35},
        "snack 1": {"calories": 75, "protein_ratio": 0.25},
        "snack 2": {"calories": 75, "protein_ratio": 0.25},
    },
    "maintain": {
        "breakfast": {"calories": 400, "protein_ratio": 0.25},
        "lunch": {"calories": 500, "protein_ratio": 0.25},
        "dinner": {"calories": 500, "protein_ratio": 0.25},
        "snack 1": {"calories": 100, "protein_ratio": 0.20},
        "snack 2": {"calories": 100, "protein_ratio": 0.20},
    },
    "gain_muscle": {
        "breakfast": {"calories": 500, "protein_ratio": 0.30},
        "lunch": {"calories": 600, "protein_ratio": 0.30},
        "dinner": {"calories": 600, "protein_ratio": 0.30},
        "snack 1": {"calories": 150, "protein_ratio": 0.35},
        "snack 2": {"calories": 150, "protein_ratio": 0.35},
    },
}


# ============================================================
# TOOL 1: GENERATE MEAL PLAN
# ============================================================

@tool
def generate_meal_plan(
    target_calories: int,
    goal: str = "maintain",
    days: int = 1,
    dietary_restrictions: str = "",
    diet_type: str = ""
) -> str:
    """
    Generates a personalized meal plan based on caloric target and goal.
    
    Args:
        target_calories: Daily caloric target (e.g., 2000)
        goal: One of 'lose_weight', 'maintain', 'gain_muscle'
        days: Number of days to plan (1-7)
        dietary_restrictions: Any dietary restrictions (e.g., "vegetarian", "gluten-free")
        diet_type: Specific diet type (e.g., "carnivore", "keto", "vegan")
    
    Returns:
        Structured meal plan with foods, portions, and macros
    """
    days = min(max(1, days), 7)
    goal = goal.lower().replace(" ", "_")
    
    if goal not in MEAL_TEMPLATES:
        goal = "maintain"
    
    template = MEAL_TEMPLATES[goal]
    
    # Combine diet_type and dietary_restrictions for food selection
    restrictions = dietary_restrictions.lower() if dietary_restrictions else ""
    if diet_type:
        restrictions = f"{diet_type.lower()} {restrictions}".strip()
    
    # Adjust template to match target calories
    template_total = sum(m["calories"] for m in template.values())
    scale = target_calories / template_total
    
    result = []
    result.append(f"## {days}-Day Meal Plan")
    result.append("")
    
    # Header info in a cleaner format
    header_parts = [f"**Goal:** {goal.replace('_', ' ').title()}", f"**Daily Target:** {target_calories} kcal"]
    if diet_type:
        header_parts.append(f"**Diet:** {diet_type.title()}")
    result.append(" | ".join(header_parts))
    
    if dietary_restrictions and dietary_restrictions.lower() != (diet_type.lower() if diet_type else ""):
        result.append(f"**Restrictions:** {dietary_restrictions}")
    result.append("")
    result.append("---")
    result.append("")
    
    for day in range(1, days + 1):
        if days > 1:
            result.append(f"### Day {day}")
            result.append("")
        daily_total = 0
        daily_protein = 0
        daily_fat = 0
        daily_carbs = 0
        
        for meal_name, meal_info in template.items():
            meal_cals = int(meal_info["calories"] * scale)
            protein_ratio = meal_info.get("protein_ratio", 0.25)
            daily_total += meal_cals
            
            # Calculate approximate macros for this meal
            meal_protein = int((meal_cals * protein_ratio) / 4)  # 4 cal/g protein
            
            # Adjust macros based on diet type
            if "carnivore" in restrictions:
                # Carnivore: 35% protein, 65% fat, 0% carbs
                meal_protein = int((meal_cals * 0.35) / 4)
                meal_fat = int((meal_cals * 0.65) / 9)
                meal_carbs = 0
            elif "keto" in restrictions:
                # Keto: 25% protein, 70% fat, 5% carbs
                meal_protein = int((meal_cals * 0.25) / 4)
                meal_fat = int((meal_cals * 0.70) / 9)
                meal_carbs = int((meal_cals * 0.05) / 4)
            else:
                # Standard: calculated protein, 30% fat, rest carbs
                meal_fat = int((meal_cals * 0.30) / 9)
                meal_carbs = int((meal_cals - meal_protein * 4 - meal_fat * 9) / 4)
            
            daily_protein += meal_protein
            daily_fat += meal_fat
            daily_carbs += meal_carbs
            
            # Select appropriate foods
            if meal_name == "breakfast":
                foods = _get_breakfast_foods(restrictions)
            elif meal_name == "lunch":
                foods = _get_lunch_foods(restrictions)
            elif meal_name == "dinner":
                foods = _get_dinner_foods(restrictions)
            else:
                foods = _get_snack_foods(restrictions)
            
            # Format with macros - cleaner layout
            display_name = meal_name.replace("_", " ").title() if "snack" not in meal_name else meal_name.title()
            result.append(f"### {display_name}")
            result.append(f"*{meal_cals} kcal | Protein: {meal_protein}g | Fat: {meal_fat}g | Carbs: {meal_carbs}g*")
            result.append("")
            for food in foods:
                result.append(f"- {food}")
            result.append("")
        
        result.append("---")
        result.append("")
        result.append(f"**Daily Total:** {daily_total} kcal")
        result.append(f"- Protein: {daily_protein}g")
        result.append(f"- Fat: {daily_fat}g")
        result.append(f"- Carbs: {daily_carbs}g")
        
        if day < days:
            result.append("")
            result.append("---")
            result.append("")
    
    # Add diet-specific tips
    result.append("")
    result.append("---")
    result.append("")
    result.append("### Tips")
    result.append("")
    
    # Tips based on diet type first, then goal
    diet_lower = (diet_type or "").lower()
    if diet_lower in ("carnivore", "animal-based"):
        tips = ["Focus on fatty cuts of meat", "Include organ meats weekly", "Use animal fats for cooking", "Stay hydrated with electrolytes"]
    elif diet_lower == "keto":
        tips = ["Keep carbs under 20g/day", "Prioritize healthy fats", "Moderate protein intake", "Watch for hidden carbs"]
    elif diet_lower == "vegan":
        tips = ["Combine proteins (legumes + grains)", "Supplement B12 and omega-3", "Include iron-rich foods daily", "Eat varied colors"]
    elif goal == "lose_weight":
        tips = ["Drink water before meals", "Eat slowly and mindfully", "Prioritize protein for satiety", "Avoid liquid calories"]
    elif goal == "gain_muscle":
        tips = ["Eat protein every meal (2g/kg)", "Don't skip breakfast", "Post-workout protein within 2h", "Include complex carbs"]
    else:
        tips = ["Maintain regular meal times", "Listen to hunger cues", "Balance all macronutrients", "Eat whole unprocessed foods"]
    
    for tip in tips:
        result.append(f"- {tip}")
    
    return "\n".join(result)


# ============================================================
# DIET-SPECIFIC FOOD OPTIONS
# ============================================================

# Carnivore diet - ONLY animal products (meat, fish, eggs, dairy)
CARNIVORE_MEALS = {
    "breakfast": [
        ["Scrambled eggs (3)", "Bacon (4 strips)", "Butter"],
        ["Beef patties (2)", "Fried eggs (2)", "Bone broth"],
        ["Steak and eggs", "Heavy cream coffee"],
        ["Pork sausages (3)", "Cheese omelette", "Beef tallow"],
    ],
    "lunch": [
        ["Ribeye steak (200g)", "Butter", "Bone broth"],
        ["Ground beef patties (250g)", "Cheddar cheese", "Egg"],
        ["Lamb chops (3)", "Beef liver pâté", "Cream"],
        ["Roasted chicken thighs (3)", "Pork rinds", "Butter"],
    ],
    "dinner": [
        ["Beef ribeye (300g)", "Butter", "Egg yolks (2)"],
        ["Grilled salmon (250g)", "Cream cheese", "Bacon"],
        ["Pork belly (200g)", "Beef bone marrow", "Eggs"],
        ["Lamb leg (250g)", "Beef tallow", "Hard cheese"],
    ],
    "snacks": [
        ["Beef jerky", "Hard boiled eggs (2)"],
        ["Pork rinds", "Cheese slices"],
        ["Bone broth cup", "Butter coffee"],
        ["Beef liver bites", "Cream cheese"],
    ],
}

# Ketogenic diet - High fat, very low carb, moderate protein
KETO_MEALS = {
    "breakfast": [
        ["Bacon and eggs (3)", "Avocado", "Butter coffee"],
        ["Cheese omelette", "Sausages", "MCT oil coffee"],
        ["Keto pancakes (almond flour)", "Cream cheese", "Berries (small)"],
        ["Smoked salmon", "Cream cheese", "Cucumber"],
    ],
    "lunch": [
        ["Caesar salad (no croutons)", "Grilled chicken", "Parmesan"],
        ["Bunless burger", "Cheese", "Avocado", "Side salad"],
        ["Tuna salad with mayo", "Lettuce wraps", "Olive oil"],
        ["Zucchini noodles", "Pesto", "Grilled shrimp"],
    ],
    "dinner": [
        ["Salmon with butter sauce", "Asparagus", "Cauliflower mash"],
        ["Ribeye steak", "Garlic butter", "Sautéed mushrooms"],
        ["Chicken thighs", "Broccoli with cheese sauce", "Bacon"],
        ["Pork chops", "Creamed spinach", "Roasted Brussels sprouts"],
    ],
    "snacks": [
        ["Macadamia nuts", "Cheese cubes"],
        ["Celery with almond butter"],
        ["Pork rinds", "Guacamole"],
        ["Fat bombs (chocolate)"],
    ],
}

# Paleo diet - Whole foods, no grains, dairy, legumes, processed foods
PALEO_MEALS = {
    "breakfast": [
        ["Scrambled eggs (3)", "Avocado", "Sweet potato hash"],
        ["Banana pancakes (egg-based)", "Berries", "Almond butter"],
        ["Smoked salmon", "Poached eggs", "Spinach"],
        ["Breakfast bowl with ground turkey", "Sweet potato", "Kale"],
    ],
    "lunch": [
        ["Grilled chicken breast", "Mixed salad", "Olive oil dressing"],
        ["Tuna with avocado", "Vegetable sticks", "Almonds"],
        ["Beef stir-fry", "Zucchini noodles", "Coconut aminos"],
        ["Shrimp salad", "Mango", "Macadamia nuts"],
    ],
    "dinner": [
        ["Grilled salmon", "Roasted sweet potato", "Asparagus"],
        ["Grass-fed steak", "Roasted vegetables", "Ghee"],
        ["Roasted chicken", "Butternut squash", "Green beans"],
        ["Pork tenderloin", "Cauliflower rice", "Sautéed spinach"],
    ],
    "snacks": [
        ["Apple slices with almond butter"],
        ["Mixed nuts and dried fruit"],
        ["Beef jerky (no sugar)"],
        ["Vegetable sticks with guacamole"],
    ],
}

# Ancestral diet - Traditional whole foods, organ meats, fermented foods
ANCESTRAL_MEALS = {
    "breakfast": [
        ["Liver and eggs", "Sauerkraut", "Bone broth"],
        ["Beef heart hash", "Fermented vegetables", "Raw milk"],
        ["Sardines", "Eggs", "Sourdough (fermented)"],
        ["Organ meat pâté", "Raw cheese", "Kefir"],
    ],
    "lunch": [
        ["Bone broth soup", "Grass-fed beef", "Fermented pickles"],
        ["Wild-caught fish", "Organ meat blend", "Kimchi"],
        ["Lamb with tallow", "Root vegetables", "Raw sauerkraut"],
        ["Beef tongue", "Bone marrow", "Fermented beets"],
    ],
    "dinner": [
        ["Slow-cooked beef roast", "Bone broth gravy", "Fermented vegetables"],
        ["Wild salmon", "Liver pâté", "Cultured butter vegetables"],
        ["Grass-fed ribeye", "Beef kidney", "Raw cheese"],
        ["Lamb shanks", "Bone marrow", "Lacto-fermented carrots"],
    ],
    "snacks": [
        ["Bone broth cup"],
        ["Liver crisps", "Raw cheese"],
        ["Kefir", "Fermented cod liver oil"],
        ["Beef heart jerky"],
    ],
}

# Mediterranean diet - Olive oil, fish, whole grains, vegetables
MEDITERRANEAN_MEALS = {
    "breakfast": [
        ["Greek yogurt", "Honey", "Walnuts", "Fresh figs"],
        ["Whole grain toast", "Olive oil", "Tomatoes", "Feta"],
        ["Omelette with vegetables", "Olives", "Whole wheat bread"],
        ["Shakshuka (eggs in tomato)", "Pita bread", "Hummus"],
    ],
    "lunch": [
        ["Grilled fish", "Greek salad", "Olive oil", "Pita"],
        ["Lentil soup", "Whole grain bread", "Feta cheese"],
        ["Chicken souvlaki", "Tzatziki", "Mixed salad"],
        ["Falafel bowl", "Hummus", "Tabbouleh", "Olive oil"],
    ],
    "dinner": [
        ["Baked salmon", "Roasted vegetables", "Olive oil", "Couscous"],
        ["Grilled lamb", "Greek salad", "Bulgur wheat"],
        ["Seafood pasta", "Olive oil", "Fresh tomatoes", "Basil"],
        ["Stuffed peppers", "Rice", "Pine nuts", "Yogurt sauce"],
    ],
    "snacks": [
        ["Olives and feta"],
        ["Hummus with vegetables"],
        ["Mixed nuts"],
        ["Fresh fruit with honey"],
    ],
}

# Low-carb diet
LOW_CARB_MEALS = {
    "breakfast": [
        ["Eggs (3)", "Bacon", "Avocado"],
        ["Greek yogurt (full-fat)", "Berries (small portion)", "Nuts"],
        ["Cheese omelette", "Sausages", "Spinach"],
        ["Smoked salmon", "Cream cheese", "Cucumber"],
    ],
    "lunch": [
        ["Grilled chicken salad", "Olive oil", "Feta cheese"],
        ["Tuna lettuce wraps", "Avocado", "Mayo"],
        ["Bunless burger", "Cheese", "Pickles", "Side salad"],
        ["Shrimp and avocado bowl", "Lime dressing"],
    ],
    "dinner": [
        ["Steak", "Butter", "Steamed broccoli", "Mushrooms"],
        ["Baked salmon", "Asparagus", "Lemon butter"],
        ["Chicken thighs", "Cauliflower mash", "Green beans"],
        ["Pork chops", "Roasted Brussels sprouts", "Bacon"],
    ],
    "snacks": [
        ["Cheese cubes", "Almonds"],
        ["Celery with cream cheese"],
        ["Beef jerky"],
        ["Boiled eggs"],
    ],
}


def _get_breakfast_foods(restrictions: str) -> List[str]:
    """Returns breakfast food suggestions based on dietary restrictions."""
    restrictions = restrictions.lower() if restrictions else ""
    
    # Check for specific diets first
    if "carnivore" in restrictions:
        return random.choice(CARNIVORE_MEALS["breakfast"])
    elif "keto" in restrictions or "ketogenic" in restrictions:
        return random.choice(KETO_MEALS["breakfast"])
    elif "paleo" in restrictions:
        return random.choice(PALEO_MEALS["breakfast"])
    elif "ancestral" in restrictions:
        return random.choice(ANCESTRAL_MEALS["breakfast"])
    elif "mediterranean" in restrictions:
        return random.choice(MEDITERRANEAN_MEALS["breakfast"])
    elif "low-carb" in restrictions or "low carb" in restrictions:
        return random.choice(LOW_CARB_MEALS["breakfast"])
    
    # Default options
    options = [
        ["Oatmeal with berries and honey", "Greek yogurt", "Green tea"],
        ["Scrambled eggs (2)", "Whole wheat toast", "Orange juice"],
        ["Banana smoothie with protein", "Almonds (handful)", "Coffee"],
        ["Avocado toast", "Boiled eggs (2)", "Fresh fruit"],
    ]
    
    if "vegan" in restrictions:
        options = [
            ["Oatmeal with berries", "Almond milk", "Chia seeds"],
            ["Tofu scramble", "Whole wheat toast", "Fruit"],
            ["Smoothie bowl with plant protein", "Nuts", "Seeds"],
            ["Avocado toast", "Hummus", "Fresh vegetables"],
        ]
    elif "vegetarian" in restrictions:
        options = [
            ["Greek yogurt with granola", "Fresh berries", "Honey"],
            ["Vegetable omelette", "Whole wheat toast", "Fruit"],
            ["Overnight oats", "Nuts", "Banana"],
            ["Avocado toast", "Poached eggs", "Tomatoes"],
        ]
    elif "gluten-free" in restrictions or "gluten free" in restrictions:
        options = [
            ["Scrambled eggs (3)", "Avocado", "Fresh fruit"],
            ["Greek yogurt", "Berries", "Gluten-free granola"],
            ["Omelette with vegetables", "Hash browns", "Orange juice"],
            ["Smoothie bowl", "Nuts", "Seeds"],
        ]
    
    return random.choice(options) if options else options[0]


def _get_lunch_foods(restrictions: str) -> List[str]:
    """Returns lunch food suggestions based on dietary restrictions."""
    restrictions = restrictions.lower() if restrictions else ""
    
    # Check for specific diets first
    if "carnivore" in restrictions:
        return random.choice(CARNIVORE_MEALS["lunch"])
    elif "keto" in restrictions or "ketogenic" in restrictions:
        return random.choice(KETO_MEALS["lunch"])
    elif "paleo" in restrictions:
        return random.choice(PALEO_MEALS["lunch"])
    elif "ancestral" in restrictions:
        return random.choice(ANCESTRAL_MEALS["lunch"])
    elif "mediterranean" in restrictions:
        return random.choice(MEDITERRANEAN_MEALS["lunch"])
    elif "low-carb" in restrictions or "low carb" in restrictions:
        return random.choice(LOW_CARB_MEALS["lunch"])
    
    # Default options
    options = [
        ["Grilled chicken salad", "Quinoa (1 cup)", "Olive oil dressing"],
        ["Turkey sandwich on whole grain", "Mixed vegetables", "Apple"],
        ["Salmon fillet", "Brown rice", "Steamed broccoli"],
        ["Lentil soup", "Whole grain bread", "Side salad"],
    ]
    
    if "vegan" in restrictions:
        options = [
            ["Buddha bowl with chickpeas", "Quinoa", "Tahini dressing"],
            ["Lentil soup", "Whole grain bread", "Hummus"],
            ["Vegetable stir-fry", "Tofu", "Brown rice"],
            ["Black bean tacos", "Guacamole", "Salsa"],
        ]
    elif "vegetarian" in restrictions:
        options = [
            ["Lentil soup", "Whole grain bread", "Side salad"],
            ["Buddha bowl with chickpeas", "Avocado", "Tahini dressing"],
            ["Vegetable stir-fry", "Tofu", "Brown rice"],
            ["Caprese salad", "Quinoa", "Olive oil"],
        ]
    elif "gluten-free" in restrictions or "gluten free" in restrictions:
        options = [
            ["Grilled chicken salad", "Rice", "Olive oil dressing"],
            ["Salmon fillet", "Sweet potato", "Steamed vegetables"],
            ["Tuna salad", "Avocado", "Mixed greens"],
            ["Shrimp stir-fry", "Rice noodles", "Vegetables"],
        ]
    
    return random.choice(options)


def _get_dinner_foods(restrictions: str) -> List[str]:
    """Returns dinner food suggestions based on dietary restrictions."""
    restrictions = restrictions.lower() if restrictions else ""
    
    # Check for specific diets first
    if "carnivore" in restrictions:
        return random.choice(CARNIVORE_MEALS["dinner"])
    elif "keto" in restrictions or "ketogenic" in restrictions:
        return random.choice(KETO_MEALS["dinner"])
    elif "paleo" in restrictions:
        return random.choice(PALEO_MEALS["dinner"])
    elif "ancestral" in restrictions:
        return random.choice(ANCESTRAL_MEALS["dinner"])
    elif "mediterranean" in restrictions:
        return random.choice(MEDITERRANEAN_MEALS["dinner"])
    elif "low-carb" in restrictions or "low carb" in restrictions:
        return random.choice(LOW_CARB_MEALS["dinner"])
    
    # Default options
    options = [
        ["Baked salmon", "Sweet potato", "Asparagus"],
        ["Lean beef stir-fry", "Mixed vegetables", "Jasmine rice"],
        ["Grilled chicken breast", "Roasted vegetables", "Quinoa"],
        ["Turkey meatballs", "Whole wheat pasta", "Marinara sauce"],
    ]
    
    if "vegan" in restrictions:
        options = [
            ["Vegetable curry", "Basmati rice", "Tofu"],
            ["Stuffed bell peppers", "Black beans", "Quinoa"],
            ["Pasta with marinara", "Nutritional yeast", "Side salad"],
            ["Lentil bolognese", "Zucchini noodles", "Garlic bread"],
        ]
    elif "vegetarian" in restrictions:
        options = [
            ["Vegetable curry", "Basmati rice", "Naan bread"],
            ["Stuffed bell peppers", "Black beans", "Cheese"],
            ["Pasta primavera", "Parmesan cheese", "Side salad"],
            ["Eggplant parmesan", "Spaghetti", "Marinara sauce"],
        ]
    elif "gluten-free" in restrictions or "gluten free" in restrictions:
        options = [
            ["Baked salmon", "Roasted potatoes", "Asparagus"],
            ["Grilled steak", "Sweet potato", "Green beans"],
            ["Chicken stir-fry", "Rice", "Mixed vegetables"],
            ["Shrimp scampi", "Rice noodles", "Garlic butter"],
        ]
    
    return random.choice(options)


def _get_snack_foods(restrictions: str) -> List[str]:
    """Returns snack suggestions based on dietary restrictions."""
    restrictions = restrictions.lower() if restrictions else ""
    
    # Check for specific diets first
    if "carnivore" in restrictions:
        return random.choice(CARNIVORE_MEALS["snacks"])
    elif "keto" in restrictions or "ketogenic" in restrictions:
        return random.choice(KETO_MEALS["snacks"])
    elif "paleo" in restrictions:
        return random.choice(PALEO_MEALS["snacks"])
    elif "ancestral" in restrictions:
        return random.choice(ANCESTRAL_MEALS["snacks"])
    elif "mediterranean" in restrictions:
        return random.choice(MEDITERRANEAN_MEALS["snacks"])
    elif "low-carb" in restrictions or "low carb" in restrictions:
        return random.choice(LOW_CARB_MEALS["snacks"])
    
    # Default options
    options = [
        ["Greek yogurt with honey"],
        ["Apple with almond butter"],
        ["Handful of mixed nuts"],
        ["Protein bar"],
        ["Cottage cheese with fruit"],
        ["Hummus with carrots"],
    ]
    
    if "vegan" in restrictions:
        options = [
            ["Hummus with vegetable sticks"],
            ["Mixed nuts and dried fruit"],
            ["Apple with almond butter"],
            ["Energy balls (dates, nuts)"],
        ]
    elif "vegetarian" in restrictions:
        options = [
            ["Greek yogurt with honey"],
            ["Cheese and crackers"],
            ["Apple with peanut butter"],
            ["Trail mix"],
        ]
    elif "gluten-free" in restrictions or "gluten free" in restrictions:
        options = [
            ["Greek yogurt with berries"],
            ["Rice cakes with almond butter"],
            ["Mixed nuts"],
            ["Cheese and fruit"],
        ]
    
    return random.choice(options)


# ============================================================
# TOOL 2: GET NUTRITION SUMMARY
# ============================================================

@tool
def get_nutrition_summary(days: int = 7) -> str:
    """
    Analyzes the user's nutrition history and provides a summary.
    
    Args:
        days: Number of days to analyze (default: 7)
    
    Returns:
        Summary of nutritional intake with insights
    """
    try:
        db = _get_db()
        meals = db.get_all_meals()
        
        if not meals:
            return "**No meals logged yet.**\n\nStart logging your meals to see nutritional insights!"
        
        # Filter by date range
        cutoff = datetime.now() - timedelta(days=days)
        recent_meals = []
        
        for meal in meals:
            # Handle different date formats
            meal_date = meal.get("data") or meal.get("date")
            if meal_date:
                if isinstance(meal_date, str):
                    try:
                        meal_dt = datetime.fromisoformat(meal_date.replace("Z", ""))
                    except:
                        meal_dt = datetime.now()
                else:
                    meal_dt = meal_date
                
                if meal_dt >= cutoff:
                    recent_meals.append(meal)
            else:
                recent_meals.append(meal)  # Include if no date
        
        if not recent_meals:
            return f"**No meals logged in the last {days} days.**"
        
        # Calculate totals
        total_calories = sum(m.get("calorias", 0) or 0 for m in recent_meals)
        total_protein = sum(m.get("proteina", 0) or 0 for m in recent_meals)
        total_carbs = sum(m.get("hidratos", 0) or 0 for m in recent_meals)
        total_fat = sum(m.get("gordura", 0) or 0 for m in recent_meals)
        
        # Calculate averages
        num_days = min(days, len(set(str(m.get("data", ""))[:10] for m in recent_meals if m.get("data"))) or 1)
        avg_calories = total_calories / num_days
        avg_protein = total_protein / num_days
        avg_carbs = total_carbs / num_days
        avg_fat = total_fat / num_days
        
        result = []
        result.append(f"**Nutrition Summary ({days} days)**")
        result.append("")
        result.append(f"**Meals logged:** {len(recent_meals)}")
        result.append("")
        result.append("### Daily Averages")
        result.append(f"Calories: **{avg_calories:.0f}** kcal/day")
        result.append(f"Protein: **{avg_protein:.0f}g**/day")
        result.append(f"Carbs: **{avg_carbs:.0f}g**/day")
        result.append(f"Fat: **{avg_fat:.0f}g**/day")
        result.append("")
        result.append("### Totals")
        result.append(f"Total Calories: {total_calories:.0f} kcal")
        result.append(f"Total Protein: {total_protein:.0f}g")
        result.append(f"Total Carbs: {total_carbs:.0f}g")
        result.append(f"Total Fat: {total_fat:.0f}g")
        
        # Insights
        result.append("")
        result.append("### Insights")
        
        # Protein check
        if avg_protein < DAILY_RECOMMENDED["protein_g"]:
            result.append(f"**Protein is low** ({avg_protein:.0f}g vs {DAILY_RECOMMENDED['protein_g']}g recommended)")
        else:
            result.append(f"Protein intake is adequate")
        
        # Calorie estimate
        if avg_calories < 1200:
            result.append(f"**Very low calorie intake** - may be unsustainable")
        elif avg_calories > 3000:
            result.append(f"High calorie intake - ensure this matches your activity level")
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Error analyzing nutrition: {str(e)}"


# ============================================================
# TOOL 3: IDENTIFY DEFICIENCIES
# ============================================================

@tool
def identify_deficiencies(target_calories: int = 2000) -> str:
    """
    Identifies potential nutritional deficiencies based on meal history.
    
    Args:
        target_calories: User's daily caloric target
    
    Returns:
        List of potential deficiencies and recommendations
    """
    try:
        db = _get_db()
        meals = db.get_all_meals()
        
        if not meals or len(meals) < 3:
            return "**Need more data**\n\nLog at least 3 meals to identify patterns and potential deficiencies."
        
        # Calculate 7-day averages
        cutoff = datetime.now() - timedelta(days=7)
        recent_meals = meals[-21:]  # Last ~3 weeks max
        
        if not recent_meals:
            recent_meals = meals
        
        avg_calories = sum(m.get("calorias", 0) or 0 for m in recent_meals) / max(1, len(recent_meals) / 3)
        avg_protein = sum(m.get("proteina", 0) or 0 for m in recent_meals) / max(1, len(recent_meals) / 3)
        avg_carbs = sum(m.get("hidratos", 0) or 0 for m in recent_meals) / max(1, len(recent_meals) / 3)
        avg_fat = sum(m.get("gordura", 0) or 0 for m in recent_meals) / max(1, len(recent_meals) / 3)
        
        deficiencies = []
        recommendations = []
        
        # Check calories
        if avg_calories < target_calories * 0.7:
            deficiencies.append(("Calories", f"{avg_calories:.0f} vs {target_calories} target", "Very low"))
            recommendations.append("Add calorie-dense healthy foods like nuts, avocado, olive oil")
        elif avg_calories < target_calories * 0.9:
            deficiencies.append(("Calories", f"{avg_calories:.0f} vs {target_calories} target", "Slightly low"))
        
        # Check protein (0.8g per kg, assuming 70kg average)
        protein_target = max(50, target_calories * 0.20 / 4)  # 20% of calories, 4 cal/g
        if avg_protein < protein_target * 0.7:
            deficiencies.append(("Protein", f"{avg_protein:.0f}g vs {protein_target:.0f}g target", "Low"))
            recommendations.append("Add lean proteins: chicken, fish, eggs, legumes, Greek yogurt")
        
        # Check carbs
        carbs_target = target_calories * 0.45 / 4  # 45% of calories
        if avg_carbs < carbs_target * 0.5:
            deficiencies.append(("Carbs", f"{avg_carbs:.0f}g vs {carbs_target:.0f}g target", "Very low"))
            recommendations.append("Add whole grains: oats, brown rice, quinoa, whole wheat bread")
        
        # Check fat
        fat_target = target_calories * 0.30 / 9  # 30% of calories, 9 cal/g
        if avg_fat < fat_target * 0.5:
            deficiencies.append(("Fat", f"{avg_fat:.0f}g vs {fat_target:.0f}g target", "Low"))
            recommendations.append("Add healthy fats: avocado, olive oil, nuts, fatty fish")
        elif avg_fat > fat_target * 1.5:
            deficiencies.append(("Fat", f"{avg_fat:.0f}g vs {fat_target:.0f}g target", "High"))
            recommendations.append("Reduce fatty foods and fried items")
        
        result = []
        result.append("**Nutritional Analysis**")
        result.append("")
        
        if not deficiencies:
            result.append("**No major deficiencies detected!**")
            result.append("")
            result.append("Your macronutrient intake appears balanced based on logged meals.")
        else:
            result.append("### Potential Issues")
            for nutrient, value, severity in deficiencies:
                marker = "[!]" if "Very" in severity or "High" in severity else "[-]"
                result.append(f"{marker} {nutrient}: {value} ({severity})")
            
            result.append("")
            result.append("### Recommendations")
            for rec in recommendations:
                result.append(f"- {rec}")
        
        result.append("")
        result.append("---")
        result.append("*Analysis based on logged meals. Log consistently for better accuracy.*")
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Error analyzing deficiencies: {str(e)}"


# ============================================================
# TOOL 4: SUGGEST FOODS FOR GOAL
# ============================================================

@tool
def suggest_foods_for_goal(goal: str, category: str = "") -> str:
    """
    Suggests foods based on user's goal.
    
    Args:
        goal: One of 'lose_weight', 'maintain', 'gain_muscle', 'more_protein', 'more_energy'
        category: Optional food category filter (proteins, vegetables, fruits, grains)
    
    Returns:
        List of recommended foods with explanations
    """
    goal = goal.lower().replace(" ", "_")
    category = category.lower() if category else ""
    
    result = []
    
    if goal in ["lose_weight", "perder_peso", "weight_loss"]:
        result.append("**Foods for Weight Loss**")
        result.append("")
        result.append("**High-Volume, Low-Calorie Foods:**")
        result.append("- Broccoli, cauliflower, spinach, kale")
        result.append("- Tomatoes, cucumbers, zucchini, bell peppers")
        result.append("- Berries, watermelon, grapefruit")
        result.append("")
        result.append("**High-Protein, Satiating Foods:**")
        result.append("- Eggs, egg whites")
        result.append("- White fish, shrimp, tuna")
        result.append("- Greek yogurt, cottage cheese")
        result.append("- Chicken breast, turkey")
        result.append("")
        result.append("**Tips:**")
        result.append("- Prioritize protein at every meal for satiety")
        result.append("- Fill half your plate with vegetables")
        result.append("- Avoid liquid calories")
        
    elif goal in ["gain_muscle", "ganhar_massa", "muscle", "bulk"]:
        result.append("**Foods for Muscle Gain**")
        result.append("")
        result.append("**Protein Sources (aim for 1.6-2.2g/kg bodyweight):**")
        result.append("- Lean beef, chicken breast, turkey")
        result.append("- Salmon, tuna, sardines")
        result.append("- Whole eggs (3-4 daily)")
        result.append("- Greek yogurt, cottage cheese, milk")
        result.append("- Lentils, chickpeas, tofu")
        result.append("")
        result.append("**Calorie-Dense Healthy Foods:**")
        result.append("- Nuts, nut butters")
        result.append("- Avocado")
        result.append("- Rice, pasta, potatoes")
        result.append("- Bananas, dried fruits")
        result.append("")
        result.append("**Tips:**")
        result.append("- Eat protein every 3-4 hours")
        result.append("- Post-workout: fast protein + carbs")
        result.append("- Don't skip breakfast")
        
    elif goal in ["more_protein", "protein"]:
        result.append("**High-Protein Foods**")
        result.append("")
        result.append("**Animal Sources:**")
        result.append("- Chicken breast: 31g per 100g")
        result.append("- Greek yogurt: 10g per 100g")
        result.append("- Eggs: 6g per egg")
        result.append("- Salmon: 25g per 100g")
        result.append("- Cottage cheese: 11g per 100g")
        result.append("")
        result.append("**Plant Sources:**")
        result.append("- Lentils: 9g per 100g (cooked)")
        result.append("- Chickpeas: 8g per 100g")
        result.append("- Tofu: 8g per 100g")
        result.append("- Tempeh: 19g per 100g")
        result.append("- Edamame: 11g per 100g")
        
    elif goal in ["more_energy", "energy", "tired"]:
        result.append("**Foods for Energy**")
        result.append("")
        result.append("**Complex Carbohydrates:**")
        result.append("- Brown rice, quinoa, oats")
        result.append("- Sweet potatoes")
        result.append("- Whole grain bread")
        result.append("")
        result.append("**Iron-Rich Foods:**")
        result.append("- Spinach, lentils")
        result.append("- Red meat (moderate)")
        result.append("")
        result.append("**B-Vitamins:**")
        result.append("- Eggs")
        result.append("- Nuts, seeds")
        result.append("- Bananas")
        
    else:
        result.append("**Balanced Food Suggestions**")
        result.append("")
        for cat_name, cat_info in FOOD_CATEGORIES.items():
            result.append(f"**{cat_name.title()}:** {', '.join(cat_info['foods'][:5])}")
        result.append("")
        result.append("*Aim for variety across all food groups.*")
    
    return "\n".join(result)


# ============================================================
# TOOL 5: GENERATE GROCERY LIST
# ============================================================

@tool
def generate_grocery_list(days: int = 7, servings: int = 1) -> str:
    """
    Generates a grocery list for a week of healthy eating.
    
    Args:
        days: Number of days to plan for (1-14)
        servings: Number of people
    
    Returns:
        Organized grocery list by category
    """
    days = min(max(1, days), 14)
    servings = min(max(1, servings), 10)
    
    # Base quantities per person per week
    base_items = {
        "Proteins": [
            f"Chicken breast: {2 * servings}lb",
            f"Eggs: {12 * servings} (1 dozen per person)",
            f"Greek yogurt: {2 * servings} containers",
            f"Salmon fillets: {2 * servings}",
            f"Lean ground beef/turkey: {1 * servings}lb",
        ],
        "Vegetables": [
            f"Broccoli: {2 * servings} heads",
            f"Spinach: {2 * servings} bags",
            f"Bell peppers: {3 * servings}",
            f"Tomatoes: {4 * servings}",
            f"Carrots: {1 * servings}lb",
            f"Onions: {3 * servings}",
            f"Garlic: {1 * servings} head",
        ],
        "Fruits": [
            f"Bananas: {7 * servings}",
            f"Apples: {4 * servings}",
            f"Berries (frozen or fresh): {2 * servings} containers",
            f"Lemons: {2 * servings}",
        ],
        "Grains & Carbs": [
            f"Brown rice: {2 * servings}lb",
            f"Oats: {1 * servings} container",
            f"Whole wheat bread: {1 * servings} loaf",
            f"Quinoa: {1 * servings}lb",
            f"Sweet potatoes: {4 * servings}",
        ],
        "Dairy & Alternatives": [
            f"Milk (or alternative): {1 * servings} gallon",
            f"Cheese: {8 * servings}oz",
            f"Butter: {1 * servings} stick",
        ],
        "Pantry Staples": [
            "Olive oil: 1 bottle",
            "Almonds/mixed nuts: 1 bag",
            "Honey: 1 jar",
            "Peanut butter: 1 jar",
        ],
    }
    
    # Scale for days
    scale = days / 7
    
    result = []
    result.append(f"**Grocery List ({days} days, {servings} {'person' if servings == 1 else 'people'})**")
    result.append("")
    
    for category, items in base_items.items():
        result.append(f"**{category}**")
        for item in items:
            result.append(f"- [ ] {item}")
        result.append("")
    
    result.append("---")
    result.append("**Tips:** Buy frozen vegetables to reduce waste | Check what you already have | Prep proteins in advance")
    
    return "\n".join(result)


# ============================================================
# EXPORT
# ============================================================

MEAL_PLANNING_TOOLS = [
    generate_meal_plan,
    get_nutrition_summary,
    identify_deficiencies,
    suggest_foods_for_goal,
    generate_grocery_list,
]
