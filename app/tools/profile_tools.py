"""
app/tools/profile_tools.py

COMPLETE profile and meal management tools for the Profile Agent.
Uses PostgreSQL for persistence (database.py).

Features:
- Profile management with calculated metrics (BMI, BMR, TDEE)
- Food diary with calorie estimation
- Statistics and analysis (daily, weekly, monthly)
- Progress vs goals
- Complete input validation
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from datetime import datetime, timedelta
import re

from app.runtime.request_context import get_user_id, writes_allowed, get_memory_manager


# ============================================================
# DATABASE HELPER (PostgreSQL)
# ============================================================

_db_instance = None

def _get_db():
    """
    Gets the PostgreSQL database instance.
    Replaces the old UserDB (SQLite).
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


# Flag for food database (now integrated in PostgreSQL)
FOODS_DB_AVAILABLE = True


# ============================================================
# CONSTANTS AND VALIDATION
# ============================================================

VALID_OBJECTIVES = {
    "lose_weight": "Lose weight/fat",
    "lose weight": "Lose weight/fat",
    "perder_peso": "Lose weight/fat",
    "perder peso": "Lose weight/fat",
    "emagrecer": "Lose weight/fat",
    "maintain": "Maintain current weight",
    "manter": "Maintain current weight",
    "manter_peso": "Maintain current weight",
    "gain_muscle": "Gain muscle mass",
    "ganhar_massa": "Gain muscle mass",
    "ganhar massa": "Gain muscle mass",
    "gain_weight": "Gain weight",
    "ganhar_peso": "Gain weight",
}

VALID_ACTIVITY_LEVELS = {
    "sedentary": ("Sedentary", 1.2),
    "sedentario": ("Sedentary", 1.2),
    "sedentário": ("Sedentary", 1.2),
    "light": ("Light (Exercise 1-3x/week)", 1.375),
    "leve": ("Light (Exercise 1-3x/week)", 1.375),
    "moderate": ("Moderate (Exercise 3-5x/week)", 1.55),
    "moderado": ("Moderate (Exercise 3-5x/week)", 1.55),
    "active": ("Active (Exercise 6-7x/week)", 1.725),
    "ativo": ("Active (Exercise 6-7x/week)", 1.725),
    "very_active": ("Very Active (2x/day)", 1.9),
    "muito_ativo": ("Very Active (2x/day)", 1.9),
}

VALID_SEXES = {
    "m": "Male",
    "male": "Male",
    "masculino": "Male",
    "homem": "Male",
    "f": "Female",
    "female": "Female",
    "feminino": "Female",
    "mulher": "Female",
}

MEAL_TYPES = {
    "breakfast": "☀️ Breakfast",
    "pequeno_almoco": "☀️ Breakfast",
    "pequeno-almoco": "☀️ Breakfast",
    "pequeno almoço": "☀️ Breakfast",
    "lunch": "🌤️ Lunch",
    "almoco": "🌤️ Lunch",
    "almoço": "🌤️ Lunch",
    "snack": "🍎 Snack",
    "lanche": "🍎 Snack",
    "dinner": "🌙 Dinner",
    "jantar": "🌙 Dinner",
    "supper": "🌜 Supper",
    "ceia": "🌜 Supper",
    "other": "🍽️ Other",
    "outro": "🍽️ Other",
}

# Validation limits
LIMITS = {
    "idade": (1, 120),
    "peso": (20, 500),
    "altura": (50, 280),
}


def _normalize(text: str) -> str:
    """Normalizes text for comparison."""
    if not text:
        return ""
    return text.lower().strip().replace("-", "_").replace(" ", "_")


def _calculate_bmi(weight_kg: float, height_cm: float) -> tuple[float, str]:
    """Calculates BMI and classification."""
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)
    
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal weight"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"
    
    return round(bmi, 1), category


def _calculate_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    """Calculates BMR using Mifflin-St Jeor formula.
    Returns unrounded value so TDEE and calorie goal can be computed
    without intermediate-rounding drift.  Callers use :.0f for display.
    """
    sex_norm = _normalize(sex)
    if sex_norm in ["m", "masculino", "homem"]:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return bmr


def _calculate_tdee(bmr: float, activity: str) -> float:
    """Calculates TDEE based on BMR and activity level.
    Returns unrounded value — callers use :.0f for display.
    """
    activity_norm = _normalize(activity)
    multiplier = VALID_ACTIVITY_LEVELS.get(activity_norm, ("", 1.55))[1]
    return bmr * multiplier


def _calculate_calorie_goal(tdee: float, objective: str) -> tuple[float, str]:
    """Calculates calorie goal based on objective."""
    obj_norm = _normalize(objective)
    
    if obj_norm in ["perder_peso", "perder peso", "emagrecer", "lose_weight"]:
        goal = tdee - 500
        desc = "500 kcal deficit for weight loss"
    elif obj_norm in ["ganhar_massa", "ganhar massa", "ganhar_peso", "gain_muscle", "gain_weight"]:
        goal = tdee + 300
        desc = "300 kcal surplus for muscle gain"
    else:
        goal = tdee
        desc = "Maintenance of current weight"
    
    return round(goal, 0), desc


