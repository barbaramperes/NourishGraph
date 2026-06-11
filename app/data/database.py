"""
app/data/database.py

Central PostgreSQL database module for NourishGraph.

Supports:
- Neon (https://neon.tech) - Recommended, generous free tier
- Supabase (https://supabase.com) - Alternative with more features
- Local PostgreSQL for development

Configuration via .env:
    DATABASE_URL=postgresql://user:pass@host:5432/dbname

Usage:
    from app.data.database import get_db, Database
    
    db = get_db()
    profile = db.get_profile()
    db.log_meal("Rice with chicken", calories=450)
"""

from __future__ import annotations

import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import uuid

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# PostgreSQL driver
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    print("[WARN] psycopg2 not installed. Install with: pip install psycopg2-binary")

# Alternative: asyncpg for async
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False


# ============================================================
# CONFIGURATION
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_PUBLIC_URL = os.getenv("DATABASE_PUBLIC_URL")

import time as _time
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse


def _strip_sslmode(url: str) -> str:
    """Remove any existing sslmode parameter from the URL."""
    if not url or "sslmode" not in url:
        return url
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params.pop("sslmode", None)
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _set_sslmode(url: str, mode: str) -> str:
    """Set a specific sslmode on a database URL."""
    base = _strip_sslmode(url)
    sep = "&" if "?" in base and base.split("?")[1] else "?"
    if "?" not in base:
        sep = "?"
    return f"{base}{sep}sslmode={mode}"


def _mask_url(url: str) -> str:
    """Mask password in URL for safe logging."""
    try:
        parsed = urlparse(url)
        if parsed.password:
            masked = url.replace(parsed.password, "****")
            return masked
    except Exception:
        pass
    return url[:50] + "..."


