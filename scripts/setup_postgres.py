#!/usr/bin/env python3
"""
NourishGraph - Setup PostgreSQL

Script to:
1. Create PostgreSQL tables
2. Migrate data from SQLite (if exists)
3. Populate food database

Usage:
    python setup_postgres.py

Requirements:
    - DATABASE_URL configured in .env
    - pip install psycopg2-binary python-dotenv
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not configured!")
    print("\nAdd to .env file:")
    print("DATABASE_URL=postgresql://user:pass@host:5432/dbname")
    print("\nRecommendations (free tier):")
    print("• Neon: https://neon.tech")
    print("• Supabase: https://supabase.com")
    sys.exit(1)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ psycopg2 not installed!")
    print("Install with: pip install psycopg2-binary")
    sys.exit(1)


# ============================================================
# SCHEMA SQL
# ============================================================

SCHEMA_SQL = """
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    age INTEGER CHECK (age >= 1 AND age <= 120),
    weight DECIMAL(5,2) CHECK (weight >= 20 AND weight <= 500),
    height INTEGER CHECK (height >= 50 AND height <= 300),
    gender CHAR(1) CHECK (gender IN ('M', 'F')),
    goal VARCHAR(50),
    activity VARCHAR(20) DEFAULT 'sedentary',
    diet VARCHAR(50),
    restrictions TEXT[],
    allergies TEXT[],
    preferences TEXT[],
    bmi DECIMAL(4,1),
    bmr INTEGER,
    tdee INTEGER,
    calorie_goal INTEGER,
    protein_goal INTEGER,
    carbs_goal INTEGER,
    fat_goal INTEGER,
    google_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- Table: meals