def _estimate_calories(description: str) -> Optional[int]:
    """Tries to estimate calories from description using PostgreSQL database."""
    if not FOODS_DB_AVAILABLE:
        return None
    
    try:
        db = _get_db()
    except Exception:
        return None
    
    # Extract quantity if mentioned (e.g., "200g of rice")
    quantity_match = re.search(r'(\d+)\s*g', description.lower())
    quantity = int(quantity_match.group(1)) if quantity_match else 100
    
    # Search for foods in description
    total_calories = 0
    foods_found = 0
    
    # Common food keywords
    food_keywords = description.lower().replace(",", " ").replace("com", " ").replace("e", " ").split()
    
    for word in food_keywords:
        if len(word) < 3:
            continue
        try:
            results = db.search_foods(word, limit=1)
            if results:
                food = results[0]
                cal_per_100g = food.kcal_100g if hasattr(food, 'kcal_100g') else 0
                if cal_per_100g > 0:
                    total_calories += (cal_per_100g * quantity / 100)
                    foods_found += 1
                    if foods_found >= 3:  # Limit to 3 foods
                        break
        except Exception:
            continue
    
    return int(total_calories) if total_calories > 0 else None


# ============================================================
# PROFILE TOOLS
# ============================================================

def _profile_to_dict(profile) -> dict:
    """Converts UserProfile object to dictionary."""
    def _ensure_profile_key_aliases(p: dict) -> dict:
        # Backward-compatible aliases (pt <-> en), but English is canonical.
        mapping = {
            "nome": "name",
            "idade": "age",
            "peso": "weight",
            "altura": "height",
            "sexo": "gender",
            "objetivo": "goal",
            "atividade": "activity",
            "restricoes": "restrictions",
            "preferencias": "preferences",
            "imc": "bmi",
            "tmb": "bmr",
            "meta_calorica": "calorie_goal",
        }

        for pt_key, en_key in mapping.items():
            if pt_key in p and en_key not in p:
                p[en_key] = p[pt_key]
            if en_key in p and pt_key not in p:
                p[pt_key] = p[en_key]
        return p

    if profile is None:
        return {}
    if isinstance(profile, dict):
        return _ensure_profile_key_aliases(profile)
    # UserProfile has to_dict() method
    if hasattr(profile, 'to_dict'):
        return _ensure_profile_key_aliases(profile.to_dict())
    # Fallback for dataclass
    if hasattr(profile, '__dataclass_fields__'):
        from dataclasses import asdict
        return _ensure_profile_key_aliases(asdict(profile))
    # Manual fallback
    result = {}
    for attr in [
        'name', 'age', 'weight', 'height', 'gender', 'goal',
        'activity', 'restrictions', 'preferences',
        'bmi', 'bmr', 'tdee', 'calorie_goal',
        'nome', 'idade', 'peso', 'altura', 'sexo', 'objetivo',
        'atividade', 'restricoes', 'preferencias',
        'imc', 'tmb', 'meta_calorica',
        'created_at', 'updated_at'
    ]:
        if hasattr(profile, attr):
            value = getattr(profile, attr)
            if value is not None:
                result[attr] = value
    return _ensure_profile_key_aliases(result)


def _meal_to_dict(meal) -> dict:
    """Converts Meal object to dictionary."""
    if meal is None:
        return {}
    if isinstance(meal, dict):
        return meal
    # Meal has to_dict() method
    if hasattr(meal, 'to_dict'):
        return meal.to_dict()
    # Fallback for dataclass
    if hasattr(meal, '__dataclass_fields__'):
        from dataclasses import asdict
        return asdict(meal)
    # Manual fallback
    result = {}
    for attr in ['id', 'user_id', 'meal_id', 'date', 'time', 'meal_type',
                 'description', 'calories', 'protein', 'carbs', 'fat', 'notes', 'created_at']:
        if hasattr(meal, attr):
            value = getattr(meal, attr)
            if value is not None:
                result[attr] = value
    return result


def _meals_to_dicts(meals: list) -> list:
    """Converts list of Meal to list of dictionaries."""
    return [_meal_to_dict(m) for m in meals]


