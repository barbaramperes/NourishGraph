"""
scripts/build_usda_database.py

Constrói base de dados SQLite com dados REAIS da USDA FoodData Central.

SEM FALLBACKS - só dados oficiais da USDA!

COMO USAR:
    1. Configura .env com: USDA_API_KEY=your_key
    2. Corre: python scripts/build_usda_database.py
    
OUTPUT:
    - app/data/foods.db (SQLite com dados USDA)

CITAÇÃO PARA TESE:
    U.S. Department of Agriculture, Agricultural Research Service.
    FoodData Central, 2024. fdc.nal.usda.gov
"""

from __future__ import annotations

import os
import sys
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import requests
from dotenv import load_dotenv

# Carregar .env
load_dotenv()

# ============================================================
# CONFIGURAÇÃO
# ============================================================

USDA_API_KEY = os.getenv("USDA_API_KEY", "")
USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
DB_PATH = DATA_DIR / "foods.db"

# Nutrientes que queremos (IDs da USDA)
NUTRIENT_IDS = {
    1008: "kcal",       # Energy (kcal)
    1003: "protein",    # Protein (g)
    1005: "carbs",      # Carbohydrate (g)
    1004: "fat",        # Total fat (g)
    1079: "fiber",      # Fiber (g)
    2000: "sugar",      # Sugars (g)
    1093: "sodium",     # Sodium (mg)
}

# Alimentos a pesquisar por categoria
FOODS_TO_FETCH = {
    "Fruits": [
        "apple raw",
        "banana raw", 
        "orange raw",
        "strawberries raw",
        "grapes raw",
        "watermelon raw",
        "mango raw",
        "pineapple raw",
        "peach raw",
        "pear raw",
        "cherries raw",
        "blueberries raw",
        "raspberries raw",
        "kiwi raw",
        "avocado raw",
        "lemon raw",
        "papaya raw",
        "melon cantaloupe",
        "plum raw",
        "apricot raw",
    ],
    "Vegetables": [
        "broccoli raw",
        "spinach raw",
        "carrot raw",
        "tomato raw",
        "potato boiled",
        "sweet potato baked",
        "onion raw",
        "garlic raw",
        "lettuce raw",
        "cucumber raw",
        "bell pepper raw",
        "cabbage raw",
        "cauliflower raw",
        "zucchini raw",
        "mushrooms raw",
        "corn cooked",
        "peas green cooked",
        "green beans cooked",
        "asparagus cooked",
        "celery raw",
        "eggplant raw",
        "kale raw",
        "brussels sprouts",
        "artichoke",
    ],
    "Proteins": [
        "chicken breast cooked",
        "chicken thigh cooked",
        "chicken wing cooked",
        "beef ground cooked",
        "beef steak cooked",
        "pork loin cooked",
        "pork chop cooked",
        "lamb cooked",
        "turkey breast cooked",
        "duck cooked",
        "salmon cooked",
        "tuna canned",
        "cod cooked",
        "tilapia cooked",
        "shrimp cooked",
        "sardines canned",
        "mackerel cooked",
        "trout cooked",
        "egg whole cooked",
        "egg white cooked",
        "bacon cooked",
        "ham cooked",
        "sausage cooked",
    ],
    "Dairy": [
        "milk whole",
        "milk skim",
        "milk 2 percent",
        "yogurt plain",
        "yogurt greek plain",
        "cheese cheddar",
        "cheese mozzarella",
        "cheese parmesan",
        "cheese cottage",
        "cheese cream",
        "cheese swiss",
        "cheese feta",
        "butter salted",
        "butter unsalted",
        "cream heavy",
        "sour cream",
        "ice cream vanilla",
    ],
    "Grains": [
        "rice white cooked",
        "rice brown cooked",
        "pasta cooked",
        "spaghetti cooked",
        "bread white",
        "bread whole wheat",
        "oats dry",
        "oatmeal cooked",
        "quinoa cooked",
        "couscous cooked",
        "barley cooked",
        "cornmeal",
        "flour all purpose",
        "flour whole wheat",
        "tortilla corn",
        "tortilla flour",
        "bagel plain",
        "crackers",
        "cereal corn flakes",
        "granola",
    ],
    "Legumes": [
        "lentils cooked",
        "chickpeas cooked",
        "black beans cooked",
        "kidney beans cooked",
        "pinto beans cooked",
        "white beans cooked",
        "lima beans cooked",
        "soybeans cooked",
        "tofu firm",
        "tofu soft",
        "tempeh",
        "hummus",
        "edamame",
    ],
    "Nuts and Seeds": [
        "almonds",
        "walnuts",
        "peanuts",
        "cashews",
        "pistachios",
        "pecans",
        "hazelnuts",
        "macadamia nuts",
        "brazil nuts",
        "sunflower seeds",
        "pumpkin seeds",
        "chia seeds",
        "flax seeds",
        "peanut butter",
        "almond butter",
    ],
    "Oils and Fats": [
        "olive oil",
        "coconut oil",
        "vegetable oil",
        "canola oil",
        "sunflower oil",
        "sesame oil",
        "avocado oil",
        "lard",
        "margarine",
    ],
    "Sweeteners": [
        "sugar white granulated",
        "sugar brown",
        "honey",
        "maple syrup",
        "molasses",
    ],
    "Beverages": [
        "orange juice",
        "apple juice",
        "grape juice",
        "tomato juice",
        "coffee brewed",
        "tea brewed",
        "coconut water",
        "almond milk",
        "soy milk",
    ],
}