CREATE TABLE IF NOT EXISTS meals (
    id SERIAL PRIMARY KEY,
    meal_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE DEFAULT 1,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    time TIME NOT NULL DEFAULT CURRENT_TIME,
    meal_type VARCHAR(30),
    description TEXT NOT NULL,
    calories INTEGER DEFAULT 0,
    protein DECIMAL(6,2) DEFAULT 0,
    carbs DECIMAL(6,2) DEFAULT 0,
    fat DECIMAL(6,2) DEFAULT 0,
    fiber DECIMAL(6,2) DEFAULT 0,
    sugar DECIMAL(6,2) DEFAULT 0,
    sodium DECIMAL(8,2) DEFAULT 0,
    notes TEXT,
    food_ids INTEGER[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_meals_user_date ON meals(user_id, date);
CREATE INDEX IF NOT EXISTS idx_meals_date ON meals(date);

-- Table: foods
CREATE TABLE IF NOT EXISTS foods (
    id SERIAL PRIMARY KEY,
    fdc_id INTEGER UNIQUE,
    name_en VARCHAR(255) NOT NULL,
    name_pt VARCHAR(255),
    name_search VARCHAR(255),
    kcal_100g DECIMAL(7,2) NOT NULL DEFAULT 0,
    protein_100g DECIMAL(6,2) DEFAULT 0,
    carbs_100g DECIMAL(6,2) DEFAULT 0,
    fat_100g DECIMAL(6,2) DEFAULT 0,
    fiber_100g DECIMAL(6,2) DEFAULT 0,
    sugar_100g DECIMAL(6,2) DEFAULT 0,
    sodium_mg_100g DECIMAL(8,2) DEFAULT 0,
    category VARCHAR(100),
    brand VARCHAR(255),
    source VARCHAR(50) DEFAULT 'USDA',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_foods_name_search ON foods(name_search);
CREATE INDEX IF NOT EXISTS idx_foods_name_en ON foods(name_en);
CREATE INDEX IF NOT EXISTS idx_foods_category ON foods(category);

-- Table: chat_history
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    chat_id UUID DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE DEFAULT 1,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    agent VARCHAR(50),
    intent VARCHAR(50),
    confidence DECIMAL(3,2),
    tools_used TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history(user_id);

-- Table: papers
CREATE TABLE IF NOT EXISTS papers (
    id SERIAL PRIMARY KEY,
    paper_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    doi VARCHAR(255) UNIQUE,
    openalex_id VARCHAR(100),
    pubmed_id VARCHAR(50),
    title TEXT NOT NULL,
    abstract TEXT,
    authors TEXT[],
    journal VARCHAR(500),
    year INTEGER,
    topics TEXT[],
    category VARCHAR(100),
    citations INTEGER DEFAULT 0,
    relevance_score DECIMAL(4,2),
    is_indexed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    indexed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_category ON papers(category);

-- Table: metadata
CREATE TABLE IF NOT EXISTS metadata (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Calculation functions
CREATE OR REPLACE FUNCTION calc_bmi(weight DECIMAL, height INTEGER)
RETURNS DECIMAL AS $$
BEGIN
    IF weight IS NULL OR height IS NULL OR height = 0 THEN
        RETURN NULL;
    END IF;
    RETURN ROUND(weight / ((height::DECIMAL / 100) ^ 2), 1);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION calc_bmr(weight DECIMAL, height INTEGER, age INTEGER, gender CHAR)
RETURNS INTEGER AS $$
DECLARE
    bmr DECIMAL;
BEGIN
    IF weight IS NULL OR height IS NULL OR age IS NULL OR gender IS NULL THEN
        RETURN NULL;
    END IF;
    IF gender = 'F' THEN
        bmr := 10 * weight + 6.25 * height - 5 * age - 161;
    ELSE
        bmr := 10 * weight + 6.25 * height - 5 * age + 5;
    END IF;
    RETURN ROUND(bmr);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION calc_tdee(bmr INTEGER, activity VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    multiplier DECIMAL;
BEGIN
    IF bmr IS NULL THEN RETURN NULL; END IF;
    multiplier := CASE activity
        WHEN 'sedentary' THEN 1.2
        WHEN 'light' THEN 1.375
        WHEN 'moderate' THEN 1.55
        WHEN 'active' THEN 1.725
        WHEN 'very_active' THEN 1.9
        ELSE 1.2
    END;
    RETURN ROUND(bmr * multiplier);
END;
$$ LANGUAGE plpgsql;

-- Trigger to calculate metrics automatically
CREATE OR REPLACE FUNCTION update_user_metrics()
RETURNS TRIGGER AS $$
DECLARE
    new_bmi DECIMAL;
    new_bmr INTEGER;
    new_tdee INTEGER;
    new_goal INTEGER;
BEGIN
    new_bmi := calc_bmi(NEW.weight, NEW.height);
    new_bmr := calc_bmr(NEW.weight, NEW.height, NEW.age, NEW.gender);
    new_tdee := calc_tdee(new_bmr, NEW.activity);
    
    IF new_tdee IS NOT NULL THEN
        new_goal := CASE
            WHEN NEW.goal ILIKE '%lose%' OR NEW.goal ILIKE '%perder%' THEN new_tdee - 500
            WHEN NEW.goal ILIKE '%gain%' OR NEW.goal ILIKE '%ganhar%' THEN new_tdee + 300
            ELSE new_tdee
        END;
    END IF;
    
    NEW.bmi := new_bmi;
    NEW.bmr := new_bmr;
    NEW.tdee := new_tdee;
    NEW.calorie_goal := new_goal;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_user_metrics ON users;
CREATE TRIGGER trigger_update_user_metrics
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_user_metrics();

-- Default user
INSERT INTO users (id, name, email)
VALUES (1, 'User', 'user@nutriai.local')
ON CONFLICT (id) DO NOTHING;

-- Metadata
INSERT INTO metadata (key, value) VALUES 
    ('schema_version', '2.0.0'),
    ('created_at', NOW()::TEXT),
    ('source', 'NourishGraph')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();
"""


# ============================================================
# BASIC FOODS
# ============================================================

BASIC_FOODS = [
    # Fruits
    ("Banana, raw", "Banana", "banana", 89, 1.1, 22.8, 0.3, 2.6, 12.2, 1, "Fruits"),
    ("Apple, raw", "Maçã", "apple maca", 52, 0.3, 13.8, 0.2, 2.4, 10.4, 1, "Fruits"),
    ("Orange, raw", "Laranja", "orange laranja", 47, 0.9, 11.8, 0.1, 2.4, 9.4, 0, "Fruits"),
    ("Strawberries, raw", "Morangos", "strawberry morango", 32, 0.7, 7.7, 0.3, 2.0, 4.9, 1, "Fruits"),
    ("Avocado, raw", "Abacate", "avocado abacate", 160, 2.0, 8.5, 14.7, 6.7, 0.7, 7, "Fruits"),
    
    # Vegetables
    ("Broccoli, raw", "Brócolos", "broccoli brocolos", 34, 2.8, 6.6, 0.4, 2.6, 1.7, 33, "Vegetables"),
    ("Carrot, raw", "Cenoura", "carrot cenoura", 41, 0.9, 9.6, 0.2, 2.8, 4.7, 69, "Vegetables"),
    ("Spinach, raw", "Espinafres", "spinach espinafre", 23, 2.9, 3.6, 0.4, 2.2, 0.4, 79, "Vegetables"),
    ("Tomato, raw", "Tomate", "tomato tomate", 18, 0.9, 3.9, 0.2, 1.2, 2.6, 5, "Vegetables"),
    ("Potato, raw", "Batata", "potato batata", 77, 2.0, 17.5, 0.1, 2.2, 0.8, 6, "Vegetables"),
    
    # Proteins
    ("Chicken breast, raw", "Peito de frango", "chicken frango", 165, 31.0, 0.0, 3.6, 0.0, 0.0, 74, "Protein"),
    ("Beef, ground, raw", "Carne de vaca picada", "beef carne vaca", 254, 17.2, 0.0, 20.0, 0.0, 0.0, 66, "Protein"),
    ("Salmon, raw", "Salmão", "salmon salmao", 208, 20.4, 0.0, 13.4, 0.0, 0.0, 59, "Protein"),
    ("Egg, whole, raw", "Ovo inteiro", "egg ovo", 143, 12.6, 0.7, 9.5, 0.0, 0.4, 142, "Protein"),
    ("Tuna, canned", "Atum em lata", "tuna atum", 116, 25.5, 0.0, 0.8, 0.0, 0.0, 338, "Protein"),
    
    # Dairy
    ("Milk, whole", "Leite gordo", "milk leite", 61, 3.2, 4.8, 3.3, 0.0, 5.0, 43, "Dairy"),
    ("Yogurt, plain", "Iogurte natural", "yogurt iogurte", 59, 10.0, 3.6, 0.5, 0.0, 3.2, 36, "Dairy"),
    ("Cheese, cheddar", "Queijo cheddar", "cheese queijo", 403, 24.9, 1.3, 33.1, 0.0, 0.5, 621, "Dairy"),
    
    # Grains
    ("Rice, white, cooked", "Arroz branco cozido", "rice arroz", 130, 2.7, 28.2, 0.3, 0.4, 0.0, 1, "Grains"),
    ("Bread, white", "Pão branco", "bread pao", 265, 9.4, 49.0, 3.2, 2.7, 5.0, 491, "Grains"),
    ("Pasta, cooked", "Massa cozida", "pasta massa", 131, 5.0, 25.0, 1.1, 1.8, 0.6, 1, "Grains"),
    ("Oats, raw", "Aveia", "oats aveia", 389, 16.9, 66.3, 6.9, 10.6, 0.0, 2, "Grains"),
    
    # Legumes
    ("Lentils, cooked", "Lentilhas cozidas", "lentils lentilhas", 116, 9.0, 20.1, 0.4, 7.9, 1.8, 2, "Legumes"),
    ("Chickpeas, cooked", "Grão de bico cozido", "chickpeas grao bico", 164, 8.9, 27.4, 2.6, 7.6, 4.8, 7, "Legumes"),
    ("Black beans, cooked", "Feijão preto cozido", "black beans feijao preto", 132, 8.9, 23.7, 0.5, 8.7, 0.3, 1, "Legumes"),
    
    # Nuts
    ("Almonds", "Amêndoas", "almonds amendoas", 579, 21.2, 21.6, 49.9, 12.5, 4.4, 1, "Nuts"),
    ("Walnuts", "Nozes", "walnuts nozes", 654, 15.2, 13.7, 65.2, 6.7, 2.6, 2, "Nuts"),
    ("Peanuts", "Amendoins", "peanuts amendoins", 567, 25.8, 16.1, 49.2, 8.5, 4.7, 18, "Nuts"),
]


def main():
    """Main setup function."""
    print("=" * 60)
    print("🐘 NourishGraph - PostgreSQL Setup")
    print("=" * 60)
    
    # Connect
    print("\n📡 Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        print("   ✅ Connection established")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        sys.exit(1)
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Create schema
    print("\n📋 Creating schema...")
    try:
        cursor.execute(SCHEMA_SQL)
        conn.commit()
        print("   ✅ Schema created")
    except Exception as e:
        conn.rollback()
        print(f"   ❌ Error: {e}")
        # Continue even with errors (tables may already exist)
    
    # Verify tables
    print("\n🔍 Verifying tables...")
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = [row['table_name'] for row in cursor.fetchall()]
    print(f"   Tables: {', '.join(tables)}")
    
    # Populate foods
    print("\n🍎 Populating food database...")
    cursor.execute("SELECT COUNT(*) as count FROM foods")
    food_count = cursor.fetchone()['count']
    
    if food_count == 0:
        for food in BASIC_FOODS:
            try:
                cursor.execute("""
                    INSERT INTO foods 
                    (name_en, name_pt, name_search, kcal_100g, protein_100g, 
                     carbs_100g, fat_100g, fiber_100g, sugar_100g, sodium_mg_100g, category)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, food)
            except:
                pass
        conn.commit()
        print(f"   ✅ {len(BASIC_FOODS)} foods added")
    else:
        print(f"   ℹ️ Database already has {food_count} foods")
    
    # Migrate SQLite (if exists)
    sqlite_path = Path(__file__).parent / "app" / "data" / "nutriai.db"
    if sqlite_path.exists():
        print("\n📦 SQLite found - migrating data...")
        migrate_sqlite(sqlite_path, cursor, conn)
    
    # Final statistics
    print("\n📊 Final statistics:")
    
    cursor.execute("SELECT COUNT(*) as count FROM users")
    print(f"   • Users: {cursor.fetchone()['count']}")
    
    cursor.execute("SELECT COUNT(*) as count FROM meals")
    print(f"   • Meals: {cursor.fetchone()['count']}")
    
    cursor.execute("SELECT COUNT(*) as count FROM foods")
    print(f"   • Foods: {cursor.fetchone()['count']}")
    
    cursor.execute("SELECT COUNT(*) as count FROM chat_history")
    print(f"   • Chat messages: {cursor.fetchone()['count']}")
    
    # Close
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start the API: python app/api.py")
    print("2. Open the frontend: npm run dev (in frontend folder)")
    print("=" * 60)


def migrate_sqlite(sqlite_path: Path, pg_cursor, pg_conn):
    """Migrate data from SQLite to PostgreSQL."""
    import sqlite3
    
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        # Migrate profile
        sqlite_cursor.execute("SELECT * FROM users WHERE id = 1")
        user = sqlite_cursor.fetchone()
        if user:
            pg_cursor.execute("""
                UPDATE users SET
                    name = %s, age = %s, weight = %s, height = %s,
                    gender = %s, goal = %s, activity = %s
                WHERE id = 1
            """, (
                user['nome'], user['idade'], user['peso'], user['altura'],
                user['sexo'], user['objetivo'], user['atividade']
            ))
            pg_conn.commit()
            print("   ✅ Profile migrated")
        
        # Migrate meals
        sqlite_cursor.execute("SELECT * FROM meals")
        meals = sqlite_cursor.fetchall()
        for meal in meals:
            try:
                pg_cursor.execute("""
                    INSERT INTO meals 
                    (user_id, date, time, meal_type, description, calories, protein, carbs, fat)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    1, meal['date'], meal['time'], meal['meal_type'],
                    meal['description'], meal['calories'],
                    meal['protein'], meal['carbs'], meal['fat']
                ))
            except:
                pass
        pg_conn.commit()
        print(f"   ✅ {len(meals)} meals migrated")
        
        sqlite_conn.close()
        
    except Exception as e:
        print(f"   ⚠️ Migration error: {e}")


if __name__ == "__main__":
    main()