"""
scripts/expand_usda_database.py

Expande a base de dados com MAIS alimentos da USDA.

Este script ADICIONA alimentos à base existente (não apaga os anteriores).

COMO USAR:
    python scripts/expand_usda_database.py

CATEGORIAS INCLUÍDAS:
    - Mais frutas e vegetais
    - Peixes e mariscos portugueses
    - Carnes variadas
    - Queijos e laticínios
    - Pães e cereais
    - Comidas portuguesas típicas
    - Bebidas
    - Snacks e sobremesas
    - Fast food
    - E muito mais!
"""

from __future__ import annotations

import os
import sys
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURAÇÃO
# ============================================================

USDA_API_KEY = os.getenv("USDA_API_KEY", "")
USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "app" / "data" / "foods.db"

# Nutrientes
NUTRIENT_IDS = {
    1008: "kcal",
    1003: "protein",
    1005: "carbs",
    1004: "fat",
    1079: "fiber",
    2000: "sugar",
    1093: "sodium",
}

# ============================================================
# ALIMENTOS EXPANDIDOS - MUITO MAIS!
# ============================================================

EXPANDED_FOODS = {
    # ========== MAIS FRUTAS ==========
    "Fruits Extra": [
        "grapefruit raw",
        "tangerine raw",
        "clementine raw",
        "lime raw",
        "pomegranate raw",
        "passion fruit raw",
        "guava raw",
        "lychee raw",
        "dragon fruit",
        "persimmon raw",
        "fig raw",
        "date dried",
        "raisins",
        "prunes dried",
        "cranberries dried",
        "apple dried",
        "banana dried",
        "coconut raw",
        "coconut dried",
        "plantain raw",
        "plantain cooked",
        "jackfruit raw",
        "starfruit raw",
        "mulberries raw",
        "gooseberries raw",
        "blackberries raw",
        "acai",
        "goji berries",
    ],
    
    # ========== MAIS VEGETAIS ==========
    "Vegetables Extra": [
        "beet raw",
        "beet cooked",
        "radish raw",
        "turnip raw",
        "parsnip raw",
        "rutabaga raw",
        "leek raw",
        "shallot raw",
        "scallion raw",
        "chives raw",
        "fennel raw",
        "bok choy raw",
        "swiss chard raw",
        "collard greens",
        "mustard greens",
        "arugula raw",
        "watercress raw",
        "endive raw",
        "radicchio raw",
        "okra raw",
        "artichoke hearts",
        "hearts of palm",
        "bamboo shoots",
        "water chestnuts",
        "jicama raw",
        "kohlrabi raw",
        "celeriac raw",
        "daikon radish",
        "seaweed dried",
        "nori seaweed",
        "kelp",
        "spirulina",
        "sauerkraut",
        "kimchi",
        "pickles",
        "olives green",
        "olives black",
        "sun dried tomatoes",
        "roasted red peppers",
        "jalapeno pepper",
        "habanero pepper",
        "poblano pepper",
        "serrano pepper",
    ],
    
    # ========== PEIXES E MARISCOS (Muito importante para PT!) ==========
    "Seafood": [
        "bacalhau cod dried salted",
        "sea bass cooked",
        "sea bream",
        "haddock cooked",
        "halibut cooked",
        "sole fish cooked",
        "flounder cooked",
        "perch cooked",
        "catfish cooked",
        "swordfish cooked",
        "mahi mahi cooked",
        "grouper cooked",
        "snapper cooked",
        "anchovy canned",
        "herring cooked",
        "herring pickled",
        "smoked salmon",
        "caviar",
        "fish roe",
        "crab cooked",
        "crab meat canned",
        "lobster cooked",
        "crawfish cooked",
        "mussels cooked",
        "clams cooked",
        "oysters raw",
        "oysters cooked",
        "scallops cooked",
        "squid cooked",
        "calamari fried",
        "octopus cooked",
        "cuttlefish cooked",
        "sea urchin",
        "fish sticks frozen",
        "fish fillet breaded",
        "surimi crab",
        "tuna steak cooked",
        "salmon smoked",
        "eel cooked",
        "monkfish cooked",
    ],
    
    # ========== MAIS CARNES ==========
    "Meats Extra": [
        "beef ribeye cooked",
        "beef tenderloin cooked",
        "beef sirloin cooked",
        "beef brisket cooked",
        "beef liver cooked",
        "beef tongue cooked",
        "beef heart cooked",
        "veal cooked",
        "lamb leg cooked",
        "lamb shoulder cooked",
        "lamb liver cooked",
        "pork belly cooked",
        "pork ribs cooked",
        "pork shoulder cooked",
        "pork liver cooked",
        "pork sausage italian",
        "chorizo",
        "salami",
        "pepperoni",
        "prosciutto",
        "mortadella",
        "bologna",
        "pastrami",
        "corned beef",
        "hot dog",
        "bratwurst",
        "kielbasa",
        "blood sausage",
        "liver pate",
        "chicken liver cooked",
        "chicken gizzard cooked",
        "chicken heart cooked",
        "turkey ground cooked",
        "turkey leg cooked",
        "duck breast cooked",
        "duck liver",
        "goose cooked",
        "quail cooked",
        "rabbit cooked",
        "venison cooked",
        "bison cooked",
        "wild boar",
        "goat meat cooked",
    ],
    
    # ========== MAIS LATICÍNIOS E QUEIJOS ==========
    "Dairy Extra": [
        "cheese brie",
        "cheese camembert",
        "cheese gouda",
        "cheese gruyere",
        "cheese provolone",
        "cheese ricotta",
        "cheese mascarpone",
        "cheese blue",
        "cheese gorgonzola",
        "cheese roquefort",
        "cheese goat",
        "cheese manchego",
        "cheese pecorino",
        "cheese asiago",
        "cheese havarti",
        "cheese muenster",
        "cheese colby",
        "cheese monterey jack",
        "cheese pepper jack",
        "cheese american",
        "cheese string",
        "cheese spread",
        "cream cheese whipped",
        "neufchatel cheese",
        "quark cheese",
        "kefir",
        "buttermilk",
        "evaporated milk",
        "condensed milk sweetened",
        "powdered milk",
        "whipped cream",
        "half and half",
        "coffee creamer",
        "yogurt fruit",
        "yogurt vanilla",
        "frozen yogurt",
        "cottage cheese low fat",
        "ricotta cheese part skim",
        "cheese sauce",
    ],
    
    # ========== MAIS GRÃOS E PÃES ==========
    "Grains Extra": [
        "wild rice cooked",
        "jasmine rice cooked",
        "basmati rice cooked",
        "arborio rice cooked",
        "sticky rice cooked",
        "rice noodles cooked",
        "egg noodles cooked",
        "ramen noodles",
        "udon noodles",
        "soba noodles",
        "rice paper",
        "bread rye",
        "bread sourdough",
        "bread pita",
        "bread naan",
        "bread ciabatta",
        "bread focaccia",
        "bread baguette",
        "bread pumpernickel",
        "bread brioche",
        "bread challah",
        "croissant",
        "english muffin",
        "hamburger bun",
        "hot dog bun",
        "dinner roll",
        "breadsticks",
        "croutons",
        "stuffing bread",
        "cornbread",
        "biscuit",
        "scone",
        "muffin blueberry",
        "muffin bran",
        "pancake",
        "waffle",
        "french toast",
        "crepe",
        "puff pastry",
        "phyllo dough",
        "pie crust",
        "pizza dough",
        "gnocchi",
        "polenta",
        "grits",
        "cream of wheat",
        "muesli",
        "bran flakes",
        "wheat germ",
        "bulgur wheat",
        "farro cooked",
        "spelt cooked",
        "millet cooked",
        "amaranth cooked",
        "buckwheat cooked",
        "teff cooked",
    ],
    
    # ========== MAIS LEGUMINOSAS ==========
    "Legumes Extra": [
        "navy beans cooked",
        "cannellini beans cooked",
        "fava beans cooked",
        "mung beans cooked",
        "adzuki beans cooked",
        "split peas cooked",
        "black eyed peas cooked",
        "pigeon peas cooked",
        "lupini beans",
        "bean sprouts",
        "soy protein",
        "textured vegetable protein",
        "seitan",
        "miso paste",
        "natto",
        "soy sauce",
        "tamari",
        "bean dip",
        "refried beans",
        "baked beans canned",
        "chili beans canned",
    ],
    
    # ========== MAIS FRUTOS SECOS E SEMENTES ==========
    "Nuts Seeds Extra": [
        "pine nuts",
        "chestnuts roasted",
        "coconut flakes",
        "coconut cream",
        "coconut milk canned",
        "tahini",
        "sesame seeds",
        "poppy seeds",
        "hemp seeds",
        "flaxseed meal",
        "psyllium husk",
        "mixed nuts",
        "trail mix",
        "nut butter mixed",
        "sunflower butter",
        "soy nuts",
    ],
    
    # ========== CONDIMENTOS E MOLHOS ==========
    "Condiments Sauces": [
        "ketchup",
        "mustard yellow",
        "mustard dijon",
        "mayonnaise",
        "mayonnaise light",
        "relish pickle",
        "horseradish",
        "wasabi",
        "hot sauce",
        "sriracha",
        "barbecue sauce",
        "teriyaki sauce",
        "hoisin sauce",
        "oyster sauce",
        "fish sauce",
        "worcestershire sauce",
        "steak sauce",
        "salsa",
        "guacamole",
        "pico de gallo",
        "chimichurri",
        "pesto sauce",
        "marinara sauce",
        "alfredo sauce",
        "tomato sauce canned",
        "tomato paste",
        "pizza sauce",
        "enchilada sauce",
        "curry paste",
        "chutney",
        "jam strawberry",
        "jelly grape",
        "marmalade orange",
        "apple butter",
        "nutella",
        "caramel sauce",
        "chocolate syrup",
        "whipped topping",
    ],
    
    # ========== TEMPEROS E ESPECIARIAS ==========
    "Spices Herbs": [
        "salt table",
        "black pepper",
        "garlic powder",
        "onion powder",
        "paprika",
        "cayenne pepper",
        "chili powder",
        "cumin ground",
        "coriander ground",
        "turmeric ground",
        "ginger ground",
        "cinnamon ground",
        "nutmeg ground",
        "cloves ground",
        "allspice ground",
        "cardamom ground",
        "curry powder",
        "garam masala",
        "oregano dried",
        "basil dried",
        "thyme dried",
        "rosemary dried",
        "sage dried",
        "parsley dried",
        "dill dried",
        "bay leaves",
        "vanilla extract",
        "cocoa powder",
        "baking powder",
        "baking soda",
        "yeast active dry",
        "cornstarch",
        "gelatin",
    ],
    
    # ========== BEBIDAS EXTRA ==========
    "Beverages Extra": [
        "espresso",
        "latte",
        "cappuccino",
        "mocha",
        "iced coffee",
        "cold brew coffee",
        "green tea",
        "black tea",
        "herbal tea",
        "chamomile tea",
        "matcha",
        "hot chocolate",
        "chocolate milk",
        "strawberry milk",
        "milkshake vanilla",
        "smoothie fruit",
        "protein shake",
        "energy drink",
        "sports drink",
        "lemonade",
        "iced tea sweetened",
        "iced tea unsweetened",
        "cranberry juice",
        "pineapple juice",
        "grapefruit juice",
        "carrot juice",
        "vegetable juice",
        "coconut milk beverage",
        "oat milk",
        "rice milk",
        "cashew milk",
        "beer light",
        "beer dark",
        "wine white",
        "wine rose",
        "champagne",
        "vodka",
        "whiskey",
        "rum",
        "gin",
        "tequila",
        "brandy",
        "liqueur",
        "margarita",
        "pina colada",
        "sangria",
        "cider apple",
        "kombucha",
    ],
    
    # ========== SNACKS ==========
    "Snacks": [
        "tortilla chips",
        "corn chips",
        "cheese puffs",
        "pretzels soft",
        "popcorn butter",
        "popcorn caramel",
        "rice cakes",
        "rice crackers",
        "animal crackers",
        "graham crackers",
        "cheese crackers",
        "pita chips",
        "veggie chips",
        "banana chips",
        "apple chips",
        "beef jerky",
        "turkey jerky",
        "pork rinds",
        "mixed snacks",
        "granola bar",
        "protein bar",
        "energy bar",
        "fruit snacks",
        "fruit leather",
        "dried mango",
        "dried pineapple",
        "dried apricots",
        "dried figs",
        "mixed dried fruit",
        "chocolate chips",
        "candy bar",
        "gummy bears",
        "licorice",
        "hard candy",
        "marshmallows",
        "caramel candy",
        "fudge",
        "peanut brittle",
    ],
    
    # ========== SOBREMESAS E DOCES ==========
    "Desserts Sweets": [
        "chocolate dark",
        "chocolate milk bar",
        "chocolate white",
        "brownie",
        "cookie chocolate chip",
        "cookie oatmeal",
        "cookie sugar",
        "cookie peanut butter",
        "cookie sandwich",
        "cake chocolate",
        "cake vanilla",
        "cake carrot",
        "cake cheesecake",
        "cake pound",
        "cake angel food",
        "cake red velvet",
        "cupcake",
        "donut glazed",
        "donut chocolate",
        "donut jelly",
        "cinnamon roll",
        "danish pastry",
        "eclair",
        "cream puff",
        "tiramisu",
        "panna cotta",
        "mousse chocolate",
        "pudding vanilla",
        "pudding chocolate",
        "pudding rice",
        "custard",
        "flan",
        "creme brulee",
        "pie apple",
        "pie pumpkin",
        "pie pecan",
        "pie cherry",
        "pie key lime",
        "pie banana cream",
        "pie coconut cream",
        "cobbler peach",
        "crisp apple",
        "strudel apple",
        "baklava",
        "cannoli",
        "churros",
        "crepe nutella",
        "ice cream chocolate",
        "ice cream strawberry",
        "gelato",
        "sorbet",
        "sherbet",
        "frozen custard",
        "popsicle",
        "ice cream sandwich",
        "ice cream cone",
        "sundae",
        "banana split",
    ],
    
    # ========== FAST FOOD E COMIDA PREPARADA ==========
    "Fast Food Prepared": [
        "hamburger",
        "cheeseburger",
        "bacon cheeseburger",
        "veggie burger",
        "chicken sandwich",
        "fish sandwich",
        "hot dog plain",
        "corn dog",
        "french fries",
        "onion rings",
        "mozzarella sticks",
        "chicken nuggets",
        "chicken tenders",
        "chicken wings fried",
        "buffalo wings",
        "pizza cheese",
        "pizza pepperoni",
        "pizza supreme",
        "pizza margherita",
        "calzone",
        "stromboli",
        "burrito bean",
        "burrito chicken",
        "burrito beef",
        "taco beef",
        "taco chicken",
        "taco fish",
        "quesadilla cheese",
        "quesadilla chicken",
        "nachos cheese",
        "nachos supreme",
        "enchilada cheese",
        "enchilada chicken",
        "tamale",
        "chimichanga",
        "tostada",
        "empanada beef",
        "empanada chicken",
        "spring roll",
        "egg roll",
        "dumpling pork",
        "dumpling vegetable",
        "gyoza",
        "wonton",
        "sushi roll california",
        "sushi roll spicy tuna",
        "sashimi salmon",
        "tempura shrimp",
        "tempura vegetable",
        "pad thai",
        "fried rice",
        "lo mein",
        "chow mein",
        "general tso chicken",
        "orange chicken",
        "sweet and sour chicken",
        "kung pao chicken",
        "beef and broccoli",
        "mongolian beef",
        "curry chicken",
        "tikka masala",
        "butter chicken",
        "samosa",
        "pakora",
        "falafel",
        "gyro",
        "shawarma",
        "kebab",
        "souvlaki",
        "spanakopita",
        "moussaka",
        "lasagna",
        "manicotti",
        "ravioli cheese",
        "tortellini cheese",
        "gnocchi sauce",
        "risotto",
        "paella",
        "jambalaya",
        "gumbo",
        "po boy",
        "reuben sandwich",
        "club sandwich",
        "blt sandwich",
        "grilled cheese",
        "tuna salad sandwich",
        "chicken salad sandwich",
        "egg salad sandwich",
        "submarine sandwich",
        "wrap chicken",
        "panini",
    ],
    
    # ========== SOPAS E CALDOS ==========
    "Soups Broths": [
        "chicken broth",
        "beef broth",
        "vegetable broth",
        "bone broth",
        "chicken noodle soup",
        "tomato soup",
        "minestrone soup",
        "vegetable soup",
        "lentil soup",
        "split pea soup",
        "black bean soup",
        "chili con carne",
        "clam chowder",
        "corn chowder",
        "potato soup",
        "broccoli cheese soup",
        "french onion soup",
        "mushroom soup cream",
        "chicken cream soup",
        "tortilla soup",
        "egg drop soup",
        "hot and sour soup",
        "miso soup",
        "pho",
        "ramen soup",
        "wonton soup",
        "gazpacho",
        "borscht",
    ],
    
    # ========== SALADAS E MOLHOS PARA SALADA ==========
    "Salads Dressings": [
        "caesar salad",
        "greek salad",
        "garden salad",
        "cobb salad",
        "chef salad",
        "spinach salad",
        "kale salad",
        "coleslaw",
        "potato salad",
        "macaroni salad",
        "pasta salad",
        "chicken salad",
        "tuna salad",
        "egg salad",
        "fruit salad",
        "waldorf salad",
        "caprese salad",
        "quinoa salad",
        "tabbouleh",
        "ranch dressing",
        "caesar dressing",
        "italian dressing",
        "balsamic vinaigrette",
        "blue cheese dressing",
        "thousand island dressing",
        "honey mustard dressing",
        "french dressing",
        "greek dressing",
        "oil and vinegar",
    ],
    
    # ========== PEQUENO ALMOÇO ==========
    "Breakfast Items": [
        "bacon strips",
        "sausage patty",
        "sausage link",
        "ham slice",
        "canadian bacon",
        "eggs scrambled",
        "eggs fried",
        "eggs poached",
        "eggs benedict",
        "omelet cheese",
        "omelet western",
        "frittata",
        "quiche lorraine",
        "hash browns",
        "home fries",
        "breakfast burrito",
        "breakfast sandwich",
        "eggs mcmuffin style",
        "french toast sticks",
        "cinnamon toast",
        "avocado toast",
        "bagel cream cheese",
        "yogurt parfait",
        "acai bowl",
        "overnight oats",
        "smoothie bowl",
    ],
    
    # ========== ALIMENTOS PORTUGUESES ==========
    "Portuguese Foods": [
        "sardines grilled",
        "codfish cakes",
        "salt cod",
        "octopus grilled",
        "clams portuguese",
        "pork alentejo",
        "chourico sausage",
        "linguica sausage",
        "presunto ham",
        "queijo serra",
        "queijo azeitao",
        "pastel nata",
        "arroz doce rice pudding",
        "pao de lo sponge cake",
        "bola de berlim",
        "travesseiro pastry",
        "queijada",
        "sweet bread",
        "broa corn bread",
        "caldo verde",
        "feijoada",
        "francesinha",
        "bifana",
        "prego steak sandwich",
        "bacalhau bras",
        "bacalhau gomes sa",
        "arroz de pato",
        "arroz de marisco",
        "acorda",
        "migas",
        "alheira sausage",
        "morcela blood sausage",
        "farinheira sausage",
        "leitao roast suckling pig",
        "cabrito roast goat",
        "polvo lagareiro",
        "amêijoas bulhao pato",
        "percebes barnacles",
        "sapateira crab",
        "santola spider crab",
        "carabineiros prawns",
        "gambas prawns",
        "choco cuttlefish",
        "lulas squid",
        "carapaus horse mackerel",
        "dourada sea bream",
        "robalo sea bass",
        "peixe espada black scabbard",
        "tamboril monkfish",
        "caldeirada fish stew",
        "cataplana",
    ],
}