@tool
def get_user_profile() -> str:
    """
    Gets the user's complete profile with calculated metrics.
    
    Returns personal information, objectives and metrics like BMI, BMR and TDEE.
    
    Returns:
        Formatted profile with all information and metrics
    """
    db = _get_db()
    profile_obj = db.get_profile(user_id=get_user_id())
    profile = _profile_to_dict(profile_obj)
    
    if not profile:
        return """## ❌ Profile Not Found

You don't have a profile yet. To create one, tell me:
- **Name** (optional)
- **Age** (years)
- **Weight** (kg)
- **Height** (cm)
- **Sex** (M/F)
- **Goal** (lose weight, maintain, gain muscle)
- **Activity level** (sedentary, light, moderate, active)

💡 Example: "I'm 30 years old, weigh 70kg, 175cm tall, male, want to lose weight, moderate activity"
"""
    
    # Build response
    response = "## 📋 Your Profile\n\n"
    
    # Personal data
    response += "### Personal Data\n"
    response += "| Field | Value |\n|-------|-------|\n"
    
    if profile.get("name"):
        response += f"| 👤 Name | {profile['name']} |\n"
    if profile.get("age"):
        response += f"| 🎂 Age | {profile['age']} years |\n"
    if profile.get("weight"):
        response += f"| ⚖️ Weight | {profile['weight']} kg |\n"
    if profile.get("height"):
        response += f"| 📏 Height | {profile['height']} cm |\n"
    if profile.get("gender"):
        sex_display = VALID_SEXES.get(_normalize(profile['gender']), profile['gender'])
        response += f"| 👫 Sex | {sex_display} |\n"
    
    # Objectives
    response += "\n### Objectives\n"
    response += "| Field | Value |\n|-------|-------|\n"
    
    if profile.get("goal"):
        obj_display = VALID_OBJECTIVES.get(_normalize(profile['goal']), profile['goal'])
        response += f"| 🎯 Goal | {obj_display} |\n"
    if profile.get("activity"):
        act_display = VALID_ACTIVITY_LEVELS.get(_normalize(profile['activity']), ("", 1.55))[0]
        response += f"| 🏃 Activity | {act_display} |\n"
    
    # Restrictions and preferences (always show diet type field)
    diet_type = profile.get("restrictions")
    if diet_type:
        response += f"| 🥗 Diet Type | {diet_type.title()} |\n"
    else:
        response += "| 🥗 Diet Type | Not specified |\n"
    if profile.get("preferences"):
        response += f"| 💚 Preferences | {profile['preferences']} |\n"
    
    # Calculated metrics (if sufficient data)
    peso = profile.get("weight")
    altura = profile.get("height")
    idade = profile.get("age")
    sexo = profile.get("gender")
    atividade = profile.get("activity", "moderate")
    objetivo = profile.get("goal", "maintain")
    
    if peso and altura:
        response += "\n### 📊 Calculated Metrics\n"
        response += "| Metric | Value |\n|---------|-------|\n"
        
        # BMI
        bmi, bmi_cat = _calculate_bmi(peso, altura)
        response += f"| 📊 BMI | {bmi} kg/m² ({bmi_cat}) |\n"
        
        # BMR and TDEE (if age and sex available)
        if idade and sexo:
            bmr = _calculate_bmr(peso, altura, idade, sexo)
            tdee = _calculate_tdee(bmr, atividade)
            goal, goal_desc = _calculate_calorie_goal(tdee, objetivo)
            
            response += f"| 🔥 BMR | {bmr:.0f} kcal/day |\n"
            response += f"| ⚡ TDEE | {tdee:.0f} kcal/day |\n"
            response += f"| 🎯 Calorie Goal | {goal:.0f} kcal/day |\n"
            
            response += f"\n💡 *{goal_desc}*\n"
    
    # Timestamps
    if profile.get("created_at") or profile.get("updated_at"):
        response += "\n---\n"
        if profile.get("created_at"):
            created = profile['created_at']
            if hasattr(created, 'strftime'):
                created = created.strftime("%Y-%m-%d")
            elif isinstance(created, str) and len(created) >= 10:
                created = created[:10]
            response += f"📅 Created: {created}\n"
        if profile.get("updated_at"):
            updated = profile['updated_at']
            if hasattr(updated, 'strftime'):
                updated = updated.strftime("%Y-%m-%d")
            elif isinstance(updated, str) and len(updated) >= 10:
                updated = updated[:10]
            response += f"🔄 Updated: {updated}\n"
    
    return response