# Traduções PT para os alimentos mais comuns
PT_TRANSLATIONS = {
    "apple": "maçã",
    "banana": "banana",
    "orange": "laranja",
    "strawberries": "morangos",
    "grapes": "uvas",
    "watermelon": "melancia",
    "mango": "manga",
    "pineapple": "ananás",
    "peach": "pêssego",
    "pear": "pera",
    "cherries": "cerejas",
    "blueberries": "mirtilos",
    "raspberries": "framboesas",
    "kiwi": "kiwi",
    "avocado": "abacate",
    "lemon": "limão",
    "broccoli": "brócolos",
    "spinach": "espinafres",
    "carrot": "cenoura",
    "tomato": "tomate",
    "potato": "batata",
    "sweet potato": "batata-doce",
    "onion": "cebola",
    "garlic": "alho",
    "lettuce": "alface",
    "cucumber": "pepino",
    "pepper": "pimento",
    "cabbage": "couve",
    "cauliflower": "couve-flor",
    "zucchini": "courgette",
    "mushrooms": "cogumelos",
    "corn": "milho",
    "peas": "ervilhas",
    "beans": "feijão",
    "asparagus": "espargos",
    "celery": "aipo",
    "eggplant": "beringela",
    "kale": "couve",
    "chicken": "frango",
    "beef": "carne de vaca",
    "pork": "porco",
    "lamb": "borrego",
    "turkey": "peru",
    "duck": "pato",
    "salmon": "salmão",
    "tuna": "atum",
    "cod": "bacalhau",
    "shrimp": "camarão",
    "sardines": "sardinhas",
    "egg": "ovo",
    "bacon": "bacon",
    "ham": "fiambre",
    "sausage": "salsicha",
    "milk": "leite",
    "yogurt": "iogurte",
    "cheese": "queijo",
    "butter": "manteiga",
    "cream": "natas",
    "ice cream": "gelado",
    "rice": "arroz",
    "pasta": "massa",
    "bread": "pão",
    "oats": "aveia",
    "quinoa": "quinoa",
    "flour": "farinha",
    "lentils": "lentilhas",
    "chickpeas": "grão-de-bico",
    "tofu": "tofu",
    "almonds": "amêndoas",
    "walnuts": "nozes",
    "peanuts": "amendoins",
    "cashews": "cajus",
    "olive oil": "azeite",
    "coconut oil": "óleo de coco",
    "sugar": "açúcar",
    "honey": "mel",
    "coffee": "café",
    "tea": "chá",
}


# ============================================================
# USDA API FUNCTIONS
# ============================================================