# Traduções PT adicionais
EXTRA_PT_TRANSLATIONS = {
    "codfish": "bacalhau",
    "sardines": "sardinhas", 
    "octopus": "polvo",
    "squid": "lulas",
    "cuttlefish": "choco",
    "clams": "amêijoas",
    "mussels": "mexilhões",
    "crab": "caranguejo",
    "lobster": "lagosta",
    "prawns": "gambas",
    "shrimp": "camarão",
    "sea bass": "robalo",
    "sea bream": "dourada",
    "monkfish": "tamboril",
    "haddock": "arinca",
    "sole": "linguado",
    "swordfish": "espadarte",
    "anchovy": "anchova",
    "herring": "arenque",
    "mackerel": "cavala",
    "trout": "truta",
    "chorizo": "chouriço",
    "ham": "presunto",
    "sausage": "salsicha",
    "veal": "vitela",
    "rabbit": "coelho",
    "goat": "cabrito",
    "duck": "pato",
    "quail": "codorniz",
    "liver": "fígado",
    "rice": "arroz",
    "bread": "pão",
    "cheese": "queijo",
    "butter": "manteiga",
    "cream": "natas",
    "milk": "leite",
    "egg": "ovo",
    "soup": "sopa",
    "salad": "salada",
    "cake": "bolo",
    "cookie": "bolacha",
    "pie": "tarte",
    "pudding": "pudim",
    "ice cream": "gelado",
}