@tool
def save_user_profile(
    # English (canonical)
    name: Optional[str] = None,
    age: Optional[int] = None,
    weight: Optional[float] = None,
    height: Optional[float] = None,
    gender: Optional[str] = None,
    goal: Optional[str] = None,
    activity: Optional[str] = None,
    restrictions: Optional[str] = None,
    preferences: Optional[str] = None,
    # Portuguese aliases (accepted)
    nome: Optional[str] = None,
    idade: Optional[int] = None,
    peso: Optional[float] = None,
    altura: Optional[float] = None,
    sexo: Optional[str] = None,
    objetivo: Optional[str] = None,
    atividade: Optional[str] = None,
    restricoes: Optional[str] = None,
    preferencias: Optional[str] = None,
) -> str:
    """
    Saves or updates the user's profile.
    
    Accepts any combination of fields - updates only the provided ones.
    Validates all inputs before saving.
    
    Args:
        nome: User's name
        idade: Age in years (1-120)
        peso: Weight in kg (20-500)
        altura: Height in cm (50-280)
        sexo: Sex (M/F, male/female)
        objetivo: Goal (lose_weight, maintain, gain_muscle)
        atividade: Activity level (sedentary, light, moderate, active, very_active)
        restricoes: Dietary restrictions (e.g., "gluten-free, vegetarian")
        preferencias: Food preferences (e.g., "mediterranean cuisine")
    
    Returns:
        Confirmation with saved data
    """
    errors = []
    updates: Dict[str, Any] = {}
    
    # Validate and process each field
    if name is None and nome is not None:
        name = nome
    if name is not None:
        updates["name"] = name.strip()
    
    if age is None and idade is not None:
        age = idade
    if age is not None:
        if LIMITS["idade"][0] <= age <= LIMITS["idade"][1]:
            updates["age"] = age
        else:
            errors.append(f"❌ Age must be between {LIMITS['idade'][0]} and {LIMITS['idade'][1]} years")
    
    if weight is None and peso is not None:
        weight = peso
    if weight is not None:
        if LIMITS["peso"][0] <= weight <= LIMITS["peso"][1]:
            updates["weight"] = weight
        else:
            errors.append(f"❌ Weight must be between {LIMITS['peso'][0]} and {LIMITS['peso'][1]} kg")
    
    if height is None and altura is not None:
        height = altura
    if height is not None:
        if LIMITS["altura"][0] <= height <= LIMITS["altura"][1]:
            updates["height"] = int(height)
        else:
            errors.append(f"❌ Height must be between {LIMITS['altura'][0]} and {LIMITS['altura'][1]} cm")
    
    if gender is None and sexo is not None:
        gender = sexo
    if gender is not None:
        sexo_norm = _normalize(gender)
        if sexo_norm in VALID_SEXES:
            # Database expects CHAR(1): 'M' or 'F'
            gender_char = "M" if VALID_SEXES[sexo_norm] == "Male" else "F"
            updates["gender"] = gender_char
        else:
            errors.append(f"❌ Invalid sex. Use: M, F, male, female")
    
    if goal is None and objetivo is not None:
        goal = objetivo
    if goal is not None:
        obj_norm = _normalize(goal)
        if obj_norm in VALID_OBJECTIVES:
            # Database expects: lose|maintain|gain
            goal_map = {
                "lose_weight": "lose",
                "perder_peso": "lose",
                "perder_peso": "lose",
                "emagrecer": "lose",
                "maintain": "maintain",
                "manter": "maintain",
                "manter_peso": "maintain",
                "gain_muscle": "gain",
                "ganhar_massa": "gain",
                "ganhar_peso": "gain",
                "gain_weight": "gain",
            }
            updates["goal"] = goal_map.get(obj_norm, obj_norm)
        else:
            errors.append(f"❌ Invalid goal. Use: lose_weight, maintain, gain_muscle")
    
    if activity is None and atividade is not None:
        activity = atividade
    if activity is not None:
        act_norm = _normalize(activity)
        if act_norm in VALID_ACTIVITY_LEVELS:
            # Database expects English keys
            activity_map = {
                "sedentario": "sedentary",
                "sedentário": "sedentary",
                "leve": "light",
                "moderado": "moderate",
                "ativo": "active",
                "muito_ativo": "very_active",
            }
            updates["activity"] = activity_map.get(act_norm, act_norm)
        else:
            errors.append(f"❌ Invalid activity. Use: sedentary, light, moderate, active, very_active")
    
    if restrictions is None and restricoes is not None:
        restrictions = restricoes
    if restrictions is not None:
        # Normalize to list for database compatibility
        if isinstance(restrictions, str):
            updates["restrictions"] = [r.strip() for r in restrictions.split(",") if r.strip()]
        elif isinstance(restrictions, list):
            updates["restrictions"] = restrictions
        else:
            updates["restrictions"] = [str(restrictions).strip()]
    
    if preferences is None and preferencias is not None:
        preferences = preferencias
    if preferences is not None:
        # Normalize to list for database compatibility
        if isinstance(preferences, str):
            updates["preferences"] = [p.strip() for p in preferences.split(",") if p.strip()]
        elif isinstance(preferences, list):
            updates["preferences"] = preferences
        else:
            updates["preferences"] = [str(preferences).strip()]
    
    # If there are errors, return
    if errors:
        return "## ⚠️ Validation Errors\n\n" + "\n".join(errors)
    
    # If no updates
    if not updates:
        return "⚠️ No data provided to save."
    
    # Confirmation gate: do not write from agent flow without explicit confirmation.
    if not writes_allowed():
        mm = get_memory_manager()
        if mm:
            # Clear any previous pending update before setting new one
            mm.confirm_pending_profile_update()  # Clear old
            mm.set_pending_profile_update({"updates": updates, "created_at": datetime.now().isoformat()})
        
        # Build simple confirmation message
        changes_list = []
        for key, value in updates.items():
            field_name = key.replace("_", " ").title()
            if key == "gender":
                value = "Female" if value == "F" else "Male"
            elif key == "weight":
                value = f"{value} kg"
            elif key == "height":
                value = f"{value} cm"
            elif key == "age":
                value = f"{value} years"
            changes_list.append(f"• **{field_name}**: {value}")
        
        response = "**Profile Update**\n\n"
        response += "Proposed changes:\n"
        response += "\n".join(changes_list)
        response += "\n\nReply **CONFIRM** to save or **CANCEL** to discard."
        return response

    # Save (allowed)
    db = _get_db()
    success, changes_made = db.save_profile(user_id=get_user_id(), **updates)
    
    if success:
        response = "## ✅ Profile Updated!\n\n"
        response += "### Saved data:\n"
        response += "| Field | Value |\n|-------|-------|\n"
        
        for key, value in updates.items():
            emoji = {
                "name": "👤", "age": "🎂", "weight": "⚖️",
                "height": "📏", "gender": "👫", "goal": "🎯",
                "activity": "🏃", "restrictions": "⚠️", "preferences": "💚"
            }.get(key, "•")
            
            # Format values
            if key == "goal":
                value = VALID_OBJECTIVES.get(value, value)
            elif key == "activity":
                value = VALID_ACTIVITY_LEVELS.get(value, ("", 1.55))[0]
            elif key == "weight":
                value = f"{value} kg"
            elif key == "height":
                value = f"{value} cm"
            elif key == "age":
                value = f"{value} years"
            
            response += f"| {emoji} {key.title()} | {value} |\n"
        
        return response
    else:
        return "❌ Error saving profile. Try again."