def search_usda(query: str, page_size: int = 5) -> List[Dict]:
    """
    Pesquisa alimentos na USDA FoodData Central API.
    
    Args:
        query: Termo de pesquisa
        page_size: Número de resultados
    
    Returns:
        Lista de alimentos encontrados
    """
    url = f"{USDA_BASE_URL}/foods/search"
    
    params = {
        "api_key": USDA_API_KEY,
        "query": query,
        "pageSize": page_size,
        "dataType": ["Foundation", "SR Legacy"],  # Dados mais confiáveis
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("foods", [])
    except requests.exceptions.RequestException as e:
        print(f"      ❌ Erro API: {e}")
        return []


def extract_nutrients(food: Dict) -> Dict[str, float]:
    """
    Extrai nutrientes de um alimento da USDA.
    
    Args:
        food: Dados do alimento da API
    
    Returns:
        Dict com nutrientes
    """
    nutrients = {name: 0.0 for name in NUTRIENT_IDS.values()}
    
    for fn in food.get("foodNutrients", []):
        nutrient_id = fn.get("nutrientId")
        value = fn.get("value", 0) or 0
        
        if nutrient_id in NUTRIENT_IDS:
            nutrients[NUTRIENT_IDS[nutrient_id]] = float(value)
    
    return nutrients


def get_pt_translation(food_name: str) -> Optional[str]:
    """
    Tenta encontrar tradução portuguesa para o nome do alimento.
    """
    food_lower = food_name.lower()
    
    for en, pt in PT_TRANSLATIONS.items():
        if en in food_lower:
            return pt
    
    return None


def process_food(food: Dict, category: str) -> Optional[Dict[str, Any]]:
    """
    Processa um alimento da API para o formato da base de dados.
    
    Args:
        food: Dados brutos da API
        category: Categoria do alimento
    
    Returns:
        Dict formatado ou None se inválido
    """
    description = food.get("description", "").strip()
    fdc_id = food.get("fdcId")
    
    if not description:
        return None
    
    nutrients = extract_nutrients(food)
    
    # Ignorar alimentos sem calorias (dados incompletos)
    if nutrients["kcal"] <= 0:
        return None
    
    return {
        "fdc_id": fdc_id,
        "name_en": description,
        "name_pt": get_pt_translation(description),
        "kcal_100g": round(nutrients["kcal"], 1),
        "protein_100g": round(nutrients["protein"], 2),
        "carbs_100g": round(nutrients["carbs"], 2),
        "fat_100g": round(nutrients["fat"], 2),
        "fiber_100g": round(nutrients["fiber"], 2),
        "sugar_100g": round(nutrients["sugar"], 2),
        "sodium_mg_100g": round(nutrients["sodium"], 1),
        "category": category,
    }


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def create_database():
    """Cria a base de dados SQLite com schema."""
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Apagar base existente para começar do zero
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"   🗑️  Base anterior apagada")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabela de alimentos
    cursor.execute("""
        CREATE TABLE foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fdc_id INTEGER UNIQUE,
            name_en TEXT NOT NULL,
            name_pt TEXT,
            name_search TEXT NOT NULL,
            kcal_100g REAL NOT NULL,
            protein_100g REAL NOT NULL,
            carbs_100g REAL NOT NULL,
            fat_100g REAL NOT NULL,
            fiber_100g REAL DEFAULT 0,
            sugar_100g REAL DEFAULT 0,
            sodium_mg_100g REAL DEFAULT 0,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Índices para pesquisa rápida
    cursor.execute("CREATE INDEX idx_name_search ON foods(name_search)")
    cursor.execute("CREATE INDEX idx_name_en ON foods(name_en)")
    cursor.execute("CREATE INDEX idx_category ON foods(category)")
    cursor.execute("CREATE INDEX idx_fdc_id ON foods(fdc_id)")
    
    # Tabela de metadados
    cursor.execute("""
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    
    print(f"   ✅ Base de dados criada: {DB_PATH}")


def insert_food(food: Dict[str, Any]) -> bool:
    """Insere um alimento na base de dados."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        name_search = food["name_en"].lower()
        
        cursor.execute("""
            INSERT OR IGNORE INTO foods 
            (fdc_id, name_en, name_pt, name_search, kcal_100g, protein_100g, 
             carbs_100g, fat_100g, fiber_100g, sugar_100g, sodium_mg_100g, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            food.get("fdc_id"),
            food["name_en"],
            food.get("name_pt"),
            name_search,
            food["kcal_100g"],
            food["protein_100g"],
            food["carbs_100g"],
            food["fat_100g"],
            food.get("fiber_100g", 0),
            food.get("sugar_100g", 0),
            food.get("sodium_mg_100g", 0),
            food.get("category"),
        ))
        
        conn.commit()
        inserted = cursor.rowcount > 0
        conn.close()
        return inserted
        
    except Exception as e:
        conn.close()
        print(f"      ❌ Erro ao inserir: {e}")
        return False


