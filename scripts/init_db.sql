-- NourishGraph Database Schema
-- PostgreSQL initialization script

-- ============================================================
-- EXTENSIONS
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- USERS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash TEXT,
    name VARCHAR(100),
    age INTEGER,
    weight DECIMAL(5,2),
    height INTEGER,
    gender CHAR(1),
    goal VARCHAR(50),
    activity VARCHAR(50) DEFAULT 'sedentary',
    diet VARCHAR(50),  -- vegetarian, vegan, keto, mediterranean, carnivore, etc.
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- MEALS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS meals (
    id SERIAL PRIMARY KEY,
    meal_id UUID DEFAULT uuid_generate_v4 () UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users (id) ON DELETE CASCADE,
    date DATE DEFAULT CURRENT_DATE,
    time TIME DEFAULT CURRENT_TIME,
    meal_type VARCHAR(20),
    description TEXT NOT NULL,
    calories INTEGER,
    protein DECIMAL(6, 2),
    carbs DECIMAL(6, 2),
    fat DECIMAL(6, 2),
    fiber DECIMAL(6, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- FOODS TABLE (USDA FoodData Central)
-- ============================================================
CREATE TABLE IF NOT EXISTS foods (
    id SERIAL PRIMARY KEY,
    fdc_id INTEGER UNIQUE,
    name_en VARCHAR(255) NOT NULL,
    name_pt VARCHAR(255),
    kcal_100g DECIMAL(7, 2) DEFAULT 0,
    protein_100g DECIMAL(6, 2) DEFAULT 0,
    carbs_100g DECIMAL(6, 2) DEFAULT 0,
    fat_100g DECIMAL(6, 2) DEFAULT 0,
    fiber_100g DECIMAL(6, 2) DEFAULT 0,
    sugar_100g DECIMAL(6, 2) DEFAULT 0,
    sodium_mg_100g DECIMAL(7, 2) DEFAULT 0,
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- CHAT HISTORY TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    chat_id UUID DEFAULT uuid_generate_v4() NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    agent VARCHAR(50),
    intent VARCHAR(50),
    confidence DECIMAL(3,2),
    tools_used TEXT[],
    sources JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

CREATE INDEX IF NOT EXISTS idx_users_uuid ON users (uuid);

CREATE INDEX IF NOT EXISTS idx_meals_user_date ON meals (user_id, date);

CREATE INDEX IF NOT EXISTS idx_foods_name ON foods (name_en);

CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history (user_id, created_at);

-- ============================================================
-- SAMPLE FOODS (for testing)
-- ============================================================
INSERT INTO
    foods (
        name_en,
        kcal_100g,
        protein_100g,
        carbs_100g,
        fat_100g,
        fiber_100g,
        category
    )
VALUES (
        'Banana',
        89,
        1.1,
        22.8,
        0.3,
        2.6,
        'Fruits'
    ),
    (
        'Apple',
        52,
        0.3,
        13.8,
        0.2,
        2.4,
        'Fruits'
    ),
    (
        'Chicken Breast',
        165,
        31.0,
        0.0,
        3.6,
        0.0,
        'Meat'
    ),
    (
        'Rice, white, cooked',
        130,
        2.7,
        28.2,
        0.3,
        0.4,
        'Grains'
    ),
    (
        'Egg, whole',
        155,
        13.0,
        1.1,
        11.0,
        0.0,
        'Eggs'
    ),
    (
        'Broccoli',
        34,
        2.8,
        7.0,
        0.4,
        2.6,
        'Vegetables'
    ),
    (
        'Salmon',
        208,
        20.4,
        0.0,
        13.4,
        0.0,
        'Fish'
    ),
    (
        'Oats',
        389,
        16.9,
        66.3,
        6.9,
        10.6,
        'Grains'
    ),
    (
        'Greek Yogurt',
        59,
        10.0,
        3.6,
        0.7,
        0.0,
        'Dairy'
    ),
    (
        'Almonds',
        579,
        21.2,
        21.6,
        49.9,
        12.5,
        'Nuts'
    ) ON CONFLICT DO NOTHING;

SELECT 'Database initialized successfully!' as status;