@tool
def update_user_profile(field: str, value: str) -> str:
    """
    Updates a specific field in the profile.
    
    Useful for quick single-field updates.
    
    Args:
        field: Field to update (nome, idade, peso, altura, sexo, objetivo, atividade)
        value: New value
    
    Returns:
        Update confirmation
    
    Example:
        update_user_profile("peso", "72")
    """
    field_norm = _normalize(field)
    
    # Map fields
    field_map = {
        # English
        "name": "name",
        "age": "age",
        "weight": "weight",
        "height": "height",
        "gender": "gender",
        "goal": "goal",
        "activity": "activity",
        "restrictions": "restrictions",
        "preferences": "preferences",
        # Portuguese aliases
        "nome": "name",
        "idade": "age",
        "peso": "weight",
        "altura": "height",
        "sexo": "gender",
        "objetivo": "goal",
        "atividade": "activity",
        "restricoes": "restrictions",
        "preferencias": "preferences",
    }
    
    if field_norm not in field_map:
        return f"❌ Field '{field}' not recognized. Valid fields: {', '.join(field_map.keys())}"
    
    # Convert value to correct type
    actual_field = field_map[field_norm]
    
    try:
        if actual_field in ["age"]:
            value = int(value)
        elif actual_field in ["weight", "height"]:
            value = float(value.replace(",", "."))
    except ValueError:
        return f"❌ Invalid value '{value}' for field '{field}'"
    
    # Use save_user_profile with specific field
    kwargs = {actual_field: value}
    return save_user_profile.invoke(kwargs)


@tool
def clear_user_profile() -> str:
    """
    Completely clears the user's profile.
    
    ⚠️ This action is irreversible! Meal history is preserved.
    
    Returns:
        Confirmation that profile was cleared
    """
    if not writes_allowed():
        mm = get_memory_manager()
        if mm:
            mm.set_pending_profile_update({"clear": True, "created_at": datetime.now().isoformat()})
        return "## ⏸️ Profile Clear Pending Confirmation\n\nReply **CONFIRM** to clear your profile, or **CANCEL** to discard."

    db = _get_db()
    success = db.clear_profile(user_id=get_user_id())
    
    if success:
        return """## 🗑️ Profile Cleared

✅ All profile data has been removed.

📝 Your meal history has been **preserved**.

💡 To create a new profile, tell me your data:
- Age, weight, height, sex
- Goal (lose weight, maintain, gain muscle)
- Activity level
"""
    else:
        return "❌ Error clearing profile."


# ============================================================
# MEAL TOOLS
# ============================================================

