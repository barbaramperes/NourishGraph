"""
Import common foods from USDA FoodData Central API into PostgreSQL.
This creates a local cache of ~500 common foods for faster lookups.
"""

import os
import requests
import psycopg2
from dotenv import load_dotenv
import time

load_dotenv()

USDA_API_KEY = os.getenv("USDA_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://nutriai_user:nutriai_password@localhost:5432/nutriai")

# Common food search terms to populate the database
COMMON_FOODS = [
    # Fruits
    "apple", "banana", "orange", "strawberry", "blueberry", "grape", "mango",
    "pineapple", "watermelon", "peach", "pear", "cherry", "kiwi", "lemon",
    "avocado", "raspberry", "blackberry", "cantaloupe", "papaya", "pomegranate",
    
    # Vegetables
    "broccoli", "spinach", "carrot", "tomato", "potato", "onion", "garlic",
    "lettuce", "cucumber", "bell pepper", "zucchini", "cauliflower", "kale",
    "celery", "asparagus", "green beans", "peas", "corn", "sweet potato",
    "mushroom", "cabbage", "brussels sprouts", "eggplant", "beetroot",
    
    # Proteins
    "chicken breast", "beef steak", "salmon", "tuna", "shrimp", "pork chop",
    "turkey breast", "lamb", "cod", "tilapia", "sardines", "mackerel",
    "egg", "tofu", "tempeh", "chickpeas", "lentils", "black beans",
    "kidney beans", "edamame",
    
    # Dairy
    "milk", "cheese", "yogurt", "butter", "cream", "cottage cheese",
    "mozzarella", "cheddar cheese", "parmesan", "greek yogurt", "kefir",
    
    # Grains
    "rice", "bread", "pasta", "oatmeal", "quinoa", "barley", "couscous",
    "whole wheat bread", "brown rice", "white rice", "bagel", "tortilla",
    "cereal", "granola", "crackers",
    
    # Nuts & Seeds
    "almonds", "walnuts", "peanuts", "cashews", "pistachios", "pecans",
    "sunflower seeds", "chia seeds", "flax seeds", "pumpkin seeds",
    "peanut butter", "almond butter",
    
    # Oils & Fats
    "olive oil", "coconut oil", "vegetable oil", "canola oil",
    
    # Beverages
    "coffee", "green tea", "orange juice", "apple juice", "coconut water",
    
    # Common dishes
    "pizza", "hamburger", "sandwich", "salad", "soup", "pasta with sauce",
    "fried rice", "burrito", "tacos", "sushi",
    
    # Snacks
    "chips", "popcorn", "chocolate", "ice cream", "cookies", "cake",
    
    # Breakfast
    "pancakes", "waffles", "bacon", "sausage", "hash browns",
    
    # Condiments
    "mayonnaise", "ketchup", "mustard", "honey", "maple syrup", "soy sauce"
]


def get_usda_food(query: str) -> list:
    """Search USDA API for a food item."""
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "api_key": USDA_API_KEY,
        "query": query,
        "pageSize": 5,  # Get top 5 results per query
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("foods", [])
    except Exception as e:
        print(f"  ❌ Error fetching '{query}': {e}")
        return []


def extract_nutrient(nutrients: list, nutrient_id: int) -> float:
    """Extract nutrient value by ID."""
    for n in nutrients:
        if n.get("nutrientId") == nutrient_id:
            return round(n.get("value", 0), 2)
    return 0.0


def parse_food(food: dict) -> dict:
    """Parse USDA food into our database format."""
    nutrients = food.get("foodNutrients", [])
    
    return {
        "fdc_id": food.get("fdcId"),
        "name_en": food.get("description", "")[:255],
        "kcal_100g": extract_nutrient(nutrients, 1008),      # Energy (kcal)
        "protein_100g": extract_nutrient(nutrients, 1003),   # Protein
        "carbs_100g": extract_nutrient(nutrients, 1005),     # Carbohydrates
        "fat_100g": extract_nutrient(nutrients, 1004),       # Total fat
        "fiber_100g": extract_nutrient(nutrients, 1079),     # Fiber
        "sugar_100g": extract_nutrient(nutrients, 2000),     # Total sugars
        "sodium_mg_100g": extract_nutrient(nutrients, 1093), # Sodium
        "category": food.get("foodCategory", "")[:100] if food.get("foodCategory") else None
    }


def import_foods():
    """Import common foods from USDA to PostgreSQL."""
    print("=" * 60)
    print("USDA FOOD IMPORT")
    print("=" * 60)
    
    if not USDA_API_KEY:
        print("❌ USDA_API_KEY not set in .env")
        return
    
    # Connect to PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Clear existing foods (except the 10 manual ones if you want to keep them)
    cur.execute("DELETE FROM foods WHERE fdc_id IS NOT NULL")
    conn.commit()
    print(f"🗑️  Cleared existing USDA foods")
    
    imported = 0
    skipped = 0
    errors = 0
    
    print(f"\n📥 Importing {len(COMMON_FOODS)} food categories...\n")
    
    for i, query in enumerate(COMMON_FOODS):
        print(f"[{i+1}/{len(COMMON_FOODS)}] Searching: {query}...", end=" ")
        
        foods = get_usda_food(query)
        
        if not foods:
            print("No results")
            skipped += 1
            continue
        
        # Import first result (most relevant)
        food = foods[0]
        parsed = parse_food(food)
        
        # Skip if no fdc_id or already exists
        if not parsed["fdc_id"]:
            print("No FDC ID")
            skipped += 1
            continue
        
        try:
            cur.execute("""
                INSERT INTO foods (fdc_id, name_en, kcal_100g, protein_100g, carbs_100g, 
                                   fat_100g, fiber_100g, sugar_100g, sodium_mg_100g, category)
                VALUES (%(fdc_id)s, %(name_en)s, %(kcal_100g)s, %(protein_100g)s, %(carbs_100g)s,
                        %(fat_100g)s, %(fiber_100g)s, %(sugar_100g)s, %(sodium_mg_100g)s, %(category)s)
                ON CONFLICT (fdc_id) DO NOTHING
            """, parsed)
            conn.commit()
            imported += 1
            print(f"✅ {parsed['name_en'][:40]} ({parsed['kcal_100g']} kcal)")
        except Exception as e:
            print(f"❌ {e}")
            errors += 1
            conn.rollback()
        
        # Rate limit: USDA allows 1000 requests/hour
        time.sleep(0.5)
    
    # Final count
    cur.execute("SELECT COUNT(*) FROM foods")
    total = cur.fetchone()[0]
    
    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"✅ Imported: {imported}")
    print(f"⏭️  Skipped:  {skipped}")
    print(f"❌ Errors:   {errors}")
    print(f"📊 Total foods in database: {total}")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    import_foods()