def save_metadata():
    """Guarda metadados da base de dados."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO metadata (key, value) VALUES
        ('source', 'USDA FoodData Central'),
        ('source_url', 'https://fdc.nal.usda.gov/'),
        ('created_at', ?),
        ('citation', 'U.S. Department of Agriculture, Agricultural Research Service. FoodData Central, 2024. fdc.nal.usda.gov')
    """, (datetime.now().isoformat(),))
    
    conn.commit()
    conn.close()


def get_stats() -> Dict[str, Any]:
    """Retorna estatísticas da base de dados."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM foods")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT category, COUNT(*) FROM foods GROUP BY category")
    by_category = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    return {
        "total_foods": total,
        "by_category": by_category,
        "database_path": str(DB_PATH),
    }


# ============================================================
# MAIN BUILD FUNCTION
# ============================================================

def build_database():
    """Constrói a base de dados completa a partir da USDA API."""
    
    print("\n" + "="*60)
    print("🍎 USDA FOODS DATABASE BUILDER")
    print("="*60)
    
    # Verificar API key
    if not USDA_API_KEY:
        print("\n❌ ERRO: USDA_API_KEY não configurada!")
        print("\n📝 Configura o ficheiro .env com:")
        print("   USDA_API_KEY=your_api_key_here")
        print("\n🔗 Obtém a key em: https://fdc.nal.usda.gov/api-key-signup.html")
        sys.exit(1)
    
    print(f"\n✅ API Key configurada: {USDA_API_KEY[:8]}...")
    
    # Criar base de dados
    print("\n📁 Criando base de dados...")
    create_database()
    
    # Contar total de queries
    total_queries = sum(len(foods) for foods in FOODS_TO_FETCH.values())
    current = 0
    total_inserted = 0
    
    print(f"\n🔍 Buscando {total_queries} alimentos da USDA API...\n")
    
    # Buscar alimentos por categoria
    for category, food_queries in FOODS_TO_FETCH.items():
        print(f"\n📂 {category}")
        print("-" * 40)
        
        for query in food_queries:
            current += 1
            print(f"   [{current}/{total_queries}] {query}...", end=" ", flush=True)
            
            # Buscar da API
            results = search_usda(query, page_size=3)
            
            if not results:
                print("❌ Não encontrado")
                continue
            
            # Processar primeiro resultado válido
            inserted = False
            for food_data in results:
                processed = process_food(food_data, category)
                if processed:
                    if insert_food(processed):
                        print(f"✅ {processed['kcal_100g']} kcal")
                        total_inserted += 1
                        inserted = True
                        break
            
            if not inserted:
                print("⚠️ Sem dados válidos")
            
            # Rate limiting (respeitar API)
            time.sleep(0.25)
    
    # Guardar metadados
    save_metadata()
    
    # Estatísticas finais
    stats = get_stats()
    
    print("\n" + "="*60)
    print("✅ BASE DE DADOS CONSTRUÍDA!")
    print("="*60)
    
    print(f"\n📊 Estatísticas:")
    print(f"   • Total de alimentos: {stats['total_foods']}")
    print(f"   • Ficheiro: {stats['database_path']}")
    
    print(f"\n📂 Por categoria:")
    for cat, count in sorted(stats['by_category'].items()):
        print(f"   • {cat}: {count}")
    
    print(f"\n📚 Citação para tese:")
    print('   "U.S. Department of Agriculture, Agricultural Research Service.')
    print('    FoodData Central, 2024. fdc.nal.usda.gov"')
    
    if stats['total_foods'] == 0:
        print("\n⚠️ AVISO: Nenhum alimento foi inserido!")
        print("   Verifica a API key e a conexão à internet.")
        sys.exit(1)
    
    print(f"\n🚀 Próximos passos:")
    print("   1. Verificar: python -m app.data.foods_db")
    print("   2. Usar: POST /chat 'Quantas calorias tem banana?'")
    
    return stats


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    build_database()