@tool
def log_meal(
    description: str,
    meal_type: Optional[str] = None,
    calories: Optional[int] = None,
    protein: Optional[float] = None,
    carbs: Optional[float] = None,
    fat: Optional[float] = None,
    notes: Optional[str] = None
) -> str:
    """
    Logs a meal to the food diary.
    
    If calories are not provided, the system automatically estimates them
    using the USDA database.
    
    Args:
        description: Meal description (e.g., "Grilled chicken with rice")
        meal_type: Meal type (breakfast, lunch, snack, dinner, supper)
        calories: Calories (optional - will be estimated if not provided)
        protein: Protein in grams (optional)
        carbs: Carbohydrates in grams (optional)
        fat: Fat in grams (optional)
        notes: Additional notes (optional)
    
    Returns:
        Confirmation with logged meal details
    
    Example:
        log_meal("Chicken salad with rice", meal_type="lunch", calories=450)
    """
    if not description or len(description.strip()) < 3:
        return "❌ Please describe the meal (minimum 3 characters)."
    
    # Normalize meal type
    meal_type_norm = None
    meal_type_display = "🍽️ Meal"
    
    if meal_type:
        meal_type_norm = _normalize(meal_type)
        if meal_type_norm in MEAL_TYPES:
            meal_type_display = MEAL_TYPES[meal_type_norm]
        else:
            meal_type_norm = "other"
            meal_type_display = "🍽️ Other"
    
    # Estimate calories if not provided
    estimated = False
    if calories is None:
        calories = _estimate_calories(description)
        if calories:
            estimated = True
    
    meal_payload = {
        "description": description.strip(),
        "meal_type": meal_type_norm,
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "notes": notes,
    }

    if not writes_allowed():
        mm = get_memory_manager()
        if mm:
            mm.set_pending_meal(meal_payload)
        response = "## ⏸️ Meal Log Pending Confirmation\n\n"
        response += "I can log this meal, but I won't save it yet.\n\n"
        response += f"📝 {meal_payload['description']}\n"
        if meal_payload.get("meal_type"):
            response += f"🍽️ Type: {meal_payload['meal_type']}\n"
        if meal_payload.get("calories"):
            response += f"🔥 Calories: {meal_payload['calories']}\n"
        response += "\nReply **CONFIRM** to log it, or **CANCEL** to discard."
        return response

    # Log meal (allowed)
    db = _get_db()
    try:
        meal_obj = db.log_meal(user_id=get_user_id(), **meal_payload)
    except ValueError as e:
        # Food validation failed - this is not a valid food item
        return f"❌ {str(e)}"
    
    if meal_obj:
        now = datetime.now()
        response = f"## ✅ Meal Logged!\n\n"
        response += f"**{meal_type_display}** - {now.strftime('%H:%M')}\n\n"
        response += f"📝 {description}\n\n"
        
        if calories:
            cal_note = " *(estimated)*" if estimated else ""
            response += f"🔥 **Calories:** {calories} kcal{cal_note}\n"
        
        if protein or carbs or fat:
            response += "\n**Macros:**\n"
            if protein:
                response += f"- 🥩 Protein: {protein}g\n"
            if carbs:
                response += f"- 🍚 Carbohydrates: {carbs}g\n"
            if fat:
                response += f"- 🥑 Fat: {fat}g\n"
        
        if notes:
            response += f"\n📌 *{notes}*\n"
        
        # Daily summary
        today_stats = db.get_daily_totals(user_id=get_user_id())
        if today_stats and today_stats.get('count', today_stats.get('meal_count', 0)) > 0:
            meal_count = today_stats.get('count', today_stats.get('meal_count', 0))
            total_cal = today_stats.get('calories', 0)
            response += f"\n---\n"
            response += f"📊 **Today:** {meal_count} meals, {total_cal} kcal total\n"
        
        return response
    else:
        return "❌ Error logging meal. Try again."


@tool
def get_meals_today() -> str:
    """
    Shows today's food summary with progress vs calorie goal.
    
    Includes all meals logged today, total calories,
    and comparison with profile calorie goal.
    
    Returns:
        Daily summary with meals and progress
    """
    db = _get_db()
    meals_raw = db.get_meals_today(user_id=get_user_id())
    meals = _meals_to_dicts(meals_raw)
    profile = _profile_to_dict(db.get_profile(user_id=get_user_id()))
    
    today = datetime.now().strftime("%d/%m/%Y")
    
    if not meals:
        return f"""## 📅 Today ({today})

📭 You haven't logged any meals today.

💡 To log a meal, say something like:
- "I had rice with chicken for lunch"
- "Breakfast: yogurt with granola"
- "Log 2 eggs and toasted bread"
"""
    
    response = f"## 📅 Today's Diary ({today})\n\n"
    
    # List meals
    response += "### 🍽️ Meals\n\n"
    total_calories = 0
    total_protein = 0
    total_carbs = 0
    total_fat = 0
    
    for meal in meals:
        meal_type = MEAL_TYPES.get(meal.get("meal_type", "other"), "🍽️")
        time = meal.get("time", "")[:5] if meal.get("time") else ""
        desc = meal.get("description", "")
        cal = meal.get("calories", 0) or 0
        
        response += f"**{time}** {meal_type}\n"
        response += f"- {desc}"
        if cal:
            response += f" ({cal} kcal)"
        response += "\n\n"
        
        total_calories += cal
        total_protein += meal.get("protein", 0) or 0
        total_carbs += meal.get("carbs", 0) or 0
        total_fat += meal.get("fat", 0) or 0
    
    # Totals
    response += "---\n"
    response += f"### 📊 Daily Totals\n\n"
    response += f"🔥 **Calories:** {total_calories} kcal\n"
    
    if total_protein or total_carbs or total_fat:
        response += f"🥩 **Protein:** {total_protein:.0f}g\n"
        response += f"🍚 **Carbohydrates:** {total_carbs:.0f}g\n"
        response += f"🥑 **Fat:** {total_fat:.0f}g\n"
    
    # Progress vs goal (if profile exists)
    if profile:
        peso = profile.get("weight")
        altura = profile.get("height")
        idade = profile.get("age")
        sexo = profile.get("gender")
        atividade = profile.get("activity", "moderate")
        objetivo = profile.get("goal", "maintain")
        
        if peso and altura and idade and sexo:
            bmr = _calculate_bmr(peso, altura, idade, sexo)
            tdee = _calculate_tdee(bmr, atividade)
            goal, _ = _calculate_calorie_goal(tdee, objetivo)
            
            remaining = goal - total_calories
            percentage = (total_calories / goal * 100) if goal > 0 else 0
            
            response += f"\n### 🎯 Progress\n\n"
            response += f"**Goal:** {goal:.0f} kcal | **Consumed:** {total_calories} kcal ({percentage:.0f}%)\n\n"
            
            # Visual progress bar
            filled = int(percentage / 10)
            empty = 10 - filled
            bar = "█" * min(filled, 10) + "░" * max(empty, 0)
            response += f"`[{bar}]` {percentage:.0f}%\n\n"
            
            if remaining > 0:
                response += f"✅ **{remaining:.0f} kcal** remaining to reach goal\n"
            elif remaining < -200:
                response += f"⚠️ You've exceeded the goal by **{abs(remaining):.0f} kcal**\n"
            else:
                response += f"✅ Goal reached! Great job! 🎉\n"
    
    return response