def parse_database_url(url: str) -> Dict[str, Any]:
    """Parse DATABASE_URL into components."""
    if not url:
        return {}
    
    from urllib.parse import urlparse
    parsed = urlparse(url)
    
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path[1:] if parsed.path else None,
        "user": parsed.username,
        "password": parsed.password,
    }


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class UserProfile:
    """User profile."""
    id: int = None
    uuid: str = None
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[int] = None
    gender: Optional[str] = None
    goal: Optional[str] = None
    activity: Optional[str] = "sedentary"
    diet: Optional[str] = None  # vegetarian, vegan, keto, mediterranean, carnivore, etc.
    restrictions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None  # Food allergies (nuts, dairy, etc.)
    preferences: Optional[List[str]] = None
    bmi: Optional[float] = None
    bmr: Optional[int] = None
    tdee: Optional[int] = None
    calorie_goal: Optional[int] = None
    protein_goal: Optional[int] = None
    carbs_goal: Optional[int] = None
    fat_goal: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Meal:
    """Meal record."""
    id: int = None
    meal_id: str = None
    user_id: int = 1
    date: str = None
    time: str = None
    meal_type: str = None
    description: str = None
    calories: Optional[int] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Food:
    """Food from USDA database."""
    id: int = None
    fdc_id: Optional[int] = None
    name_en: str = None
    name_pt: Optional[str] = None
    kcal_100g: float = 0
    protein_100g: float = 0
    carbs_100g: float = 0
    fat_100g: float = 0
    fiber_100g: float = 0
    sugar_100g: float = 0
    sodium_mg_100g: float = 0
    category: Optional[str] = None
    
    def get_nutrition(self, grams: float = 100) -> Dict[str, float]:
        """Calculates nutrition for specific quantity."""
        factor = grams / 100.0
        return {
            "kcal": round(self.kcal_100g * factor, 1),
            "protein": round(self.protein_100g * factor, 2),
            "carbs": round(self.carbs_100g * factor, 2),
            "fat": round(self.fat_100g * factor, 2),
            "fiber": round(self.fiber_100g * factor, 2),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# DATABASE CLASS
# ============================================================

class Database:
    """
    Main PostgreSQL database access class.
    
    Example:
        db = Database()
        
        # Profile
        db.save_profile(name="John", weight=70)
        profile = db.get_profile()
        
        # Meals
        db.log_meal("Rice with chicken", calories=450)
        meals = db.get_meals_today()
        
        # Foods
        foods = db.search_foods("banana")
    """
    
    def __init__(self, database_url: str = None, lazy: bool = False):
        """Initializes PostgreSQL connection.
        
        Args:
            database_url: Override DATABASE_URL.
            lazy: If True, don't test the connection now (connect on first use).
        """
        self._raw_primary_url = database_url or DATABASE_URL
        self._raw_fallback_url = DATABASE_PUBLIC_URL
        # Avoid duplicate fallback
        if self._raw_fallback_url and _strip_sslmode(self._raw_fallback_url) == _strip_sslmode(self._raw_primary_url or ""):
            self._raw_fallback_url = None
        
        self.database_url = self._raw_primary_url
        self._connected = False
        
        if not self.database_url:
            raise ValueError(
                "❌ DATABASE_URL not configured!\n"
                "Add to .env file:\n"
                "DATABASE_URL=postgresql://user:pass@host:5432/dbname"
            )
        
        if not HAS_PSYCOPG2:
            raise ImportError(
                "❌ psycopg2 not installed!\n"
                "Install with: pip install psycopg2-binary"
            )
        
        if not lazy:
            self._establish_connection()
    
    def _establish_connection(self):
        """Try all URL + SSL mode combinations until one works."""
        urls_to_try = []
        if self._raw_primary_url:
            urls_to_try.append((self._raw_primary_url, "primary"))
        if self._raw_fallback_url:
            urls_to_try.append((self._raw_fallback_url, "public"))
        
        # SSL modes to try for each URL
        ssl_modes = ["require", "disable", "prefer"]
        
        last_error = None
        for raw_url, label in urls_to_try:
            for ssl_mode in ssl_modes:
                url = _set_sslmode(raw_url, ssl_mode)
                try:
                    print(f"[DB] Trying {label} with sslmode={ssl_mode}...")
                    self._try_connect(url)
                    self.database_url = url
                    self._connected = True
                    print(f"[OK] PostgreSQL connected via {label} (sslmode={ssl_mode})")
                    return
                except Exception as e:
                    err_msg = str(e).replace('\n', ' ')[:120]
                    print(f"[WARN] {label}/sslmode={ssl_mode}: {err_msg}")
                    last_error = e
        
        raise ConnectionError(
            f"❌ PostgreSQL: all connection attempts failed. "
            f"Last error: {str(last_error)[:150]}"
        )
    
    def _try_connect(self, url: str, timeout: int = 8):
        """Single connection attempt with TCP pre-check to avoid long hangs."""
        import socket
        from urllib.parse import urlparse as _urlparse
        
        # Fast TCP check first (avoids psycopg2 hanging on unreachable hosts)
        try:
            parsed = _urlparse(url)
            host = parsed.hostname
            port = parsed.port or 5432
            sock = socket.create_connection((host, port), timeout=3)
            sock.close()
        except Exception as e:
            raise ConnectionError(f"TCP unreachable {host}:{port}: {e}")
        
        # TCP is open — now try the actual PostgreSQL handshake
        conn = psycopg2.connect(url, connect_timeout=timeout)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        finally:
            conn.close()
    
    def _ensure_connected(self):
        """Lazy connection: establish on first use if not yet connected."""
        if not self._connected:
            self._establish_connection()
    
    def run_migrations(self):
        """Run database migrations to add missing columns.
        Each migration runs in its own transaction to prevent one failure
        from aborting subsequent migrations."""
        migrations = [
            # Columns that may be missing depending on which schema created the DB
            ("diet", "ALTER TABLE users ADD COLUMN IF NOT EXISTS diet VARCHAR(50);"),
            ("allergies", "ALTER TABLE users ADD COLUMN IF NOT EXISTS allergies TEXT[];"),
            ("protein_goal", "ALTER TABLE users ADD COLUMN IF NOT EXISTS protein_goal INTEGER;"),
            ("carbs_goal", "ALTER TABLE users ADD COLUMN IF NOT EXISTS carbs_goal INTEGER;"),
            ("fat_goal", "ALTER TABLE users ADD COLUMN IF NOT EXISTS fat_goal INTEGER;"),
            ("google_id", "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255);"),
        ]
        
        for name, sql in migrations:
            try:
                with self._cursor() as cur:
                    cur.execute(sql)
                print(f"[OK] Migration '{name}' applied")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"[WARN] Migration '{name}': {e}")
    
    @contextmanager
    def _connection(self):
        """Context manager for connection with auto-reconnect on failure."""
        self._ensure_connected()
        try:
            conn = psycopg2.connect(self.database_url, connect_timeout=10)
        except psycopg2.OperationalError:
            print("[WARN] DB connection failed, attempting full reconnect...")
            self._connected = False
            self._establish_connection()
            conn = psycopg2.connect(self.database_url, connect_timeout=10)
        try:
            yield conn
        finally:
            conn.close()
    
    @contextmanager
    def _cursor(self, commit: bool = True):
        """Context manager for cursor with dict results."""
        with self._connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
                if commit:
                    conn.commit()
    
    # ========================================
    # PROFILE
    # ========================================
    
    def get_profile(self, user_id: int = 1) -> Optional[UserProfile]:
        """Gets user profile."""
        with self._cursor(commit=False) as cur:
            cur.execute(
                "SELECT * FROM users WHERE id = %s",
                (user_id,)
            )
            row = cur.fetchone()
            
            if not row:
                return None
            
            return UserProfile(
                id=row["id"],
                uuid=str(row["uuid"]) if row.get("uuid") else None,
                name=row.get("name"),
                email=row.get("email"),
                age=row.get("age"),
                weight=float(row["weight"]) if row.get("weight") else None,
                height=row.get("height"),
                gender=row.get("gender"),
                goal=row.get("goal"),
                activity=row.get("activity"),
                diet=row.get("diet"),
                restrictions=row.get("restrictions"),
                allergies=row.get("allergies"),
                preferences=row.get("preferences"),
                bmi=float(row["bmi"]) if row.get("bmi") else None,
                bmr=row.get("bmr"),
                tdee=row.get("tdee"),
                calorie_goal=row.get("calorie_goal"),
                protein_goal=row.get("protein_goal"),
                carbs_goal=row.get("carbs_goal"),
                fat_goal=row.get("fat_goal"),
                created_at=str(row["created_at"]) if row.get("created_at") else None,
                updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
            )
    
    def save_profile(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        age: Optional[int] = None,
        weight: Optional[float] = None,
        height: Optional[int] = None,
        gender: Optional[str] = None,
        goal: Optional[str] = None,
        activity: Optional[str] = None,
        diet: Optional[str] = None,
        restrictions: Optional[List[str]] = None,
        allergies: Optional[List[str]] = None,
        preferences: Optional[List[str]] = None,
        user_id: int = 1
    ) -> Tuple[bool, List[str]]:
        """Saves or updates profile and calculates nutritional goals."""
        changes = []
        
        with self._cursor() as cur:
            # Check if exists
            cur.execute("SELECT id, weight, height, age, gender, goal, activity FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            exists = row is not None
            
            if not exists:
                # Create new
                cur.execute(
                    "INSERT INTO users (id, name) VALUES (%s, %s)",
                    (user_id, name or "User")
                )
                changes.append("👤 Profile created")
                existing_data = {}
            else:
                existing_data = {
                    "weight": row.get("weight"),
                    "height": row.get("height"),
                    "age": row.get("age"),
                    "gender": row.get("gender"),
                    "goal": row.get("goal"),
                    "activity": row.get("activity")
                } if row else {}
            
            # Merge existing with new values
            final_weight = weight if weight is not None else existing_data.get("weight")
            final_height = height if height is not None else existing_data.get("height")
            final_age = age if age is not None else existing_data.get("age")
            final_gender = gender if gender is not None else existing_data.get("gender")
            final_goal = goal if goal is not None else existing_data.get("goal")
            final_activity = activity if activity is not None else existing_data.get("activity", "sedentary")
            
            # Calculate nutritional metrics if we have enough data
            bmi = None
            bmr = None
            tdee = None
            calorie_goal = None
            protein_goal = None
            carbs_goal = None
            fat_goal = None
            
            if final_weight and final_height and final_age and final_gender:
                # Convert Decimal to float for calculations
                final_weight_f = float(final_weight)
                final_height_f = float(final_height)
                final_age_f = float(final_age)
                
                # BMI
                height_m = final_height_f / 100
                bmi = round(final_weight_f / (height_m * height_m), 1)
                
                # BMR (Mifflin-St Jeor)
                # Keep full precision until final rounding for consistency with frontend
                if final_gender and final_gender.upper().startswith('M'):
                    bmr_raw = 10 * final_weight_f + 6.25 * final_height_f - 5 * final_age_f + 5
                else:
                    bmr_raw = 10 * final_weight_f + 6.25 * final_height_f - 5 * final_age_f - 161
                
                # TDEE (activity multiplier)
                activity_multipliers = {
                    'sedentary': 1.2,
                    'light': 1.375,
                    'moderate': 1.55,
                    'active': 1.725,
                    'very_active': 1.9
                }
                multiplier = activity_multipliers.get(final_activity, 1.55)
                tdee_raw = bmr_raw * multiplier
                
                # Round only at the end (single rounding for consistency with frontend)
                bmr = round(bmr_raw)
                tdee = round(tdee_raw)
                
                # Calorie goal based on fitness goal
                if final_goal in ('lose', 'lose_weight'):
                    calorie_goal = round(tdee_raw - 500)  # 500 cal deficit
                elif final_goal in ('gain', 'gain_muscle'):
                    calorie_goal = round(tdee_raw + 300)  # 300 cal surplus
                else:
                    calorie_goal = round(tdee_raw)  # maintain
                
                # Macro goals
                protein_goal = int(final_weight_f * 2)  # 2g per kg
                fat_goal = int((calorie_goal * 0.25) / 9)  # 25% of calories from fat
                carbs_goal = int((calorie_goal - (protein_goal * 4) - (fat_goal * 9)) / 4)
                
                changes.append(f"📊 BMI: {bmi}, BMR: {bmr}, TDEE: {tdee}")
                changes.append(f"🎯 Goals: {calorie_goal} kcal, {protein_goal}g protein, {carbs_goal}g carbs, {fat_goal}g fat")
            
            # Build dynamic UPDATE
            updates = []
            params = []
            
            # Whitelist of allowed fields (prevents SQL injection)
            ALLOWED_UPDATE_FIELDS = {
                "name", "email", "age", "weight", "height", "gender",
                "goal", "activity", "diet", "restrictions", "allergies", "preferences",
                "bmi", "bmr", "tdee", "calorie_goal", "protein_goal", "carbs_goal", "fat_goal"
            }
            
            fields = {
                "name": name,
                "email": email,
                "age": age,
                "weight": weight,
                "height": height,
                "gender": gender,
                "goal": goal,
                "activity": activity,
                "diet": diet,
                "restrictions": restrictions,
                "allergies": allergies,
                "preferences": preferences,
                "bmi": bmi,
                "bmr": bmr,
                "tdee": tdee,
                "calorie_goal": calorie_goal,
                "protein_goal": protein_goal,
                "carbs_goal": carbs_goal,
                "fat_goal": fat_goal,
            }
            
            for field, value in fields.items():
                # Security: Only allow whitelisted fields
                if field not in ALLOWED_UPDATE_FIELDS:
                    continue
                if value is not None:
                    updates.append(f"{field} = %s")
                    params.append(value)
                    if field not in ['bmi', 'bmr', 'tdee', 'calorie_goal', 'protein_goal', 'carbs_goal', 'fat_goal']:
                        changes.append(f"✏️ {field}: {value}")
            
            if updates:
                params.append(user_id)
                query = f"UPDATE users SET {', '.join(updates)}, updated_at = NOW() WHERE id = %s"
                try:
                    cur.execute(query, params)
                except Exception as e:
                    error_str = str(e).lower()
                    if 'column' in error_str and 'does not exist' in error_str:
                        # A column is missing — retry without it
                        print(f"[WARN] save_profile: column missing, retrying without it: {e}")
                        # Parse which column is missing and rebuild
                        import re
                        match = re.search(r'column "(\w+)"', str(e))
                        bad_col = match.group(1) if match else None
                        if bad_col:
                            retry_updates = []
                            retry_params = []
                            for field, value in fields.items():
                                if field not in ALLOWED_UPDATE_FIELDS or field == bad_col:
                                    continue
                                if value is not None:
                                    retry_updates.append(f"{field} = %s")
                                    retry_params.append(value)
                            if retry_updates:
                                retry_params.append(user_id)
                                retry_query = f"UPDATE users SET {', '.join(retry_updates)}, updated_at = NOW() WHERE id = %s"
                                cur.execute(retry_query, retry_params)
                                changes.append(f"⚠️ Column '{bad_col}' missing, saved other fields")
                    else:
                        raise
        
        return True, changes
    
    def clear_profile(self, user_id: int = 1) -> bool:
        """Clears profile (reset)."""
        with self._cursor() as cur:
            cur.execute("""
                UPDATE users SET
                    name = NULL, age = NULL, weight = NULL, height = NULL,
                    gender = NULL, goal = NULL, activity = 'sedentary',
                    restrictions = NULL, preferences = NULL,
                    bmi = NULL, bmr = NULL, tdee = NULL, calorie_goal = NULL
                WHERE id = %s
            """, (user_id,))
            return True
    
    def delete_account(self, user_id: int) -> bool:
        """
        Permanently deletes a user account and ALL associated data.
        This action cannot be undone.
        Uses atomic transaction to ensure data consistency.
        """
        with self._connection() as conn:
            try:
                with conn.cursor() as cur:
                    # Delete all meals for this user
                    cur.execute("DELETE FROM meals WHERE user_id = %s", (user_id,))
                    
                    # Delete the user
                    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                    deleted = cur.rowcount > 0
                
                conn.commit()
                return deleted
            except Exception as e:
                conn.rollback()
                print(f"[DB] Error deleting account {user_id}: {e}")
                raise
    
    # ========================================
    # AUTHENTICATION
    # ========================================
    
    def create_user(
        self,
        email: str,
        password_hash: str,
        name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Creates a new user with email and password hash."""
        try:
            with self._cursor() as cur:
                # Check if email already exists
                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    return None  # Email already exists
                
                # Create user
                cur.execute("""
                    INSERT INTO users (email, password_hash, name, uuid)
                    VALUES (%s, %s, %s, gen_random_uuid())
                    RETURNING id, uuid, email, name, created_at
                """, (email, password_hash, name or email.split('@')[0]))
                
                row = cur.fetchone()
                return {
                    "id": row["id"],
                    "uuid": str(row["uuid"]),
                    "email": row["email"],
                    "name": row["name"],
                    "created_at": str(row["created_at"])
                }
        except Exception as e:
            print(f"[ERROR] Error creating user: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Gets a user by email."""
        with self._cursor(commit=False) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            return {
                "id": row["id"],
                "uuid": str(row["uuid"]) if row.get("uuid") else None,
                "email": row["email"],
                "password_hash": row.get("password_hash"),
                "name": row.get("name"),
                "age": row.get("age"),
                "weight": float(row["weight"]) if row.get("weight") else None,
                "height": row.get("height"),
                "gender": row.get("gender"),
                "goal": row.get("goal"),
                "activity": row.get("activity"),
                "diet": row.get("diet"),
                "restrictions": row.get("restrictions"),
                "allergies": row.get("allergies"),
                "preferences": row.get("preferences"),
                "bmi": float(row["bmi"]) if row.get("bmi") else None,
                "bmr": row.get("bmr"),
                "tdee": row.get("tdee"),
                "calorie_goal": row.get("calorie_goal"),
                "created_at": str(row["created_at"]) if row.get("created_at") else None,
                "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
            }
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Gets a user by ID."""
        with self._cursor(commit=False) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            return {
                "id": row["id"],
                "uuid": str(row["uuid"]) if row.get("uuid") else None,
                "email": row.get("email"),
                "name": row.get("name"),
                "age": row.get("age"),
                "weight": float(row["weight"]) if row.get("weight") else None,
                "height": row.get("height"),
                "gender": row.get("gender"),
                "goal": row.get("goal"),
                "activity": row.get("activity"),
                "diet": row.get("diet"),
                "restrictions": row.get("restrictions"),
                "allergies": row.get("allergies"),
                "preferences": row.get("preferences"),
                "bmi": float(row["bmi"]) if row.get("bmi") else None,
                "bmr": row.get("bmr"),
                "tdee": row.get("tdee"),
                "calorie_goal": row.get("calorie_goal"),
                "password_hash": row.get("password_hash"),
                "created_at": str(row["created_at"]) if row.get("created_at") else None,
                "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
            }
    
    def update_user_profile(
        self,
        user_id: int,
        **kwargs
    ) -> bool:
        """Updates user profile fields."""
        if not kwargs:
            return True
        
        allowed_fields = {
            'name', 'email', 'age', 'weight', 'height', 'gender',
            'goal', 'activity', 'restrictions', 'preferences',
            'bmi', 'bmr', 'tdee', 'calorie_goal'
        }
        
        updates = []
        params = []
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                updates.append(f"{field} = %s")
                params.append(value)
        
        if not updates:
            return True
        
        params.append(user_id)
        
        with self._cursor() as cur:
            query = f"UPDATE users SET {', '.join(updates)}, updated_at = NOW() WHERE id = %s"
            cur.execute(query, params)
            return cur.rowcount > 0
    
    # ========================================
    # FOOD VALIDATION
    # ========================================
    
    # Common non-food items that should not be logged as meals
    NON_FOOD_KEYWORDS = {
        # Personal care / hygiene
        'perfume', 'perfum', 'cologne', 'deodorant', 'desodorante', 'shampoo', 'xampu',
        'conditioner', 'condicionador', 'soap', 'sabonete', 'sabão', 'lotion', 'loção',
        'cream', 'creme facial', 'sunscreen', 'protetor solar', 'makeup', 'maquiagem',
        'lipstick', 'batom', 'mascara', 'nail polish', 'esmalte', 'toothpaste', 'pasta de dente',
        'mouthwash', 'enxaguante', 'floss', 'fio dental', 'razor', 'gilete',
        # Cleaning products
        'detergent', 'detergente', 'bleach', 'lixívia', 'cleaner', 'limpador',
        'disinfectant', 'desinfetante', 'polish', 'wax', 'cera',
        # Medications (should go through safety check)
        'medicine', 'medicamento', 'medication', 'pill', 'pílula', 'comprimido',
        'tablet', 'capsule', 'cápsula', 'injection', 'injeção', 'vaccine', 'vacina',
        'antibiotic', 'antibiótico', 'painkiller', 'analgésico', 'aspirin', 'aspirina',
        'ibuprofen', 'ibuprofeno', 'paracetamol', 'acetaminophen',
        # Office/School supplies
        'pencil', 'lápis', 'pen', 'caneta', 'eraser', 'borracha', 'paper', 'papel',
        'notebook', 'caderno', 'stapler', 'grampeador', 'tape', 'fita',
        # Electronics
        'phone', 'telefone', 'telemóvel', 'celular', 'computer', 'computador',
        'laptop', 'tablet', 'battery', 'bateria', 'charger', 'carregador', 'cable', 'cabo',
        # Clothing
        'shirt', 'camisa', 'pants', 'calças', 'dress', 'vestido', 'shoes', 'sapatos',
        'socks', 'meias', 'underwear', 'roupa interior', 'jacket', 'casaco',
        # Household items
        'furniture', 'móvel', 'chair', 'cadeira', 'table', 'mesa', 'bed', 'cama',
        'pillow', 'almofada', 'blanket', 'cobertor', 'towel', 'toalha',
        # Automotive
        'gasoline', 'gasolina', 'oil', 'óleo motor', 'tire', 'pneu', 'fuel', 'combustível',
        # Tobacco/Drugs (not food)
        'cigarette', 'cigarro', 'tobacco', 'tabaco', 'vape', 'cigar', 'charuto',
        # Misc non-edible
        'plastic', 'plástico', 'metal', 'glass', 'vidro', 'wood', 'madeira',
        'rock', 'pedra', 'sand', 'areia', 'dirt', 'terra',
    }
    
    def is_valid_food_item(self, description: str) -> Tuple[bool, str]:
        """
        Validates if the description is a valid food item.
        Returns (is_valid, error_message).
        """
        if not description or not description.strip():
            return False, "Description cannot be empty."
        
        text = description.lower().strip()
        
        # Check against non-food keywords
        for keyword in self.NON_FOOD_KEYWORDS:
            if keyword in text:
                return False, f"'{description}' is not a food item. Please log only foods and beverages."
        
        # If length is very short (1-2 chars), probably not valid
        if len(text) < 3:
            return False, "Please provide a more descriptive food name."
        
        # Check if it exists in our foods database (optional - allows unknown foods too)
        # We'll be lenient here and allow foods not in DB, but block obvious non-foods
        
        return True, ""
    
    # ========================================
    # NUTRITION ESTIMATION
    # ========================================
    
    def estimate_nutrition_from_text(self, description: str) -> Dict[str, float]:
        """
        Estimates calories/macros only if foods exist in DB.
        If no known food is detected → raises ValueError.
        """
        if not description:
            raise ValueError("Meal description is empty.")

        text = description.lower()

        with self._cursor(commit=False) as cur:
            cur.execute("""
                SELECT *
                FROM foods
                WHERE %s ILIKE '%%' || name_en || '%%'
                   OR %s ILIKE '%%' || COALESCE(name_pt,'') || '%%'
                ORDER BY LENGTH(name_en)
                LIMIT 1
            """, (text, text))

            row = cur.fetchone()

        if not row:
            raise ValueError(
                f"No matching foods found in database for: '{description}'."
            )

        food = self._row_to_food(row)

        # Default quantity
        grams = 150

        n = food.get_nutrition(grams)

        return {
            "calories": n["kcal"],
            "protein": n["protein"],
            "carbs": n["carbs"],
            "fat": n["fat"],
            "fiber": n["fiber"],
        }
    
    # ========================================
    # MEALS
    # ========================================
    
    def log_meal(
        self,
        description: str,
        meal_type: Optional[str] = None,
        calories: Optional[int] = None,
        protein: Optional[float] = None,
        carbs: Optional[float] = None,
        fat: Optional[float] = None,
        fiber: Optional[float] = None,
        notes: Optional[str] = None,
        user_id: int = 1
    ) -> Meal:
        """Logs a meal. Validates that description is a food item."""
        
        # Validate that this is actually a food item
        is_valid, error_msg = self.is_valid_food_item(description)
        if not is_valid:
            raise ValueError(error_msg)
        
        # If calories/macros not provided → estimate
        if calories is None or protein is None or carbs is None or fat is None:
            try:
                est = self.estimate_nutrition_from_text(description)
                calories = calories or int(est["calories"])
                protein = protein or est["protein"]
                carbs = carbs or est["carbs"]
                fat = fat or est["fat"]
                fiber = fiber or est["fiber"]
            except ValueError:
                # If estimation fails, use default values
                calories = calories or 0
                protein = protein or 0
                carbs = carbs or 0
                fat = fat or 0
                fiber = fiber or 0

        now = datetime.now()

        if not meal_type:
            hour = now.hour
            if hour < 10:
                meal_type = "breakfast"
            elif hour < 14:
                meal_type = "lunch"
            elif hour < 18:
                meal_type = "snack"
            else:
                meal_type = "dinner"

        meal_uuid = str(uuid.uuid4())

        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO meals
                (meal_id, user_id, date, time, meal_type, description,
                 calories, protein, carbs, fat, fiber, notes)
                VALUES (%s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (
                meal_uuid, user_id,
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M"),
                meal_type, description,
                calories, protein, carbs, fat, fiber, notes
            ))

            result = cur.fetchone()

        return Meal(
            id=result["id"],
            meal_id=meal_uuid,
            user_id=user_id,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M"),
            meal_type=meal_type,
            description=description,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            fiber=fiber,
            notes=notes,
            created_at=str(result["created_at"]),
        )
    
    def get_meals_today(self, user_id: int = 1) -> List[Meal]:
        """Gets today's meals."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_meals_by_date(today, user_id)
    
    def get_meals_by_date(self, date_str: str, user_id: int = 1) -> List[Meal]:
        """Gets meals for a specific date."""
        with self._cursor(commit=False) as cur:
            cur.execute("""
                SELECT * FROM meals
                WHERE user_id = %s AND date = %s
                ORDER BY time
            """, (user_id, date_str))
            
            return [self._row_to_meal(row) for row in cur.fetchall()]
    
    def get_meals_history(self, days: int = 7, user_id: int = 1) -> List[Meal]:
        """Gets meal history."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with self._cursor(commit=False) as cur:
            cur.execute("""
                SELECT * FROM meals
                WHERE user_id = %s AND date >= %s
                ORDER BY date DESC, time DESC
            """, (user_id, cutoff))
            
            return [self._row_to_meal(row) for row in cur.fetchall()]
    
    def get_daily_totals(self, date_str: str = None, user_id: int = 1) -> Dict[str, Any]:
        """Calculates daily totals."""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        with self._cursor(commit=False) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as meal_count,
                    COALESCE(SUM(calories), 0) as total_calories,
                    COALESCE(SUM(protein), 0) as total_protein,
                    COALESCE(SUM(carbs), 0) as total_carbs,
                    COALESCE(SUM(fat), 0) as total_fat
                FROM meals
                WHERE user_id = %s AND date = %s
            """, (user_id, date_str))
            
            row = cur.fetchone()
            return {
                "date": date_str,
                "meal_count": row["meal_count"],
                "count": row["meal_count"],
                "calories": int(row["total_calories"]),
                "protein": float(row["total_protein"]),
                "carbs": float(row["total_carbs"]),
                "fat": float(row["total_fat"]),
            }
    
    def delete_meal(self, meal_id: str, user_id: int = None) -> bool:
        """Deletes a meal."""
        with self._cursor() as cur:
            if user_id:
                # Verify the meal belongs to the user
                cur.execute(
                    "DELETE FROM meals WHERE meal_id = %s AND user_id = %s",
                    (meal_id, user_id)
                )
            else:
                cur.execute(
                    "DELETE FROM meals WHERE meal_id = %s",
                    (meal_id,)
                )
            return cur.rowcount > 0
    
    def clear_meals(self, user_id: int = 1) -> int:
        """Clears all meals."""
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM meals WHERE user_id = %s",
                (user_id,)
            )
            return cur.rowcount
    
    def _row_to_meal(self, row: Dict) -> Meal:
        """Converts row to Meal."""
        return Meal(
            id=row["id"],
            meal_id=str(row["meal_id"]),
            user_id=row["user_id"],
            date=str(row["date"]),
            time=str(row["time"]),
            meal_type=row["meal_type"],
            description=row["description"],
            calories=row["calories"],
            protein=float(row["protein"]) if row["protein"] else None,
            carbs=float(row["carbs"]) if row["carbs"] else None,
            fat=float(row["fat"]) if row["fat"] else None,
            fiber=float(row["fiber"]) if row.get("fiber") else None,
            notes=row.get("notes"),
            created_at=str(row["created_at"]) if row.get("created_at") else None,
        )
    
    # ========================================
    # FOODS
    # ========================================
    
    # Common food aliases for better search matching (pointing to USDA names)
    FOOD_ALIASES = {
        # Cream/dairy
        "heavy cream": "heavy whipping",
        "whipping cream": "heavy whipping",
        "sour cream": "sour, cultured",
        "half and half": "half and half",
        "cream cheese": "cheese, cream",
        "cheddar": "Cheese, cheddar",
        "parmesan": "Cheese, parmesan",
        "mozzarella": "Cheese, mozzarella",
        "brie": "Cheese, Brie",
        "gouda": "Cheese, gouda",
        "ghee": "Clarified butter (ghee)",
        
        # Eggs
        "egg": "egg, whole",
        "eggs": "egg, whole",
        "boiled egg": "egg, whole, boiled",
        "fried egg": "egg, whole, fried",
        "scrambled egg": "egg, whole, scrambled",
        "egg white": "Eggs, Grade A, Large, egg white",
        "egg yolk": "Egg, yolk, raw, fresh",
        
        # Meats - chicken
        "chicken breast": "Chicken, breast, boneless, skinless, raw",
        "chicken thigh": "chicken, thigh",
        
        # Meats - beef
        "beef steak": "beef, steak",
        "ribeye": "Beef, steak, ribeye",
        "ground beef": "beef, ground",
        "beef patty": "beef, ground, patties",
        "hamburger": "beef, ground, patties",
        "beef liver": "Beef, variety meats and by-products, liver",
        "beef heart": "Beef, variety meats and by-products, heart",
        "beef tongue": "Beef, variety meats and by-products, tongue",
        "beef kidney": "Beef, variety meats and by-products, kidneys",
        
        # Meats - pork
        "bacon": "bacon",
        "pork chop": "pork, chop",
        "pork belly": "Pork, belly",
        "pork sausage": "Pork sausage, link/patty",
        "sausage": "Pork sausage, link/patty",
        "pork rinds": "Snacks, pork skins, plain",
        "lard": "Lard",
        "pork tenderloin": "Pork, loin, tenderloin",
        
        # Meats - lamb
        "lamb chop": "Lamb, New Zealand, imported, loin chop",
        "lamb leg": "Lamb, leg, shank half",
        "lamb": "Lamb, ground",
        
        # Meats - turkey
        "turkey breast": "Turkey, whole, breast, meat only, raw",
        "ground turkey": "Turkey, ground",
        
        # Meats - organ/other
        "chicken liver": "Liver, chicken",
        "liver": "Liver, beef",
        
        # Fats
        "beef tallow": "Fat, beef tallow",
        "tallow": "Fat, beef tallow",
        
        # Seafood
        "salmon": "salmon",
        "tuna": "tuna",
        
        # Common foods
        "rice": "rice, white",
        "brown rice": "rice, brown",
        "pasta": "pasta, cooked",
        "bread": "bread, white",
        "butter": "butter",
        "olive oil": "olive oil",
        "banana": "banana",
        "apple": "apple",
        "orange": "orange",
    }
    
    def search_foods(self, query: str, limit: int = 10) -> List[Food]:
        """Searches for foods with smart aliasing."""
        if not query or not query.strip():
            return []
        
        query_lower = query.lower().strip()
        
        # Check for aliases first
        aliased_query = self.FOOD_ALIASES.get(query_lower, query_lower)
        
        search_term = f"%{aliased_query}%"
        
        with self._cursor(commit=False) as cur:
            cur.execute("""
                SELECT * FROM foods
                WHERE name_en ILIKE %s
                   OR name_pt ILIKE %s
                ORDER BY LENGTH(name_en)
                LIMIT %s
            """, (search_term, search_term, limit))
            
            return [self._row_to_food(row) for row in cur.fetchall()]
    
    def get_food_nutrition(self, query: str, grams: float = 100) -> Optional[Dict]:
        """Gets nutrition info for a food."""
        foods = self.search_foods(query, limit=1)
        if not foods:
            return None
        
        food = foods[0]
        return {
            "food": food.to_dict(),
            "grams": grams,
            "nutrients": food.get_nutrition(grams),
            "per_100g": food.get_nutrition(100),  # Add values per 100g
        }
    
    def _row_to_food(self, row: Dict) -> Food:
        """Converts row to Food."""
        return Food(
            id=row["id"],
            fdc_id=row.get("fdc_id"),
            name_en=row["name_en"],
            name_pt=row.get("name_pt"),
            kcal_100g=float(row["kcal_100g"]) if row["kcal_100g"] else 0,
            protein_100g=float(row["protein_100g"]) if row["protein_100g"] else 0,
            carbs_100g=float(row["carbs_100g"]) if row["carbs_100g"] else 0,
            fat_100g=float(row["fat_100g"]) if row["fat_100g"] else 0,
            fiber_100g=float(row.get("fiber_100g") or 0),
            sugar_100g=float(row.get("sugar_100g") or 0),
            sodium_mg_100g=float(row.get("sodium_mg_100g") or 0),
            category=row.get("category"),
        )
    
    # ========================================
    # CHAT HISTORY
    # ========================================
    
    @staticmethod
    def _ensure_uuid(value: str) -> str:
        """Convert any string to a valid UUID.
        
        The frontend now sends proper UUIDs as chat_id (via crypto.randomUUID()).
        Legacy clients may still send Date.now() timestamps (e.g. '1770476881086').
        PostgreSQL's chat_id column is UUID type, so we convert non-UUID strings
        to a deterministic UUID v5 based on the original value.
        """
        if not value:
            return str(uuid.uuid4())
        try:
            # Already a valid UUID — return as-is
            return str(uuid.UUID(value))
        except (ValueError, AttributeError):
            # Not a UUID (e.g. timestamp) — derive one deterministically
            return str(uuid.uuid5(uuid.NAMESPACE_URL, value))

    def save_chat_message(
        self,
        role: str,
        content: str,
        agent: str = None,
        intent: str = None,
        confidence: float = None,
        tools_used: List[str] = None,
        chat_id: str = None,
        user_id: int = 1
    ) -> int:
        """Saves chat message."""
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO chat_history 
                (chat_id, user_id, role, content, agent, intent, confidence, tools_used)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                self._ensure_uuid(chat_id),
                user_id, role, content, agent, intent, confidence, tools_used
            ))
            return cur.fetchone()["id"]
    
    def get_chat_history(self, limit: int = 50, user_id: int = 1) -> List[Dict]:
        """Gets chat history."""
        with self._cursor(commit=False) as cur:
            cur.execute("""
                SELECT * FROM chat_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, limit))
            
            return [dict(row) for row in cur.fetchall()]
    
    def delete_conversation(self, chat_id: str, user_id: int = 1) -> bool:
        """Deletes all messages for a conversation."""
        try:
            uuid_id = self._ensure_uuid(chat_id)
            with self._cursor() as cur:
                cur.execute(
                    "DELETE FROM chat_history WHERE chat_id = %s AND user_id = %s",
                    (uuid_id, user_id)
                )
                return cur.rowcount > 0
        except Exception as e:
            print(f"[ERROR] delete_conversation: {e}")
            return False

    def get_conversations(self, user_id: int = 1, limit: int = 50) -> List[Dict]:
        """Gets conversations grouped by chat_id with their messages.
        
        Returns a list of conversations, each with:
        - chat_id: the conversation identifier
        - name: auto-generated from first user message
        - created_at: timestamp of first message
        - updated_at: timestamp of last message
        - messages: list of messages in chronological order
        """
        with self._cursor(commit=False) as cur:
            # Get distinct chat_ids for this user, ordered by most recent activity
            cur.execute("""
                SELECT chat_id,
                       MIN(created_at) as created_at,
                       MAX(created_at) as updated_at
                FROM chat_history
                WHERE user_id = %s AND chat_id IS NOT NULL
                GROUP BY chat_id
                ORDER BY MAX(created_at) DESC
                LIMIT %s
            """, (user_id, limit))
            
            conversations = []
            for row in cur.fetchall():
                chat_id = str(row["chat_id"])
                
                # Get all messages for this conversation
                cur.execute("""
                    SELECT role, content, agent, intent, tools_used, sources, created_at
                    FROM chat_history
                    WHERE chat_id = %s AND user_id = %s
                    ORDER BY created_at ASC
                """, (row["chat_id"], user_id))
                
                messages = []
                first_user_msg = None
                for msg in cur.fetchall():
                    msg_dict = {
                        "role": msg["role"],
                        "content": msg["content"],
                    }
                    if msg["agent"]:
                        msg_dict["agent"] = msg["agent"]
                    if msg["intent"]:
                        msg_dict["intent"] = msg["intent"]
                    if msg["tools_used"]:
                        msg_dict["toolsUsed"] = msg["tools_used"]
                    messages.append(msg_dict)
                    
                    # Capture first user message for title
                    if not first_user_msg and msg["role"] == "user":
                        first_user_msg = msg["content"]
                
                # Generate conversation name from first user message
                name = "New Conversation"
                if first_user_msg:
                    words = first_user_msg.split()[:6]
                    name = " ".join(words)
                    if len(name) > 35:
                        name = name[:35] + "..."
                
                conversations.append({
                    "id": chat_id,
                    "name": name,
                    "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
                    "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
                    "messages": messages,
                })
            
            return conversations
    
    # ========================================
    # STATISTICS
    # ========================================
    
    def get_stats(self, user_id: int = 1) -> Dict[str, Any]:
        """General statistics."""
        with self._cursor(commit=False) as cur:
            # Total meals
            cur.execute(
                "SELECT COUNT(*) as count FROM meals WHERE user_id = %s",
                (user_id,)
            )
            total_meals = cur.fetchone()["count"]
            
            # Days with logs
            cur.execute(
                "SELECT COUNT(DISTINCT date) as count FROM meals WHERE user_id = %s",
                (user_id,)
            )
            days_logged = cur.fetchone()["count"]
            
            # Average calories
            cur.execute("""
                SELECT AVG(daily_cal) as avg FROM (
                    SELECT date, SUM(calories) as daily_cal
                    FROM meals WHERE user_id = %s AND calories IS NOT NULL
                    GROUP BY date
                ) daily
            """, (user_id,))
            avg_result = cur.fetchone()
            avg_calories = round(float(avg_result["avg"])) if avg_result["avg"] else 0
            
            # Total foods
            cur.execute("SELECT COUNT(*) as count FROM foods")
            total_foods = cur.fetchone()["count"]
            
            return {
                "total_meals": total_meals,
                "days_logged": days_logged,
                "avg_daily_calories": avg_calories,
                "total_foods": total_foods,
                "database": "PostgreSQL",
            }

    # ============================================================
    # PASSWORD RESET
    # ============================================================

    def save_password_reset_token(
        self,
        email: str,
        token: str,
        expires_at: datetime
    ) -> bool:
        """
        Saves a password reset token for a user.
        Uses upsert to handle multiple reset requests.
        """
        try:
            with self._cursor() as cur:
                # First, delete any existing tokens for this email
                cur.execute("""
                    DELETE FROM password_reset_tokens 
                    WHERE email = %s
                """, (email,))
                
                # Insert new token
                cur.execute("""
                    INSERT INTO password_reset_tokens (email, token, expires_at)
                    VALUES (%s, %s, %s)
                """, (email, token, expires_at))
                
                return True
        except Exception as e:
            print(f"[ERROR] Error saving reset token: {e}")
            return False

    def verify_password_reset_token(self, token: str) -> Optional[str]:
        """
        Verifies a password reset token and returns the email if valid.
        Returns None if token is invalid or expired.
        """
        try:
            with self._cursor(commit=False) as cur:
                cur.execute("""
                    SELECT email, expires_at 
                    FROM password_reset_tokens 
                    WHERE token = %s
                """, (token,))
                row = cur.fetchone()
                
                if not row:
                    return None
                
                # Check if expired
                expires_at = row["expires_at"]
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                
                if datetime.now() > expires_at:
                    # Token expired, delete it
                    self.delete_password_reset_token(token)
                    return None
                
                return row["email"]
        except Exception as e:
            print(f"[ERROR] Error verifying reset token: {e}")
            return None

    def delete_password_reset_token(self, token: str) -> bool:
        """Deletes a password reset token after use or expiration."""
        try:
            with self._cursor() as cur:
                cur.execute("""
                    DELETE FROM password_reset_tokens 
                    WHERE token = %s
                """, (token,))
                return True
        except Exception as e:
            print(f"[ERROR] Error deleting reset token: {e}")
            return False

    def update_user_password(self, email: str, password_hash: str) -> bool:
        """Updates user's password by email."""
        try:
            with self._cursor() as cur:
                cur.execute("""
                    UPDATE users 
                    SET password_hash = %s, updated_at = NOW()
                    WHERE email = %s
                """, (password_hash, email))
                return cur.rowcount > 0
        except Exception as e:
            print(f"[ERROR] Error updating password: {e}")
            return False


# ============================================================
# SINGLETON
# ============================================================

_db_instance: Optional[Database] = None


def get_db() -> Database:
    """Returns singleton Database instance.
    
    Uses lazy initialization: the first call creates the instance.
    Connection is established lazily on first actual DB operation.
    """
    global _db_instance
    if _db_instance is None:
        # Create with lazy=True so it doesn't block
        _db_instance = Database(lazy=True)
    return _db_instance


def warm_db_connection():
    """Try to establish DB connection in background.
    Call this from a thread to avoid blocking the main event loop.
    """
    try:
        db = get_db()
        db._establish_connection()
        try:
            db.run_migrations()
        except Exception as e:
            print(f"[WARN] Migrations: {e}")
        stats = db.get_stats()
        print(f"  PostgreSQL: OK ({stats.get('total_foods', 0)} foods)")
    except Exception as e:
        print(f"  PostgreSQL: PENDING (will retry on first request)")
        print(f"              {str(e)[:100]}")