# ============================================================
# FUNÇÕES
# ============================================================

def search_usda(query: str, page_size: int = 3) -> List[Dict]:
    """Pesquisa na USDA API."""
    url = f"{USDA_BASE_URL}/foods/search"
    params = {
        "api_key": USDA_API_KEY,
        "query": query,
        "pageSize": page_size,
        "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"],
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json().get("foods", [])
    except Exception as e:
        return []


def extract_nutrients(food: Dict) -> Dict[str, float]:
    """Extrai nutrientes."""
    nutrients = {name: 0.0 for name in NUTRIENT_IDS.values()}
    
    for fn in food.get("foodNutrients", []):
        nutrient_id = fn.get("nutrientId")
        value = fn.get("value", 0) or 0
        if nutrient_id in NUTRIENT_IDS:
            nutrients[NUTRIENT_IDS[nutrient_id]] = float(value)
    
    return nutrients


def get_pt_translation(food_name: str) -> Optional[str]:
    """Tradução para português."""
    food_lower = food_name.lower()
    for en, pt in EXTRA_PT_TRANSLATIONS.items():
        if en in food_lower:
            return pt
    return None


def insert_food(cursor, food_data: Dict) -> bool:
    """Insere alimento na BD."""
    try:
        name_search = food_data["name_en"].lower()
        cursor.execute("""
            INSERT OR IGNORE INTO foods 
            (fdc_id, name_en, name_pt, name_search, kcal_100g, protein_100g, 
             carbs_100g, fat_100g, fiber_100g, sugar_100g, sodium_mg_100g, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            food_data.get("fdc_id"),
            food_data["name_en"],
            food_data.get("name_pt"),
            name_search,
            food_data["kcal_100g"],
            food_data["protein_100g"],
            food_data["carbs_100g"],
            food_data["fat_100g"],
            food_data.get("fiber_100g", 0),
            food_data.get("sugar_100g", 0),
            food_data.get("sodium_mg_100g", 0),
            food_data.get("category"),
        ))
        return cursor.rowcount > 0
    except:
        return False


def expand_database():
    """Expande a base de dados."""
    
    print("\n" + "="*60)
    print("🍎 USDA DATABASE EXPANSION")
    print("="*60)
    
    if not USDA_API_KEY:
        print("\n❌ USDA_API_KEY não configurada no .env!")
        sys.exit(1)
    
    if not DB_PATH.exists():
        print(f"\n❌ Base de dados não encontrada: {DB_PATH}")
        print("   Corre primeiro: python scripts/build_usda_database.py")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Contar existentes
    cursor.execute("SELECT COUNT(*) FROM foods")
    initial_count = cursor.fetchone()[0]
    print(f"\n📊 Alimentos existentes: {initial_count}")
    
    # Contar total de queries
    total_queries = sum(len(foods) for foods in EXPANDED_FOODS.values())
    current = 0
    added = 0
    
    print(f"🔍 Buscando mais {total_queries} alimentos...\n")
    
    for category, food_queries in EXPANDED_FOODS.items():
        print(f"\n📂 {category}")
        print("-" * 40)
        
        for query in food_queries:
            current += 1
            print(f"   [{current}/{total_queries}] {query}...", end=" ", flush=True)
            
            results = search_usda(query, page_size=2)
            
            if not results:
                print("❌")
                time.sleep(0.2)
                continue
            
            for food in results:
                description = food.get("description", "").strip()
                nutrients = extract_nutrients(food)
                
                if nutrients["kcal"] <= 0:
                    continue
                
                food_data = {
                    "fdc_id": food.get("fdcId"),
                    "name_en": description,
                    "name_pt": get_pt_translation(description),
                    "kcal_100g": round(nutrients["kcal"], 1),
                    "protein_100g": round(nutrients["protein"], 2),
                    "carbs_100g": round(nutrients["carbs"], 2),
                    "fat_100g": round(nutrients["fat"], 2),
                    "fiber_100g": round(nutrients.get("fiber", 0), 2),
                    "sugar_100g": round(nutrients.get("sugar", 0), 2),
                    "sodium_mg_100g": round(nutrients.get("sodium", 0), 1),
                    "category": category,
                }
                
                if insert_food(cursor, food_data):
                    added += 1
                    print(f"✅ {nutrients['kcal']:.0f} kcal")
                    break
            else:
                print("⚠️")
            
            time.sleep(0.25)  # Rate limiting
        
        conn.commit()
    
    # Estatísticas finais
    cursor.execute("SELECT COUNT(*) FROM foods")
    final_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT category, COUNT(*) FROM foods GROUP BY category ORDER BY category")
    by_category = cursor.fetchall()
    
    conn.close()
    
    print("\n" + "="*60)
    print("✅ EXPANSÃO CONCLUÍDA!")
    print("="*60)
    
    print(f"\n📊 Estatísticas:")
    print(f"   • Antes: {initial_count} alimentos")
    print(f"   • Adicionados: {added}")
    print(f"   • Total agora: {final_count} alimentos")
    
    print(f"\n📂 Por categoria:")
    for cat, count in by_category:
        print(f"   • {cat}: {count}")


if __name__ == "__main__":
    expand_database()