@tool
def get_meals_history(days: int = 7) -> str:
    """
    Shows meal history with statistics.
    
    Includes daily totals, averages, and trends over the period.
    
    Args:
        days: Number of days to show (1-30, default: 7)
    
    Returns:
        History with statistics and analysis
    """
    if days < 1:
        days = 1
    elif days > 30:
        days = 30
    
    db = _get_db()
    stats = db.get_stats(user_id=get_user_id())
    
    if not stats or stats.get("total_meals", 0) == 0:
        return f"""## 📈 History ({days} days)

📭 You don't have any logged meals.

💡 Start logging your meals to see statistics!
"""
    
    response = f"## 📈 {days}-Day History\n\n"
    
    # General statistics
    response += "### 📊 General Statistics\n\n"
    response += "| Metric | Value |\n|---------|-------|\n"
    response += f"| 📝 Total Meals | {stats.get('total_meals', 0)} |\n"
    response += f"| 📅 Days Logged | {stats.get('days_with_meals', stats.get('days_logged', 0))} |\n"
    
    avg_cal = stats.get("avg_daily_calories", 0)
    if avg_cal:
        response += f"| 🔥 Daily Average | {avg_cal:.0f} kcal |\n"
    
    total_cal = stats.get("total_calories", 0)
    if total_cal:
        response += f"| ⚡ Period Total | {total_cal:.0f} kcal |\n"
    
    # Recent meals
    meals_raw = db.get_meals_history(days=days, user_id=get_user_id())
    meals = _meals_to_dicts(meals_raw)
    
    if meals:
        response += f"\n### 🗓️ Recent Meals\n\n"
        
        # Group by date
        by_date = {}
        for meal in meals[-20:]:  # Last 20
            date = meal.get("date", "")
            if hasattr(date, 'strftime'):
                date = date.strftime("%Y-%m-%d")
            elif not isinstance(date, str):
                date = str(date)
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(meal)
        
        for date in sorted(by_date.keys(), reverse=True)[:5]:  # Last 5 days
            date_meals = by_date[date]
            day_calories = sum(m.get("calories", 0) or 0 for m in date_meals)
            
            # Format date
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                date_formatted = date_obj.strftime("%d/%m")
            except:
                date_formatted = date
            
            response += f"**{date_formatted}** - {len(date_meals)} meals, {day_calories} kcal\n"
    
    # Analysis based on data
    response += "\n### 💡 Analysis\n\n"
    
    if avg_cal > 0:
        profile = _profile_to_dict(db.get_profile(user_id=get_user_id()))
        if profile:
            peso = profile.get("weight")
            altura = profile.get("height")
            idade = profile.get("age")
            sexo = profile.get("gender")
            atividade = profile.get("activity", "moderate")
            objetivo = profile.get("goal", "maintain")
            
            if peso and altura and idade and sexo:
                bmr = _calculate_bmr(peso, altura, idade, sexo)
                tdee = _calculate_tdee(bmr, atividade)
                goal, _ = _calculate_calorie_goal(tdee, objetivo)
                
                diff = avg_cal - goal
                if abs(diff) < 100:
                    response += "✅ Your calorie average is aligned with your goal!\n"
                elif diff > 0:
                    response += f"⚠️ You're consuming on average **{diff:.0f} kcal** above your goal.\n"
                else:
                    response += f"📉 You're consuming on average **{abs(diff):.0f} kcal** below your goal.\n"
    
    return response


@tool
def clear_meals_history() -> str:
    """
    Clears all meal history.
    
    ⚠️ This action is irreversible! Profile is preserved.
    
    Returns:
        Confirmation that history was cleared
    """
    if not writes_allowed():
        mm = get_memory_manager()
        if mm:
            mm.set_pending_profile_update({"clear_meals": True, "created_at": datetime.now().isoformat()})
        return "## ⏸️ Clear Meal History Pending Confirmation\n\nReply **CONFIRM** to delete all your meal history, or **CANCEL** to discard."

    db = _get_db()
    deleted_count = db.clear_meals(user_id=get_user_id())
    
    if deleted_count >= 0:  # 0 is valid if there were no meals
        return f"""## 🗑️ History Cleared

✅ {deleted_count} meals have been removed.

📝 Your profile has been **preserved**.

💡 You can start logging new meals anytime!
"""
    else:
        return "❌ No meals to clear."


@tool
def get_nutrition_summary(period: str = "week") -> str:
    """
    Generates a detailed nutritional summary for a period.
    
    Includes averages, macro distribution, and recommendations.
    
    Args:
        period: Summary period (day, week, month)
    
    Returns:
        Complete nutritional summary with analysis
    """
    period_norm = _normalize(period)
    
    days_map = {
        "day": 1,
        "today": 1,
        "dia": 1,
        "hoje": 1,
        "week": 7,
        "semana": 7,
        "month": 30,
        "mes": 30,
        "mês": 30,
    }
    
    days = days_map.get(period_norm, 7)
    
    db = _get_db()
    
    meals_raw = db.get_meals_history(days=days, user_id=get_user_id())
    meals = _meals_to_dicts(meals_raw)
    
    period_names = {
        1: "Today",
        7: "This Week",
        30: "This Month",
    }
    period_name = period_names.get(days, f"Last {days} days")
    
    if not meals:
        return f"""## 📊 Nutritional Summary - {period_name}

📭 You don't have any logged meals for this period.

💡 Log your meals to get a detailed summary!
"""
    
    response = f"## 📊 Nutritional Summary - {period_name}\n\n"
    
    # Calculate totals
    total_meals = len(meals)
    total_calories = sum(m.get("calories", 0) or 0 for m in meals)
    total_protein = sum(m.get("protein", 0) or 0 for m in meals)
    total_carbs = sum(m.get("carbs", 0) or 0 for m in meals)
    total_fat = sum(m.get("fat", 0) or 0 for m in meals)
    
    # Unique days
    unique_dates = set()
    for m in meals:
        date = m.get("date", "")
        if hasattr(date, 'strftime'):
            date = date.strftime("%Y-%m-%d")
        unique_dates.add(str(date))
    unique_days = len(unique_dates)
    
    # Daily averages
    avg_daily_cal = total_calories / unique_days if unique_days > 0 else 0
    avg_daily_meals = total_meals / unique_days if unique_days > 0 else 0
    
    # Statistics
    response += "### 📈 Statistics\n\n"
    response += "| Metric | Total | Avg/Day |\n|---------|-------|----------|\n"
    response += f"| 🍽️ Meals | {total_meals} | {avg_daily_meals:.1f} |\n"
    response += f"| 🔥 Calories | {total_calories} kcal | {avg_daily_cal:.0f} kcal |\n"
    
    if total_protein > 0:
        avg_protein = total_protein / unique_days if unique_days > 0 else 0
        response += f"| 🥩 Protein | {total_protein:.0f}g | {avg_protein:.0f}g |\n"
    if total_carbs > 0:
        avg_carbs = total_carbs / unique_days if unique_days > 0 else 0
        response += f"| 🍚 Carbohydrates | {total_carbs:.0f}g | {avg_carbs:.0f}g |\n"
    if total_fat > 0:
        avg_fat = total_fat / unique_days if unique_days > 0 else 0
        response += f"| 🥑 Fat | {total_fat:.0f}g | {avg_fat:.0f}g |\n"
    
    # Distribution by meal type
    by_type = {}
    for meal in meals:
        mt = meal.get("meal_type", "other") or "other"
        if mt not in by_type:
            by_type[mt] = {"count": 0, "calories": 0}
        by_type[mt]["count"] += 1
        by_type[mt]["calories"] += meal.get("calories", 0) or 0
    
    if by_type:
        response += "\n### 🍽️ By Meal Type\n\n"
        response += "| Type | Meals | Calories |\n|------|-----------|----------|\n"
        for mt, data in sorted(by_type.items(), key=lambda x: -x[1]["count"]):
            mt_display = MEAL_TYPES.get(mt, "🍽️ Other")
            response += f"| {mt_display} | {data['count']} | {data['calories']} kcal |\n"
    
    # Comparison with goal
    profile = _profile_to_dict(db.get_profile())
    if profile:
        peso = profile.get("weight")
        altura = profile.get("height")
        idade = profile.get("age")
        sexo = profile.get("gender")
        atividade = profile.get("atividade", "moderado")
        objetivo = profile.get("objetivo", "manter")
        
        if peso and altura and idade and sexo:
            bmr = _calculate_bmr(peso, altura, idade, sexo)
            tdee = _calculate_tdee(bmr, atividade)
            goal, goal_desc = _calculate_calorie_goal(tdee, objetivo)
            
            response += "\n### 🎯 Goal Comparison\n\n"
            response += f"**Daily Goal:** {goal:.0f} kcal ({goal_desc})\n"
            response += f"**Actual Average:** {avg_daily_cal:.0f} kcal\n\n"
            
            diff = avg_daily_cal - goal
            if abs(diff) < 100:
                response += "✅ **Excellent!** You're within your goal.\n"
            elif diff > 0:
                response += f"⚠️ You're **{diff:.0f} kcal above** your goal on average.\n"
            else:
                response += f"📉 You're **{abs(diff):.0f} kcal below** your goal on average.\n"
    
    return response


# ============================================================
# TOOLS LIST FOR EXPORT
# ============================================================

PROFILE_TOOLS = [
    get_user_profile,
    save_user_profile,
    update_user_profile,
    clear_user_profile,
    log_meal,
    get_meals_today,
    get_meals_history,
    clear_meals_history,
    get_nutrition_summary,
]