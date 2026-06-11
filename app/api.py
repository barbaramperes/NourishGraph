#!/usr/bin/env python3
"""
NourishGraph - FastAPI (PostgreSQL + LangGraph)

Complete API for the NourishGraph website.
Uses PostgreSQL as database and LangGraph for intelligent processing.

To run:
    python -m app.api
    # or
    uvicorn app.api:app --reload --port 8000

Test:
    - Swagger UI: http://localhost:8000/docs
    - Postman: http://localhost:8000/openapi.json
"""

import os
import sys
import traceback
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

try:
    import jwt  # PyJWT
except Exception:  # pragma: no cover
    jwt = None

from fastapi import FastAPI, HTTPException, Query, Depends, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
import json
import asyncio

# Load environment variables
from dotenv import load_dotenv

# Add app to path for imports
APP_DIR = Path(__file__).parent
ROOT_DIR = APP_DIR.parent
for p in [str(APP_DIR), str(ROOT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Load .env from repository root regardless of where the process is started.
# This is important for AUTH_SECRET_KEY so JWT sessions remain valid.
try:
    load_dotenv(dotenv_path=ROOT_DIR / ".env")
except Exception:
    load_dotenv()

# ================================================================
# IMPORT DATABASE
# ================================================================

HAS_DATABASE = False
get_db = None

try:
    from app.data.database import Database, get_db
    HAS_DATABASE = True
except ImportError:
    try:
        from data.database import Database, get_db
        HAS_DATABASE = True
    except ImportError as e:
        print(f"[ERROR] Database module not found: {e}")

# ================================================================
# IMPORT SAFETY MODULE
# ================================================================

HAS_SAFETY = False
safety_guard = None

try:
    from app.safety import (
        check_input_safety, 
        add_safety_disclaimer, 
        detect_red_flags,
        SafetyLevel,
        SafetyResult
    )
    from app.safety.metrics import get_safety_metrics, record_safety_event
    HAS_SAFETY = True
except ImportError:
    try:
        from safety import (
            check_input_safety,
            add_safety_disclaimer,
            detect_red_flags,
            SafetyLevel,
            SafetyResult
        )
        from safety.metrics import get_safety_metrics, record_safety_event
        HAS_SAFETY = True
    except ImportError as e:
        print(f"[WARN] Safety module not available: {e}")

# ================================================================
# IMPORT LANGGRAPH
# ================================================================

HAS_LANGGRAPH = False
run_agent = None
run_supervisor = None
USE_SUPERVISOR = os.getenv("USE_SUPERVISOR", "false").lower() == "true"

try:
    from app.graph.graph import run_agent, compile_graph
    HAS_LANGGRAPH = True
    # Import supervisor if available
    try:
        from app.graph.supervisor import run_supervisor, is_supervisor_enabled
        print(f"[OK] LangGraph Supervisor available (enabled={USE_SUPERVISOR})")
    except ImportError:
        pass
except ImportError:
    try:
        from graph.graph import run_agent, compile_graph
        HAS_LANGGRAPH = True
    except ImportError as e:
        print(f"[WARN] LangGraph not available: {e}")


# ================================================================
# IMPORT MEMORY MANAGER
# ================================================================

HAS_MEMORY = False
get_memory_manager = None

try:
    from app.memory.manager import get_memory_manager, clear_user_memory
    HAS_MEMORY = True
except ImportError:
    try:
        from memory.manager import get_memory_manager, clear_user_memory
        HAS_MEMORY = True
    except ImportError as e:
        print(f"[WARN] Memory manager not available: {e}")


# ================================================================
# RATE LIMITING (In-Memory for single instance, use Redis for scale)
# ================================================================
from collections import defaultdict
import time
from threading import Lock

class RateLimiter:
    """
    Simple in-memory rate limiter.
    For production with multiple instances, use Redis-based rate limiting.
    """
    def __init__(self):
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()
    
    def is_rate_limited(
        self, 
        key: str, 
        max_requests: int = 5, 
        window_seconds: int = 60
    ) -> tuple[bool, int]:
        """
        Check if a key is rate limited.
        
        Args:
            key: Identifier (e.g., IP address, email, user_id)
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
            
        Returns:
            (is_limited: bool, retry_after_seconds: int)
        """
        now = time.time()
        window_start = now - window_seconds
        
        with self._lock:
            # Clean old requests
            self._requests[key] = [
                ts for ts in self._requests[key] 
                if ts > window_start
            ]
            
            # Check if rate limited
            if len(self._requests[key]) >= max_requests:
                oldest = min(self._requests[key])
                retry_after = int(oldest + window_seconds - now) + 1
                return True, max(retry_after, 1)
            
            # Record this request
            self._requests[key].append(now)
            return False, 0
    
    def cleanup(self, max_age_seconds: int = 3600):
        """Remove entries older than max_age_seconds."""
        cutoff = time.time() - max_age_seconds
        with self._lock:
            keys_to_remove = []
            for key, timestamps in self._requests.items():
                self._requests[key] = [ts for ts in timestamps if ts > cutoff]
                if not self._requests[key]:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del self._requests[key]


# Global rate limiter instance
rate_limiter = RateLimiter()

# Rate limit configurations
RATE_LIMITS = {
    "login": {"max_requests": 5, "window_seconds": 300},      # 5 attempts per 5 minutes
    "signup": {"max_requests": 3, "window_seconds": 3600},    # 3 signups per hour per IP
    "forgot_password": {"max_requests": 3, "window_seconds": 3600},  # 3 requests per hour
    "chat": {"max_requests": 30, "window_seconds": 60},       # 30 messages per minute
}


def check_rate_limit(request: Request, endpoint: str) -> None:
    """
    Check rate limit for an endpoint. Raises HTTPException if limited.
    
    Uses client IP as the rate limit key.
    """
    # Get client IP (handle proxies)
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.client.host if request.client else "unknown"
    
    config = RATE_LIMITS.get(endpoint, {"max_requests": 60, "window_seconds": 60})
    key = f"{endpoint}:{client_ip}"
    
    is_limited, retry_after = rate_limiter.is_rate_limited(
        key, 
        config["max_requests"], 
        config["window_seconds"]
    )
    
    if is_limited:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )


# ================================================================
# LIFESPAN
# ================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    print("\n" + "=" * 58)
    print("  NOURISHGRAPH API v2.0")
    print("  Agentic AI Nutrition Assistant")
    print("=" * 58)

    auth_secret_loaded = bool(_get_auth_secret_key())
    jwt_enabled = bool(jwt) and auth_secret_loaded
    print(f"  Auth:       {'OK (JWT)' if jwt_enabled else 'WARN (legacy tokens)'}")
    
    if HAS_DATABASE:
        # Warm up DB connection in a background thread — don't block startup
        import threading
        from app.data.database import warm_db_connection
        db_thread = threading.Thread(target=warm_db_connection, daemon=True)
        db_thread.start()
        print("  PostgreSQL: CONNECTING (background)...")
    else:
        print("  PostgreSQL: NOT CONFIGURED")
    
    if HAS_LANGGRAPH:
        print(f"  LangGraph:  OK (5 agents)")
    else:
        print(f"  LangGraph:  DISABLED")
    
    print(f"\n  Server:     http://localhost:8000")
    print(f"  Docs:       http://localhost:8000/docs")
    print("=" * 58 + "\n")
    
    yield
    
    print("\n[INFO] NourishGraph API shutdown\n")


# ================================================================
# FASTAPI APP
# ================================================================

app = FastAPI(
    title="NourishGraph API",
    description="""
**NourishGraph** - Agentic AI Nutrition Assistant

## Architecture
- **Database**: PostgreSQL (Neon)
- **Vector Store**: Pinecone (Hybrid RAG)
- **Orchestration**: LangGraph (Multi-Agent)

## Agents
- **ScienceAgent**: Scientific literature search (RAG)
- **NutritionAgent**: Nutritional calculations (BMR, TDEE, macros)
- **ProfileAgent**: User profile and meal management
- **ChatAgent**: General nutrition conversation
- **MealPlannerAgent**: Personalized meal planning

## Endpoints
- `POST /chat` - Main chat endpoint (LangGraph)
- `GET/POST/DELETE /profile` - User profile management
- `GET/POST/DELETE /meals` - Meal logging
- `GET /foods/search` - Food database search
- `GET /stats` - Usage statistics
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Configuration - restrict in production
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://nourishgraph.up.railway.app",
    "https://nourishgraph-production.up.railway.app",
]
# Filter empty strings
_allowed_origins = [o.strip() for o in _allowed_origins if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# ================================================================
# PYDANTIC MODELS
# ================================================================

class ProfileIn(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = Field(None, ge=1, le=120)
    sex: Optional[str] = None
    gender: Optional[str] = None  # Alias for sex from frontend
    weight: Optional[float] = Field(None, ge=20, le=500)
    height: Optional[float] = Field(None, ge=50, le=300)
    goal: Optional[str] = None
    activity: Optional[str] = "sedentary"
    diet: Optional[str] = None  # vegetarian, vegan, keto, mediterranean, carnivore, etc.
    restrictions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None  # Food allergies (nuts, dairy, etc.)
    preferences: Optional[List[str]] = None
    # Calculated fields from frontend (will be recalculated by backend)
    calorie_goal: Optional[int] = None
    protein_goal: Optional[int] = None
    carbs_goal: Optional[int] = None
    fat_goal: Optional[int] = None


# ================================================================
# ERROR HANDLING HELPERS
# ================================================================
import logging

logger = logging.getLogger(__name__)

def sanitize_error_message(e: Exception, context: str = "operation") -> str:
    """
    Sanitize error messages to avoid exposing internal details to users.
    Logs the full error for debugging, returns safe message to user.
    """
    error_str = str(e).lower()
    
    # Log full error for debugging
    logger.error(f"Error in {context}: {type(e).__name__}: {e}")
    
    # Return safe, user-friendly messages based on error type
    if "connection" in error_str or "timeout" in error_str:
        return "Service temporarily unavailable. Please try again."
    elif "duplicate" in error_str or "unique" in error_str:
        return "This record already exists."
    elif "not found" in error_str or "does not exist" in error_str:
        return "The requested resource was not found."
    elif "permission" in error_str or "access denied" in error_str:
        return "You don't have permission to perform this action."
    elif "invalid" in error_str:
        return "Invalid request. Please check your input."
    elif "rate limit" in error_str:
        return "Too many requests. Please wait a moment."
    else:
        return f"An error occurred during {context}. Please try again."


# ================================================================
# AUTH MODELS & HELPERS
# ================================================================

class SignupIn(BaseModel):
    email: str
    password: str
    name: Optional[str] = None


class LoginIn(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


# ================================================================
# EMAIL VALIDATION HELPERS
# ================================================================
import re

# Try to import dns.resolver for MX record validation
try:
    import dns.resolver
    HAS_DNS = True
except ImportError:
    HAS_DNS = False
    print("[WARNING] dnspython not installed - email domain verification disabled")

# Common disposable email domains to block
DISPOSABLE_EMAIL_DOMAINS = {
    'tempmail.com', 'throwaway.email', 'guerrillamail.com', 'mailinator.com',
    'temp-mail.org', '10minutemail.com', 'fakeinbox.com', 'trashmail.com',
    'yopmail.com', 'sharklasers.com', 'getnada.com', 'tempail.com',
    'maildrop.cc', 'mailnesia.com', 'dispostable.com', 'tempr.email'
}

def validate_email_format(email: str) -> tuple[bool, str]:
    """
    Validate email format using regex.
    Returns (is_valid, error_message).
    """
    if not email:
        return False, "Email is required"
    
    email = email.strip().lower()
    
    # RFC 5322 compliant email regex (simplified but robust)
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_regex, email):
        return False, "Invalid email format. Please use a valid email address (e.g., user@example.com)"
    
    # Check length constraints
    if len(email) > 254:
        return False, "Email address is too long"
    
    local_part, domain = email.rsplit('@', 1)
    
    if len(local_part) > 64:
        return False, "Email local part is too long"
    
    if len(domain) > 253:
        return False, "Email domain is too long"
    
    # Check for consecutive dots
    if '..' in email:
        return False, "Email cannot contain consecutive dots"
    
    # Check for leading/trailing dots in local part
    if local_part.startswith('.') or local_part.endswith('.'):
        return False, "Email local part cannot start or end with a dot"
    
    return True, ""


def is_disposable_email(email: str) -> bool:
    """Check if email is from a known disposable email provider."""
    try:
        domain = email.lower().strip().rsplit('@', 1)[1]
        return domain in DISPOSABLE_EMAIL_DOMAINS
    except:
        return False


def verify_email_domain(email: str) -> tuple[bool, str]:
    """
    Verify that the email domain has valid MX records.
    Returns (is_valid, error_message).
    """
    # Skip DNS check if dnspython not available
    if not HAS_DNS:
        return True, ""
    
    try:
        domain = email.lower().strip().rsplit('@', 1)[1]
        
        # Try to resolve MX records
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            if mx_records:
                return True, ""
        except dns.resolver.NoAnswer:
            pass
        except dns.resolver.NXDOMAIN:
            return False, f"The email domain '{domain}' does not exist"
        except dns.resolver.NoNameservers:
            pass
        except Exception:
            pass
        
        # Fallback: try to resolve A record
        try:
            a_records = dns.resolver.resolve(domain, 'A')
            if a_records:
                return True, ""
        except:
            pass
        
        return False, f"The email domain '{domain}' cannot receive emails"
        
    except Exception as e:
        # If DNS check fails, allow the email (don't block due to network issues)
        return True, ""


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    Returns (is_valid, error_message).
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password is too long (max 128 characters)"
    
    # Check for at least one letter and one number
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    if not has_letter:
        return False, "Password must contain at least one letter"
    
    if not has_digit:
        return False, "Password must contain at least one number"
    
    return True, ""


def normalize_email(email: str) -> str:
    """Normalize email address (lowercase, strip whitespace)."""
    return email.strip().lower() if email else ""


# Backward-compat in-memory token store (dev only).
# Kept so existing sessions in the same process still work even if JWT isn't available.
_active_tokens: Dict[str, int] = {}  # token -> user_id


def _get_auth_secret_key() -> Optional[str]:
    # Prefer explicit auth secret; fall back to common env var names.
    return (
        os.getenv("AUTH_SECRET_KEY")
        or os.getenv("NUTRISAGE_SECRET_KEY")
        or os.getenv("SECRET_KEY")
    )


def create_access_token(user_id: int, *, expires_in_days: int = 30) -> str:
    """Create a signed access token.

    Uses JWT if PyJWT is installed and a stable secret exists.
    Falls back to a random token stored in-memory (dev-only) otherwise.
    """
    secret = _get_auth_secret_key()
    if jwt and secret:
        now = datetime.utcnow()
        payload = {
            "sub": str(user_id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=expires_in_days)).timestamp()),
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    # Fallback (not restart-safe)
    token = generate_token()
    _active_tokens[token] = user_id
    return token


def decode_access_token(token: str) -> Optional[int]:
    """Decode a token into user_id.

    Supports JWT (preferred) and in-memory legacy tokens (fallback).
    """
    # JWT path
    secret = _get_auth_secret_key()
    if jwt and secret:
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            sub = payload.get("sub")
            return int(sub) if sub is not None else None
        except Exception:
            # Fall through to legacy lookup
            pass

    # Legacy path
    return _active_tokens.get(token)


def hash_password(password: str) -> str:
    """Hash password with salt."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{hash_obj.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    try:
        salt, stored_hash = password_hash.split(':')
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_obj.hex() == stored_hash
    except (ValueError, AttributeError, TypeError) as e:
        # Log specific errors instead of silently failing
        print(f"[AUTH] Password verification failed: {type(e).__name__}")
        return False


def generate_token() -> str:
    """Generate a secure token."""
    return secrets.token_urlsafe(32)


def get_current_user_id(authorization: Optional[str] = Header(None)) -> Optional[int]:
    """Get current user ID from token."""
    if not authorization:
        return None
    
    # Support "Bearer token" format
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    
    return decode_access_token(token)


def require_auth(authorization: Optional[str] = Header(None)) -> int:
    """Require authentication - raises 401 if not authenticated."""
    user_id = get_current_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id


class ProfileOut(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    gender: Optional[str] = None  # Alias for frontend compatibility
    weight: Optional[float] = None
    height: Optional[int] = None
    goal: Optional[str] = None
    activity: Optional[str] = None
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


class MealIn(BaseModel):
    meal_type: Optional[str] = None
    description: str
    calories: Optional[int] = Field(0, ge=0)
    protein: Optional[float] = Field(0, ge=0)
    carbs: Optional[float] = Field(0, ge=0)
    fat: Optional[float] = Field(0, ge=0)
    fiber: Optional[float] = Field(0, ge=0)
    notes: Optional[str] = None


class MealOut(BaseModel):
    id: Optional[int] = None
    meal_id: Optional[str] = None
    meal_type: Optional[str] = None
    description: Optional[str] = None
    calories: Optional[int] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    time: Optional[str] = None
    date: Optional[str] = None
    notes: Optional[str] = None


class MealsResponse(BaseModel):
    meals: List[MealOut]
    totals: Dict[str, Any]
    date: str


# Maximum message length to prevent abuse
MAX_MESSAGE_LENGTH = 10000


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    profile: Optional[Dict[str, Any]] = None  # Profile from frontend (priority)
    chat_id: Optional[str] = None  # Conversation ID for grouping messages


class SourceOut(BaseModel):
    """Scientific source/paper reference."""
    id: Optional[str] = None
    title: str = ""
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    source: Optional[str] = None  # Journal name
    score: Optional[float] = None
    path: Optional[str] = None  # PDF file path (e.g., "papers_pdf/filename.pdf")
    filename: Optional[str] = None  # Just the filename (e.g., "filename.pdf")


class ChatOut(BaseModel):
    response: str
    agent: str = "NourishGraph"
    intent: Optional[str] = None
    tools_used: Optional[List[str]] = None
    sources: Optional[List[SourceOut]] = None
    # Evidence grading (for science queries)
    evidence_level: Optional[str] = None  # A, B, C, D, or None
    confidence: Optional[float] = None  # 0.0 to 1.0
    # Confirmation gate fields
    requires_confirmation: bool = False
    pending: Optional[Dict[str, Any]] = None
    # Safety fields (TA5 - Guardrails)
    safety_level: Optional[str] = None
    safety_flags: Optional[List[str]] = None
    # Profile sync signal - tells frontend to reload profile from DB
    profile_updated: bool = False
    # Nutritional calculations (for visual display)
    calculations: Optional[Dict[str, Any]] = None


class FoodOut(BaseModel):
    id: int
    fdc_id: Optional[int] = None
    name_en: str
    name_pt: Optional[str] = None
    kcal_100g: float
    protein_100g: float
    carbs_100g: float
    fat_100g: float
    fiber_100g: Optional[float] = None
    category: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str
    langgraph: str
    timestamp: str


class StatsResponse(BaseModel):
    total_meals: int
    days_logged: int
    avg_daily_calories: int
    total_foods: int
    database: str


# ================================================================
# HELPERS
# ================================================================

import re

def clean_llm_response(text: str) -> str:
    """
    Post-process LLM response to remove fake links and other artifacts.
    The LLM sometimes generates fake links even when instructed not to.
    """
    if not text:
        return text
    
    # Patterns to remove - fake links and disclaimers
    patterns_to_remove = [
        # Fake links with parentheses
        r'\(link is illustrative\)',
        r'\(illustrative link\)',
        r'\(example link\)',
        r'\[Read the full paper here\][^\]]*',
        r'Read the full paper here\.?',
        r'Read the full study here\.?',
        r'Read more here\.?',
        r'Access the paper here\.?',
        r'Full text available here\.?',
        r'Click here to read\.?',
        # Markdown links with fake URLs
        r'\[.*?\]\(https?://[^\)]+\)',
        # Plain URLs that look fake
        r'https?://example\.com[^\s]*',
        r'https?://placeholder[^\s]*',
        r'https?://link[^\s]*',
        # DOI links (we want sources panel instead)
        r'https?://doi\.org/[^\s\)]*',
        r'DOI:\s*10\.[^\s]*',
        # Common fake patterns
        r'\[link\]',
        r'\(link\)',
        r'here\s+is\s+the\s+link',
        r'access\s+the\s+full\s+paper',
    ]
    
    result = text
    for pattern in patterns_to_remove:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Clean up extra whitespace/newlines left behind
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = re.sub(r'  +', ' ', result)
    result = result.strip()
    
    return result


def check_db():
    if not HAS_DATABASE or get_db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return get_db()


def extract_sources_from_result(result: Dict[str, Any], response_text: str = "") -> List[SourceOut]:
    """
    Extract scientific paper sources from LangGraph result.
    Only returns papers that are actually cited in the response text.
    
    The sources can be in:
    - result["context"]["papers"] - from hybrid search
    - result["context"]["sources"] - direct sources list
    - result["sources"] - direct sources in result
    """
    sources_list = []
    context = result.get("context", {})
    
    # Check for papers in context
    papers = context.get("papers", []) or context.get("sources", []) or result.get("sources", [])
    
    if not papers:
        return []
    
    # Filter papers to only include those actually cited in the response
    response_lower = response_text.lower() if response_text else ""
    
    print(f"   📚 Processing {len(papers)} papers for sources (filtering by citation)")
    
    for paper in papers:
        title = paper.get("title", "")
        if not title:
            continue
        
        # Check if this paper is actually cited in the response
        # Look for author name, year, or significant part of title
        authors = paper.get("authors", [])
        year = str(paper.get("year", "")) if paper.get("year") else ""
        
        # Get first author's last name
        first_author = ""
        if isinstance(authors, list) and authors:
            first_author = authors[0].split()[-1].lower() if authors[0] else ""
        elif isinstance(authors, str) and authors:
            first_author = authors.split(",")[0].split()[-1].lower()
        
        # Check if paper is cited (author + year, or significant title match)
        is_cited = False
        if response_lower:
            # Check for "Author (Year)" or "Author et al. (Year)" pattern
            if first_author and year:
                if f"{first_author}" in response_lower and year in response_text:
                    is_cited = True
            # Check for title keywords (first 3 significant words)
            title_words = [w.lower() for w in title.split()[:5] if len(w) > 4]
            if title_words and any(word in response_lower for word in title_words[:3]):
                is_cited = True
        else:
            # No response text to check - include all papers
            is_cited = True
        
        if not is_cited:
            continue
            
        # Get PDF path from filename
        filename = paper.get("filename", "")
        
        # Ensure filename has .pdf extension
        if filename and not filename.endswith('.pdf'):
            filename = filename.replace('.json', '.pdf').replace('.txt', '.pdf')
            if not filename.endswith('.pdf'):
                filename = filename + '.pdf'
        
        pdf_path = f"papers/pdf/{filename}" if filename else None
        
        sources_list.append(SourceOut(
            id=paper.get("id"),
            title=title,
            authors=paper.get("authors") if isinstance(paper.get("authors"), list) else [paper.get("authors", "")] if paper.get("authors") else [],
            year=paper.get("year"),
            abstract=paper.get("abstract", "") or paper.get("text", "")[:500] if paper.get("text") else "",
            source=paper.get("source", ""),
            score=paper.get("score_hybrid") or paper.get("score"),
            path=pdf_path,
            filename=filename
        ))
    
    print(f"   ✅ Returning {len(sources_list)} sources")
    return sources_list


def meal_to_response(meal) -> MealOut:
    if meal is None:
        return MealOut()
    m = meal.to_dict() if hasattr(meal, 'to_dict') else (meal if isinstance(meal, dict) else {})
    return MealOut(
        id=m.get("id"),
        meal_id=m.get("meal_id"),
        meal_type=m.get("meal_type", ""),
        description=m.get("description", ""),
        calories=m.get("calories", 0),
        protein=m.get("protein", 0),
        carbs=m.get("carbs", 0),
        fat=m.get("fat", 0),
        fiber=m.get("fiber", 0),
        time=m.get("time", ""),
        date=m.get("date", ""),
        notes=m.get("notes", ""),
    )


def profile_to_response(profile) -> ProfileOut:
    if profile is None:
        return ProfileOut()
    p = profile.to_dict() if hasattr(profile, 'to_dict') else (profile if isinstance(profile, dict) else {})
    gender_value = p.get("gender") or p.get("sex")
    return ProfileOut(
        id=p.get("id"),
        name=p.get("name"),
        email=p.get("email"),
        age=p.get("age"),
        sex=gender_value,
        gender=gender_value,  # Both fields for compatibility
        weight=p.get("weight"),
        height=p.get("height"),
        goal=p.get("goal"),
        activity=p.get("activity"),
        diet=p.get("diet"),
        restrictions=p.get("restrictions"),
        allergies=p.get("allergies"),
        preferences=p.get("preferences"),
        bmi=p.get("bmi"),
        bmr=p.get("bmr"),
        tdee=p.get("tdee"),
        calorie_goal=p.get("calorie_goal"),
        protein_goal=p.get("protein_goal"),
        carbs_goal=p.get("carbs_goal"),
        fat_goal=p.get("fat_goal"),
    )


def extract_calculations_from_profile(user_profile: Dict[str, Any], intent: str, message: str = "") -> Optional[Dict[str, Any]]:
    """
    Extract nutritional calculations from user profile for visual display.
    
    Returns calculation data ONLY when the query is specifically about
    calories, weight goals, BMR, TDEE, or diet planning.
    """
    if not user_profile:
        return None
    
    # Only show calculations for nutrition-related queries
    if intent not in ["nutrition", "profile", "meal"]:
        return None
    
    # Only show calculations when the message is actually about calories/weight/diet
    import re
    msg_lower = (message or "").lower()
    CALORIE_KEYWORDS = (
        r'(?:calori\w*|cal[oó]ri\w*|kcal|bmr|tdee|metaboli\w*|energy\s*(?:expenditure|intake|needs)|'
        r'how\s+many\s+calories|quant[ao]s?\s+caloria\w*|'
        r'macros?\b|weight\s*(?:loss|gain|goal)|'
        r'lose\s+weight|gain\s+(?:weight|muscle)|perder\s+peso|ganhar\s+(?:peso|m[uú]sculo)|'
        r'diet\s*(?:plan|target)|meal\s*plan|plano\s*(?:alimentar|de\s*refei)|'
        r'daily\s*(?:intake|target|goal|needs)|'
        r'how\s+much\s+should\s+i\s+eat|quanto\s+devo\s+comer|'
        r'surplus|deficit|maintenance|manuten[çc][aã]o|'
        r'target.*kcal|target.*calori|objetivo.*calori)'
    )
    if not re.search(CALORIE_KEYWORDS, msg_lower, re.IGNORECASE):
        return None
    
    # Check if we have enough profile data
    weight = user_profile.get("weight")
    height = user_profile.get("height")
    age = user_profile.get("age")
    gender = user_profile.get("gender") or user_profile.get("sex")
    
    if not all([weight, height, age]):
        return None
    
    # Calculate BMR (Mifflin-St Jeor)
    # NOTE: Do NOT round intermediate values — round only the final target_calories.
    # This matches the frontend calculation in macroCalculations.js and avoids
    # 1-kcal drift between the Dashboard card and the API-returned value.
    is_male = gender and str(gender).upper().startswith("M")
    bmr_base = 10 * weight + 6.25 * height - 5 * age
    bmr_raw = bmr_base + 5 if is_male else bmr_base - 161
    
    # Get activity level and calculate TDEE
    activity = user_profile.get("activity", "moderate")
    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
        "extreme": 1.9
    }
    multiplier = activity_multipliers.get(activity, 1.55)
    tdee_raw = bmr_raw * multiplier
    
    # Get goal and calculate target calories
    goal_raw = user_profile.get("goal", "maintain")
    # Normalize goal names (frontend uses lose_weight/gain_muscle, backend uses lose/gain)
    goal_mapping = {
        "lose_weight": "lose",
        "lose": "lose",
        "maintain": "maintain",
        "gain_muscle": "gain",
        "gain": "gain"
    }
    goal = goal_mapping.get(goal_raw, "maintain")
    goal_adjustments = {
        "lose": -500,
        "maintain": 0,
        "gain": 300
    }
    adjustment = goal_adjustments.get(goal, 0)
    # Single round at the very end — matches frontend calculateCalorieGoal()
    target_calories = round(tdee_raw + adjustment)
    
    # Rounded versions for display in the returned payload
    bmr = round(bmr_raw)
    tdee = round(tdee_raw)
    
    # Calculate macros (balanced split)
    # Protein: 25%, Carbs: 45%, Fat: 30%
    protein = round((target_calories * 0.25) / 4)  # 4 cal/g
    carbs = round((target_calories * 0.45) / 4)    # 4 cal/g
    fat = round((target_calories * 0.30) / 9)      # 9 cal/g
    
    # Override with stored goals if available
    if user_profile.get("protein_goal"):
        protein = user_profile.get("protein_goal")
    if user_profile.get("carbs_goal"):
        carbs = user_profile.get("carbs_goal")
    if user_profile.get("fat_goal"):
        fat = user_profile.get("fat_goal")
    
    return {
        "weight": weight,
        "height": height,
        "age": age,
        "gender": gender,
        "bmr": bmr,
        "tdee": tdee,
        "activityLevel": activity,
        "goal": goal,
        "targetCalories": target_calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
    }


# ================================================================
# ENDPOINTS - INFO
# ================================================================

@app.get("/", tags=["Info"], response_class=HTMLResponse, include_in_schema=False)
async def root():
    """Serve frontend in production or API info in development."""
    # Check if static directory exists (production build)
    static_dir = ROOT_DIR / "static"
    index_file = static_dir / "index.html"
    
    if index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")
    
    # Development mode - return API info as JSON
    from fastapi.responses import JSONResponse
    return JSONResponse({
        "name": "NourishGraph API",
        "version": "2.0.0",
        "database": "PostgreSQL" if HAS_DATABASE else "Not configured",
        "langgraph": "Available" if HAS_LANGGRAPH else "Simple mode",
        "docs": "/docs",
    })


@app.get("/health", response_model=HealthResponse, tags=["Info"])
async def health_check():
    db_status = "not_configured"
    if HAS_DATABASE:
        try:
            # Only check DB if singleton already exists and is connected
            from app.data.database import _db_instance
            if _db_instance is not None and getattr(_db_instance, '_connected', False):
                _db_instance.get_stats()
                db_status = "connected"
            else:
                db_status = "initializing"
        except ImportError:
            db_status = "initializing"
        except Exception as e:
            db_status = f"error: {str(e)[:30]}"
    
    langgraph_status = "simple_mode"
    if HAS_LANGGRAPH:
        langgraph_status = "supervisor" if USE_SUPERVISOR else "standard"
    
    # Always return "online" — the server is running and can serve requests.
    # DB issues are reported in the database field but don't make the service unhealthy.
    return HealthResponse(
        status="online",
        service="NourishGraph API",
        version="2.0.0",
        database=db_status,
        langgraph=langgraph_status,
        timestamp=datetime.now().isoformat(),
    )


@app.get("/db-diagnostics", tags=["Info"])
async def db_diagnostics():
    """Fast diagnostic endpoint — only DNS + TCP checks (no blocking psycopg2 connect)."""
    import socket
    results = {
        "DATABASE_URL_set": bool(os.getenv("DATABASE_URL")),
        "DATABASE_PUBLIC_URL_set": bool(os.getenv("DATABASE_PUBLIC_URL")),
        "psycopg2_available": False,
        "tests": [],
    }
    
    try:
        import psycopg2
        results["psycopg2_available"] = True
        results["psycopg2_version"] = psycopg2.__version__
    except ImportError:
        pass
    
    from app.data.database import _db_instance
    
    results["singleton_exists"] = _db_instance is not None
    results["singleton_connected"] = getattr(_db_instance, '_connected', False) if _db_instance else False
    results["active_url_host"] = ""
    if _db_instance and _db_instance.database_url:
        try:
            from urllib.parse import urlparse
            p = urlparse(_db_instance.database_url)
            results["active_url_host"] = f"{p.hostname}:{p.port}"
            results["active_sslmode"] = dict(parse_qs(p.query)).get("sslmode", ["not set"])
        except Exception:
            pass
    
    urls = []
    db_url = os.getenv("DATABASE_URL")
    pub_url = os.getenv("DATABASE_PUBLIC_URL")
    if db_url:
        urls.append(("DATABASE_URL", db_url))
    if pub_url:
        urls.append(("DATABASE_PUBLIC_URL", pub_url))
    
    for label, raw_url in urls:
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(raw_url)
            host = parsed.hostname
            port = parsed.port or 5432
            db_name = parsed.path[1:] if parsed.path else "unknown"
            
            test = {
                "label": label,
                "host": f"{host}:{port}",
                "database": db_name,
                "user": parsed.username,
            }
            
            # DNS test (fast)
            try:
                addrs = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
                test["dns_ok"] = True
                test["ip_addresses"] = list(set(a[4][0] for a in addrs[:5]))
            except Exception as e:
                test["dns_ok"] = False
                test["dns_error"] = str(e)[:100]
            
            # TCP test (2s timeout — fast)
            if test.get("dns_ok"):
                try:
                    sock = socket.create_connection((host, port), timeout=3)
                    sock.close()
                    test["tcp_open"] = True
                except Exception as e:
                    test["tcp_open"] = False
                    test["tcp_error"] = str(e)[:100]
            
            results["tests"].append(test)
        except Exception as e:
            results["tests"].append({
                "label": label,
                "error": str(e)[:150],
            })
    
    return results


@app.get("/stats", response_model=StatsResponse, tags=["Info"])
async def get_stats():
    try:
        db = check_db()
        stats = db.get_stats()
        return StatsResponse(
            total_meals=stats.get("total_meals", 0),
            days_logged=stats.get("days_logged", 0),
            avg_daily_calories=stats.get("avg_daily_calories", 0),
            total_foods=stats.get("total_foods", 0),
            database="PostgreSQL",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=sanitize_error_message(e, "retrieving database stats"))


@app.get("/data-sources", tags=["Info"])
async def get_data_sources():
    """
    Get available data sources for the agent.
    
    Returns information about all integrated data sources:
    - PostgreSQL: User profiles, meals, and USDA foods
    - Pinecone: Scientific papers with hybrid search
    """
    sources = {
        "databases": {
            "postgresql": {
                "status": "connected" if HAS_DATABASE else "not_configured",
                "description": "User profiles, meals, and USDA food database",
                "data": {
                    "foods": "USDA FoodData Central",
                    "profiles": "User profiles and preferences",
                    "meals": "Meal logging and history"
                }
            },
            "pinecone": {
                "status": "available",
                "description": "Hybrid search (Dense + BM25) over scientific papers",
                "data": {
                    "papers": "34 papers from PubMed and OpenAlex",
                    "topics": ["nutrition", "vitamins", "diet", "microbiome", "metabolism"],
                    "search_type": "Hybrid (semantic + lexical)"
                }
            }
        },
        "local_files": {
            "papers_txt": {
                "status": "available",
                "description": "34 scientific papers as text files",
                "path": "papers_txt/"
            }
        },
        "agents": {
            "ScienceAgent": {
                "description": "Scientific evidence from indexed papers",
                "tools": ["search_scientific_papers", "get_paper_details"],
                "data_source": "Pinecone (PubMed/OpenAlex papers)"
            },
            "NutritionAgent": {
                "description": "Nutritional calculations and food info",
                "tools": ["calculate_bmr", "calculate_tdee", "get_food_nutrition"],
                "data_source": "PostgreSQL (USDA foods)"
            },
            "ProfileAgent": {
                "description": "User profile and meal management",
                "tools": ["save_user_profile", "log_meal", "get_meals_history"],
                "data_source": "PostgreSQL"
            },
            "MealPlannerAgent": {
                "description": "Personalized meal planning",
                "tools": ["generate_meal_plan", "suggest_foods_for_goal"],
                "data_source": "PostgreSQL + User profile"
            }
        }
    }
    return sources


@app.get("/safety/metrics", tags=["Safety"])
async def get_safety_stats():
    """
    Get safety metrics for evaluation (TA5 - Guardrails).
    
    Returns:
        Safety compliance metrics, flag frequencies, and recent events.
    """
    if not HAS_SAFETY:
        return {"error": "Safety module not available", "enabled": False}
    
    try:
        metrics = get_safety_metrics()
        return {
            "enabled": True,
            **metrics.get_summary()
        }
    except Exception as e:
        return {"error": str(e), "enabled": True}


@app.get("/safety/report", tags=["Safety"])
async def get_safety_report():
    """
    Get formatted safety evaluation report for thesis.
    
    Returns:
        Markdown-formatted safety compliance report.
    """
    if not HAS_SAFETY:
        return {"error": "Safety module not available"}
    
    try:
        metrics = get_safety_metrics()
        return {
            "report": metrics.get_evaluation_report(),
            "format": "markdown"
        }
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# ENDPOINTS - OBSERVABILITY & METRICS
# ================================================================

@app.get("/metrics", tags=["Observability"])
async def get_pipeline_metrics():
    """
    Get comprehensive pipeline metrics for observability.
    
    Returns metrics from:
    - Adaptive RAG (query complexity distribution, strategy usage)
    - Feedback Loop (quality scores, refinement rates)
    - Tracing (latencies, success rates)
    """
    try:
        from app.graph.enhanced_pipeline import get_enhanced_pipeline
        pipeline = get_enhanced_pipeline()
        return pipeline.get_metrics()
    except ImportError:
        return {"error": "Enhanced pipeline not available", "enabled": False}
    except Exception as e:
        return {"error": str(e)}


@app.get("/metrics/prometheus", tags=["Observability"])
async def get_prometheus_metrics():
    """
    Get metrics in Prometheus format for scraping.
    
    Compatible with Prometheus/Grafana monitoring stack.
    """
    try:
        from app.observability.tracing import Tracer
        tracer = Tracer("api")
        return tracer.collector.export_prometheus()
    except ImportError:
        return "# Tracing module not available\n"
    except Exception as e:
        return f"# Error: {e}\n"


@app.get("/metrics/trace/{trace_id}", tags=["Observability"])
async def get_trace_details(trace_id: str):
    """
    Get detailed trace information by trace ID.
    
    Returns span hierarchy, timings, and metadata for debugging.
    """
    try:
        from app.observability.tracing import Tracer
        tracer = Tracer("api")
        
        # Try to find trace in history
        for trace in tracer.traces[-100:]:  # Last 100 traces
            if trace.id == trace_id:
                return {
                    "trace_id": trace.id,
                    "name": trace.name,
                    "start_time": trace.start_time.isoformat(),
                    "end_time": trace.end_time.isoformat() if trace.end_time else None,
                    "duration_ms": trace.duration_ms,
                    "success": trace.success,
                    "error": trace.error,
                    "spans": [
                        {
                            "id": s.id,
                            "name": s.name,
                            "duration_ms": s.duration_ms,
                            "metadata": s.metadata
                        }
                        for s in trace.spans
                    ],
                    "metadata": trace.metadata
                }
        
        return {"error": "Trace not found", "trace_id": trace_id}
    except ImportError:
        return {"error": "Tracing module not available"}
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# ENDPOINTS - AUTH
# ================================================================

@app.post("/auth/signup", response_model=AuthResponse, tags=["Auth"])
async def signup(data: SignupIn, request: Request):
    """
    Register a new user.
    
    Validates:
    - Email format (RFC 5322 compliant)
    - Email domain has valid MX records
    - Email is not from disposable email providers
    - Email is not already registered
    - Password strength (min 8 chars, letters + numbers)
    
    Rate limited: 3 signups per hour per IP.
    
    Returns a token that should be sent in Authorization header for subsequent requests.
    """
    # Check rate limit first
    check_rate_limit(request, "signup")
    
    try:
        db = check_db()
        
        # Normalize email
        email = normalize_email(data.email)
        
        # 1. Validate email format
        is_valid, error_msg = validate_email_format(email)
        if not is_valid:
            return AuthResponse(success=False, message=error_msg)
        
        # 2. Check for disposable email
        if is_disposable_email(email):
            return AuthResponse(
                success=False, 
                message="Disposable email addresses are not allowed. Please use a permanent email."
            )
        
        # 3. Verify email domain has MX records (can receive emails)
        is_valid, error_msg = verify_email_domain(email)
        if not is_valid:
            return AuthResponse(success=False, message=error_msg)
        
        # 4. Validate password strength
        is_valid, error_msg = validate_password_strength(data.password)
        if not is_valid:
            return AuthResponse(success=False, message=error_msg)
        
        # 5. Check if user already exists
        existing = db.get_user_by_email(email)
        if existing:
            return AuthResponse(
                success=False, 
                message="This email is already registered. Please login or use a different email."
            )
        
        # 6. Validate name (optional but sanitize)
        name = data.name.strip() if data.name else None
        if name and len(name) > 100:
            return AuthResponse(success=False, message="Name is too long (max 100 characters)")
        
        # Hash password and create user
        password_hash = hash_password(data.password)
        user = db.create_user(
            email=email,
            password_hash=password_hash,
            name=name
        )
        
        if not user:
            return AuthResponse(success=False, message="Failed to create user. Please try again.")
        
        # Generate token (JWT preferred)
        token = create_access_token(user["id"])
        
        # Return user data (without password hash)
        user_data = {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "hasProfile": False  # New user needs onboarding
        }
        
        return AuthResponse(
            success=True,
            token=token,
            user=user_data,
            message="Registration successful! Welcome to NourishGraph."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        return AuthResponse(success=False, message="Registration failed. Please try again later.")


@app.post("/auth/login", response_model=AuthResponse, tags=["Auth"])
async def login(data: LoginIn, request: Request):
    """
    Login with email and password.
    
    Rate limited: 5 attempts per 5 minutes per IP.
    
    Returns a token that should be sent in Authorization header for subsequent requests.
    """
    # Check rate limit first
    check_rate_limit(request, "login")
    
    try:
        db = check_db()
        
        # Normalize email
        email = normalize_email(data.email)
        
        # Validate email format
        is_valid, _ = validate_email_format(email)
        if not is_valid:
            return AuthResponse(success=False, message="Invalid email format")
        
        # Get user
        user = db.get_user_by_email(email)
        if not user:
            return AuthResponse(success=False, message="Account not found. Please check your email or create a new account.")
        
        # Verify password
        if not user.get("password_hash") or not verify_password(data.password, user["password_hash"]):
            return AuthResponse(success=False, message="Incorrect password. Please try again.")
        
        # Generate token (JWT preferred)
        token = create_access_token(user["id"])
        
        # Check if user has profile (weight is a good indicator)
        has_profile = bool(user.get("weight") or user.get("age"))
        
        # Return user data (without password hash)
        user_data = {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "age": user.get("age"),
            "weight": user.get("weight"),
            "height": user.get("height"),
            "gender": user.get("gender"),
            "goal": user.get("goal"),
            "activity": user.get("activity"),
            "diet": user.get("diet"),
            "allergies": user.get("allergies"),
            "hasProfile": has_profile
        }
        
        return AuthResponse(
            success=True,
            token=token,
            user=user_data,
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        return AuthResponse(success=False, message=sanitize_error_message(e, "login"))


class ForgotPasswordIn(BaseModel):
    email: str


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


@app.post("/change-password", tags=["Auth"])
async def change_password(data: ChangePasswordIn, user_id: int = Depends(require_auth)):
    """Change the authenticated user's password."""
    try:
        db = check_db()
        
        # Get current user
        user = db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify current password
        if not user.get("password_hash") or not verify_password(data.current_password, user["password_hash"]):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Hash new password and update
        new_hash = hash_password(data.new_password)
        
        with db._cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
                (new_hash, user_id)
            )
        return {"success": True, "message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to change password")


class GoogleAuthIn(BaseModel):
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


@app.post("/auth/google", response_model=AuthResponse, tags=["Auth"])
async def google_auth(data: GoogleAuthIn):
    """
    Authenticate with Google OAuth.
    
    Creates user if doesn't exist, or logs in if exists.
    Always updates name from Google to ensure it's current.
    Returns a JWT token for subsequent requests.
    """
    try:
        db = check_db()
        
        if not data.email or '@' not in data.email:
            return AuthResponse(success=False, message="Invalid email from Google")
        
        # Check if user exists
        user = db.get_user_by_email(data.email)
        
        if user:
            # Existing user - login and update name from Google if different
            if data.name and user.get("name") != data.name:
                db.update_user_profile(user["id"], name=data.name)
                user["name"] = data.name
        else:
            # New user - create account (no password needed for Google users)
            user = db.create_user(
                email=data.email,
                password_hash=None,  # Google users don't have password
                name=data.name
            )
            if not user:
                return AuthResponse(success=False, message="Failed to create account")
        
        # Generate JWT token
        token = create_access_token(user["id"])
        
        # Check if user has profile
        has_profile = bool(user.get("weight") or user.get("age"))
        
        # Always use the name from Google (data.name) as primary
        user_data = {
            "id": user["id"],
            "email": user["email"],
            "name": data.name or user.get("name"),
            "age": user.get("age"),
            "weight": user.get("weight"),
            "height": user.get("height"),
            "gender": user.get("gender"),
            "goal": user.get("goal"),
            "activity": user.get("activity"),
            "diet": user.get("diet"),
            "allergies": user.get("allergies"),
            "hasProfile": has_profile
        }
        
        return AuthResponse(
            success=True,
            token=token,
            user=user_data,
            message="Google authentication successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        return AuthResponse(success=False, message=sanitize_error_message(e, "Google authentication"))


@app.post("/auth/forgot-password", tags=["Auth"])
async def forgot_password(data: ForgotPasswordIn, request: Request, background_tasks: BackgroundTasks):
    """
    Request password reset. Sends an email with reset instructions.
    
    Rate limited: 3 requests per hour per IP.
    """
    # Check rate limit first
    check_rate_limit(request, "forgot_password")
    
    try:
        db = check_db()
        
        # Check if user exists
        user = db.get_user_by_email(data.email)
        
        # Always return success to prevent email enumeration attacks
        if user:
            # Generate secure reset token
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=1)
            
            # Save token to database
            db.save_password_reset_token(data.email, reset_token, expires_at)
            
            # Send email in background
            try:
                from app.services.email_service import send_password_reset_email
                background_tasks.add_task(
                    send_password_reset_email,
                    to_email=data.email,
                    reset_token=reset_token,
                    user_name=user.get("name")
                )
                print(f"📧 Password reset email queued for: {data.email}")
            except ImportError:
                print(f"📧 Email service not available. Reset token for {data.email}: {reset_token}")
        else:
            print(f"📧 Password reset requested for non-existent email: {data.email}")
        
        return {"success": True, "message": "If an account exists with this email, you'll receive reset instructions."}
        
    except Exception as e:
        traceback.print_exc()
        return {"success": True, "message": "If an account exists with this email, you'll receive reset instructions."}


@app.post("/auth/reset-password", tags=["Auth"])
async def reset_password(data: ResetPasswordIn):
    """
    Reset password using token from email.
    
    The token is validated and the password is updated if valid.
    """
    try:
        db = check_db()
        
        # Verify token and get email
        email = db.verify_password_reset_token(data.token)
        
        if not email:
            raise HTTPException(
                status_code=400, 
                detail="Invalid or expired reset token. Please request a new password reset."
            )
        
        # Validate new password
        if len(data.new_password) < 6:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 6 characters long"
            )
        
        # Hash new password using the same method as signup
        new_password_hash = hash_password(data.new_password)
        
        # Update password
        success = db.update_user_password(email, new_password_hash)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update password")
        
        # Delete the used token
        db.delete_password_reset_token(data.token)
        
        print(f"✅ Password reset successful for: {email}")
        
        return {"success": True, "message": "Password reset successful. You can now log in with your new password."}
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=sanitize_error_message(e, "password reset"))


@app.get("/auth/me", tags=["Auth"])
async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Get current authenticated user info.
    
    Requires Authorization header with token.
    """
    user_id = get_current_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        db = check_db()
        user = db.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user has profile
        has_profile = bool(user.get("weight") or user.get("age"))
        
        return {
            "id": user["id"],
            "email": user.get("email"),
            "name": user.get("name"),
            "age": user.get("age"),
            "weight": user.get("weight"),
            "height": user.get("height"),
            "gender": user.get("gender"),
            "goal": user.get("goal"),
            "activity": user.get("activity"),
            "diet": user.get("diet"),
            "allergies": user.get("allergies"),
            "restrictions": user.get("restrictions"),
            "preferences": user.get("preferences"),
            "calorie_goal": user.get("calorie_goal"),
            "hasProfile": has_profile
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_error_message(e, "request"))


@app.post("/auth/logout", tags=["Auth"])
async def logout(authorization: Optional[str] = Header(None)):
    """
    Logout current user (invalidate token).
    """
    if authorization:
        token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
        # JWTs are stateless; "logout" is client-side token removal.
        # If this was a legacy in-memory token, revoke it here.
        if token in _active_tokens:
            del _active_tokens[token]
    
    return {"success": True, "message": "Logged out"}


# ================================================================
# ENDPOINTS - PROFILE
# ================================================================

@app.get("/profile", response_model=ProfileOut, tags=["Profile"])
async def get_profile(user_id: int = Depends(require_auth)):
    try:
        db = check_db()
        profile = db.get_profile(user_id=user_id)
        return profile_to_response(profile)
    except HTTPException:
        raise
    except Exception as e:
        return ProfileOut()


@app.post("/profile", tags=["Profile"])
async def save_profile(data: ProfileIn, user_id: int = Depends(require_auth)):
    try:
        db = check_db()
        # Accept both 'sex' and 'gender' from frontend
        sex_value = data.sex or data.gender
        sex = sex_value.upper()[0] if sex_value and len(sex_value) > 0 else None
        
        logger.info(f"[PROFILE SAVE] user_id={user_id}, diet={data.diet}, allergies={data.allergies}")
        
        success, changes = db.save_profile(
            name=data.name,
            email=data.email,
            age=data.age,
            weight=data.weight,
            height=int(data.height) if data.height else None,
            gender=sex,
            goal=data.goal,
            activity=data.activity,
            diet=data.diet,
            restrictions=data.restrictions,
            allergies=data.allergies,
            preferences=data.preferences,
            user_id=user_id,
        )
        
        profile = db.get_profile(user_id=user_id)
        response_profile = profile_to_response(profile).model_dump()
        logger.info(f"[PROFILE SAVED] user_id={user_id}, diet_in_response={response_profile.get('diet')}, changes={changes}")
        return {
            "success": success,
            "changes": changes,
            "profile": response_profile,
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=sanitize_error_message(e, "request"))


@app.delete("/profile", tags=["Profile"])
async def clear_profile(user_id: int = Depends(require_auth)):
    try:
        db = check_db()
        db.clear_profile(user_id=user_id)
        return {"success": True, "message": "Profile cleared"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_error_message(e, "request"))


@app.delete("/account", tags=["Profile"])
async def delete_account(user_id: int = Depends(require_auth)):
    """
    Permanently delete user account and ALL associated data.
    This action cannot be undone.
    """
    try:
        db = check_db()
        success = db.delete_account(user_id=user_id)
        if success:
            return {"success": True, "message": "Account permanently deleted"}
        else:
            raise HTTPException(status_code=404, detail="Account not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_error_message(e, "request"))


# ================================================================
# ENDPOINTS - MEALS
# ================================================================

@app.get("/meals", response_model=MealsResponse, tags=["Meals"])
async def get_meals(user_id: int = Depends(require_auth)):
    try:
        db = check_db()
        meals_today = db.get_meals_today(user_id=user_id)
        meals_list = [meal_to_response(m) for m in meals_today]
        totals = db.get_daily_totals(user_id=user_id)
        return MealsResponse(
            meals=meals_list,
            totals={
                "calories": totals.get("calories", 0),
                "protein": totals.get("protein", 0),
                "carbs": totals.get("carbs", 0),
                "fat": totals.get("fat", 0),
                "meals": totals.get("count", 0),
            },
            date=date.today().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        return MealsResponse(meals=[], totals={}, date=date.today().isoformat())


@app.post("/meals", tags=["Meals"])
async def add_meal(data: MealIn, user_id: int = Depends(require_auth)):
    try:
        db = check_db()
        # Map meal type names (support both English and Portuguese)
        tipo_map = {
            "breakfast": "breakfast",
            "lunch": "lunch",
            "snack": "snack",
            "dinner": "dinner",
            "pequeno-almoço": "breakfast",
            "pequeno-almoco": "breakfast",
            "pequeno_almoco": "breakfast",
            "almoço": "lunch",
            "almoco": "lunch",
            "lanche": "snack",
            "jantar": "dinner",
        }
        meal_type = tipo_map.get(data.meal_type, data.meal_type) if data.meal_type else None
        
        meal = db.log_meal(
            description=data.description,
            meal_type=meal_type,
            calories=data.calories,
            protein=data.protein,
            carbs=data.carbs,
            fat=data.fat,
            fiber=data.fiber,
            notes=data.notes,
            user_id=user_id,
        )
        return {
            "success": True,
            "meal": meal_to_response(meal).model_dump(),
            "message": f"✅ Meal logged: {data.description}",
        }
    except ValueError as e:
        # Food validation failed - return user-friendly error
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=sanitize_error_message(e, "request"))


@app.delete("/meals/{meal_id}", tags=["Meals"])
async def delete_meal(meal_id: str, user_id: int = Depends(require_auth)):
    try:
        db = check_db()
        success = db.delete_meal(meal_id, user_id=user_id)
        if success:
            return {"success": True, "message": "Meal deleted"}
        else:
            raise HTTPException(status_code=404, detail="Meal not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_error_message(e, "request"))


@app.get("/history", tags=["Meals"])
async def get_history(days: int = Query(7, ge=1, le=365), user_id: int = Depends(require_auth)):
    try:
        db = check_db()
        meals = db.get_meals_history(days=days, user_id=user_id)
        return [meal_to_response(m).model_dump() for m in meals]
    except Exception:
        return []


# ================================================================
# ENDPOINTS - FOODS
# ================================================================

@app.get("/foods/search", response_model=List[FoodOut], tags=["Foods"])
async def search_foods(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50)
):
    try:
        db = check_db()
        foods = db.search_foods(q, limit=limit)
        return [
            FoodOut(
                id=f.id,
                fdc_id=f.fdc_id,
                name_en=f.name_en,
                name_pt=f.name_pt,
                kcal_100g=f.kcal_100g,
                protein_100g=f.protein_100g,
                carbs_100g=f.carbs_100g,
                fat_100g=f.fat_100g,
                fiber_100g=f.fiber_100g,
                category=f.category,
            )
            for f in foods
        ]
    except Exception as e:
        return []


@app.get("/foods/nutrition", tags=["Foods"])
async def get_nutrition(
    q: str = Query(...),
    grams: float = Query(100, ge=1)
):
    try:
        db = check_db()
        result = db.get_food_nutrition(q, grams=grams)
        if not result:
            raise HTTPException(status_code=404, detail=f"Food '{q}' not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_error_message(e, "request"))


# ================================================================
# ENDPOINTS - CONVERSATIONS (Server-persisted chat history)
# ================================================================

@app.get("/conversations", tags=["Chat"])
async def get_conversations(user_id: int = Depends(require_auth)):
    """
    Get all conversations for the authenticated user.
    Returns conversations grouped by chat_id with their messages,
    so chat history persists across browser windows and devices.
    """
    try:
        db = get_db()
        conversations = db.get_conversations(user_id=user_id, limit=50)
        return {"conversations": conversations}
    except Exception as e:
        print(f"[ERROR] get_conversations: {e}")
        return {"conversations": []}


@app.delete("/conversations/{chat_id}", tags=["Chat"])
async def delete_conversation(chat_id: str, user_id: int = Depends(require_auth)):
    """Delete a conversation and all its messages."""
    try:
        db = get_db()
        deleted = db.delete_conversation(chat_id=chat_id, user_id=user_id)
        return {"success": deleted}
    except Exception as e:
        print(f"[ERROR] delete_conversation: {e}")
        return {"success": False}


# ================================================================
# ENDPOINTS - CHAT (WITH LANGGRAPH!)
# ================================================================

@app.post("/chat", response_model=ChatOut, tags=["Chat"])
async def chat(data: ChatIn, user_id: int = Depends(require_auth)):
    """
    Chat with NourishGraph assistant.
    
    Uses LANGGRAPH to process messages intelligently!
    
    Flow:
    1. Planner analyzes the question (Chain-of-Thought)
    2. Router selects the right agent
    3. Agent executes (Science/Nutrition/Profile/Chat)
    4. Reflection evaluates the response
    5. Synthesizer formats the final response
    """
    message = (data.message or "").strip()
    
    if not message:
        return ChatOut(response="The message is empty. 🙂", agent="NourishGraph")
    
    try:
        db = check_db()

        # Request-scoped context for tools (user scoping + write gating)
        try:
            from app.runtime.request_context import current_user_id, allow_writes, memory_manager as mm_var
            current_user_id.set(user_id)
            allow_writes.set(False)
        except Exception:
            mm_var = None

        # Initialize memory manager for pending confirmations (in-memory)
        mm = None
        if HAS_MEMORY and get_memory_manager:
            try:
                mm = get_memory_manager(user_id)
                if mm_var is not None:
                    mm_var.set(mm)
            except Exception:
                mm = None

        # ============================================================
        # CONFIRMATION GATE (explicit commits only)
        # ============================================================
        msg_lower = message.strip().lower()
        if msg_lower in {"confirm", "confirmar", "yes", "sim"} and mm is not None:
            # Commit pending meal
            pending_meal = mm.confirm_pending_meal()
            if pending_meal:
                try:
                    meal = db.log_meal(user_id=user_id, **pending_meal)
                    return ChatOut(
                        response=f"✅ Meal logged: {pending_meal.get('description', '')}",
                        agent="NourishGraph",
                        intent="meal_log",
                    )
                except ValueError as e:
                    # Food validation failed
                    return ChatOut(
                        response=f"❌ {str(e)}",
                        agent="NourishGraph",
                        intent="error",
                    )

            # Commit pending profile update/clear
            pending_profile = mm.confirm_pending_profile_update()
            if pending_profile:
                if pending_profile.get("clear"):
                    db.clear_profile(user_id=user_id)
                    return ChatOut(
                        response="✅ Profile cleared.",
                        agent="NourishGraph",
                        intent="profile_clear",
                        profile_updated=True,  # Signal frontend to reload profile
                    )
                if pending_profile.get("clear_meals"):
                    deleted = db.clear_meals(user_id=user_id)
                    return ChatOut(
                        response=f"✅ Meal history cleared ({deleted} meals deleted).",
                        agent="NourishGraph",
                        intent="meals_clear",
                    )
                updates = pending_profile.get("updates") or {}
                if updates:
                    # Normalize restrictions and preferences to lists
                    if "restrictions" in updates and isinstance(updates["restrictions"], str):
                        updates["restrictions"] = [updates["restrictions"]] if updates["restrictions"] else None
                    if "preferences" in updates and isinstance(updates["preferences"], str):
                        updates["preferences"] = [updates["preferences"]] if updates["preferences"] else None
                    
                    # Normalize gender to single char (DB expects CHAR(1))
                    if "gender" in updates:
                        g = str(updates["gender"]).strip().lower()
                        if g in ("male", "masculino", "homem", "m"):
                            updates["gender"] = "M"
                        elif g in ("female", "feminino", "mulher", "f"):
                            updates["gender"] = "F"
                    
                    db.save_profile(user_id=user_id, **updates)
                    
                    # Build a summary of what was updated
                    updated_fields = []
                    if updates.get("name"):
                        updated_fields.append(f"Name: {updates['name']}")
                    if updates.get("age"):
                        updated_fields.append(f"Age: {updates['age']}")
                    if updates.get("weight"):
                        updated_fields.append(f"Weight: {updates['weight']} kg")
                    if updates.get("height"):
                        updated_fields.append(f"Height: {updates['height']} cm")
                    if updates.get("gender"):
                        updated_fields.append(f"Gender: {'Female' if updates['gender'] == 'F' else 'Male'}")
                    if updates.get("goal"):
                        updated_fields.append(f"Goal: {updates['goal']}")
                    if updates.get("activity"):
                        updated_fields.append(f"Activity: {updates['activity']}")
                    
                    summary = "\n".join([f"• {f}" for f in updated_fields]) if updated_fields else "Profile data"
                    
                    return ChatOut(
                        response=f"Profile updated successfully.\n\n{summary}",
                        agent="NourishGraph",
                        intent="profile_update",
                        profile_updated=True,
                    )

            return ChatOut(
                response="Nothing pending to confirm.",
                agent="NourishGraph",
                intent="confirmation",
            )

        if msg_lower in {"cancel", "cancelar", "no", "não", "nao"} and mm is not None:
            meal = mm.confirm_pending_meal()  # clears
            prof = mm.confirm_pending_profile_update()  # clears
            if meal or prof:
                return ChatOut(
                    response="✅ Pending action discarded.",
                    agent="NourishGraph",
                    intent="confirmation",
                )
            return ChatOut(
                response="Nothing pending to cancel.",
                agent="NourishGraph",
                intent="confirmation",
            )
        
        # ============================================
        # DIRECT PROFILE UPDATE DETECTION
        # Detect ALL profile fields in a single message
        # SKIP if user is asking for meal suggestions!
        # ============================================
        import re
        
        # Check if this is a meal/food suggestion request
        # If so, don't intercept as profile update
        meal_suggestion_keywords = [
            'suggest', 'recommend', 'breakfast', 'lunch', 'dinner', 'snack',
            'meal', 'recipe', 'what to eat', 'food idea', 'give me a', 'make me a',
            'healthy meal', 'plan my', 'eating plan'
        ]
        is_meal_request = any(kw in msg_lower for kw in meal_suggestion_keywords)
        
        # Only do direct profile detection if NOT a meal request
        if not is_meal_request:
            # Collect ALL profile updates from the message
            profile_updates = {}
        
            # Extract GOAL: "my goal is to gain muscle", "I want to lose weight", "change goal to maintain"
            goal_patterns = [
                r'(?:my\s+)?goal\s+(?:is\s+)?(?:to\s+)?(lose\s*weight|gain\s*muscle|gain\s*weight|maintain(?:ing)?(?:\s*weight)?)',
                r'(?:i\s+)?want\s+to\s+(lose\s*weight|gain\s*muscle|gain\s*weight|maintain)',
                r'(?:change|update|set)\s+(?:my\s+)?goal\s+to\s+(lose\s*weight|gain\s*muscle|gain\s*weight|maintain(?:ing)?(?:\s*weight)?)',
            ]
            for pattern in goal_patterns:
                goal_match = re.search(pattern, msg_lower)
                if goal_match:
                    goal_value = goal_match.group(1).lower()
                    if "lose" in goal_value:
                        profile_updates["goal"] = "lose_weight"
                    elif "gain" in goal_value and "muscle" in goal_value:
                        profile_updates["goal"] = "gain_muscle"
                    elif "gain" in goal_value:
                        profile_updates["goal"] = "gain_weight"
                    else:
                        profile_updates["goal"] = "maintain"
                    break
            
            # Extract WEIGHT: "60kg", "weigh 60", "60 kg", "peso 60", "weight to 59"
            weight_patterns = [
                r'(?:weigh|peso|weight(?:\s+(?:to|is))?)\s*(\d+(?:\.\d+)?)\s*(?:kg|kilos?)?',
                r'(\d+(?:\.\d+)?)\s*kg\b',
                r'(?:my\s+)?weight\s+(?:to|is)\s*(\d+(?:\.\d+)?)',
            ]
            for pattern in weight_patterns:
                weight_match = re.search(pattern, msg_lower)
                if weight_match:
                    weight_val = float(weight_match.group(1))
                    if 20 <= weight_val <= 500:
                        profile_updates["weight"] = weight_val
                    break
            
            # Extract AGE: "I'm 28", "28 years old", "age 28", "tenho 28 anos"
            age_match = re.search(r"(?:i'?m|i am|age|tenho)\s*(\d{1,3})(?:\s*(?:years?\s*old|anos))?|(\d{1,3})\s*(?:years?\s*old|anos)", msg_lower)
            if age_match:
                age_val = int(age_match.group(1) or age_match.group(2))
                if 1 <= age_val <= 120:
                    profile_updates["age"] = age_val
            
            # Extract HEIGHT: "1.80m", "180cm", "1m80", "altura 180"
            height_match = re.search(r"(\d{1,2})[.,](\d{2})\s*m(?:eters?)?|(\d{2,3})\s*cm|(\d{1,2})\s*m\s*(\d{2})|(?:height|altura)\s*(\d{2,3})", msg_lower)
            if height_match:
                if height_match.group(1) and height_match.group(2):
                    height_val = int(height_match.group(1)) * 100 + int(height_match.group(2))
                elif height_match.group(3):
                    height_val = int(height_match.group(3))
                elif height_match.group(4) and height_match.group(5):
                    height_val = int(height_match.group(4)) * 100 + int(height_match.group(5))
                elif height_match.group(6):
                    height_val = int(height_match.group(6))
                else:
                    height_val = None
                if height_val and 50 <= height_val <= 280:
                    profile_updates["height"] = height_val
            
            # Extract GENDER: "female", "male", "woman", "man"
            if re.search(r'\b(female|woman|mulher|feminino)\b', msg_lower):
                profile_updates["gender"] = 'F'
            elif re.search(r'\b(male|man|homem|masculino)\b', msg_lower):
                profile_updates["gender"] = 'M'
            
            # Extract DIET: vegetarian, vegan, keto, etc.
            diet_match = re.search(r"(?:i'?m|i am|my diet is|i follow(?: a)?)\s+(vegetarian|vegan|mediterranean|keto|ketogenic|paleo|pescatarian|carnivore|ancestral|gluten[- ]?free|dairy[- ]?free|low[- ]?carb)(?:\s+diet)?", msg_lower)
            if diet_match:
                profile_updates["restrictions"] = [diet_match.group(1).strip()]
            
            # If we found ANY profile updates, create pending update with ALL fields
            if profile_updates and mm is not None:
                mm.confirm_pending_profile_update()  # Clear old pending
                mm.set_pending_profile_update({"updates": profile_updates, "created_at": datetime.now().isoformat()})
                
                # Build summary of ALL updates
                summary_parts = []
                if profile_updates.get("goal"):
                    goal_display = {
                        "lose_weight": "Lose weight", 
                        "gain_muscle": "Gain muscle", 
                        "gain_weight": "Gain weight", 
                        "maintain": "Maintain weight"
                    }.get(profile_updates["goal"], profile_updates["goal"])
                    summary_parts.append(f"• **Goal**: {goal_display}")
                if profile_updates.get("weight"):
                    summary_parts.append(f"• **Weight**: {profile_updates['weight']} kg")
                if profile_updates.get("age"):
                    summary_parts.append(f"• **Age**: {profile_updates['age']} years")
                if profile_updates.get("height"):
                    summary_parts.append(f"• **Height**: {profile_updates['height']} cm")
                if profile_updates.get("gender"):
                    summary_parts.append(f"• **Gender**: {'Female' if profile_updates['gender'] == 'F' else 'Male'}")
                if profile_updates.get("restrictions"):
                    summary_parts.append(f"• **Diet**: {profile_updates['restrictions'][0].title()}")
                
                summary = "\n".join(summary_parts)
                
                return ChatOut(
                    response=f"**Profile Update**\n\nProposed changes:\n{summary}\n\nReply **CONFIRM** to save, or **CANCEL** to discard.",
                    agent="ProfileAgent",
                    intent="profile_update",
                    requires_confirmation=True,
                    pending_action={"action": "profile_update", "updates": profile_updates, "created_at": datetime.now().isoformat()},
                )
        
        # ============================================
        # SAFETY CHECK (Guardrails - TA5)
        # ============================================
        safety_result = None
        if HAS_SAFETY:
            safety_result = check_input_safety(message)
            
            # Log safety event
            action = "allowed"
            if safety_result.level == SafetyLevel.CRITICAL:
                action = "blocked"
            elif safety_result.requires_disclaimer:
                action = "disclaimer_added"
            elif safety_result.requires_escalation:
                action = "escalated"
            
            record_safety_event(safety_result, message, action)
            
            # Handle CRITICAL level (medical emergency, etc.)
            if safety_result.level == SafetyLevel.CRITICAL:
                print(f"🚨 CRITICAL safety flag: {safety_result.flags}")
                return ChatOut(
                    response=safety_result.redirect_message or "I cannot help with this. Please seek professional help.",
                    agent="NourishGraph",
                    intent="safety_redirect",
                    safety_level=safety_result.level.value,
                    safety_flags=safety_result.flags,
                )
            
            # Log warnings
            if safety_result.level == SafetyLevel.WARNING:
                print(f"[SAFETY] Warning flags: {safety_result.flags}")
        
        # ============================================
        # MEDICAL QUERY BLOCKING (FA6 - Safety Boundaries)
        # Block medication dosage queries BEFORE LangGraph
        # ============================================
        import re
        MEDICAL_BLOCK_PATTERNS = [
            r'\b(dosage|dose|how much|how many)\s+(of\s+)?(insulin|metformin|ozempic|wegovy|medication|medicine|drug|pills?)\b',
            r'\b(insulin|metformin|ozempic|wegovy|semaglutide|tirzepatide|mounjaro)\s+(dosage|dose|amount|units?|injection)\b',
            r'\b(correct|right|proper|recommended|safe)\s+(dosage|dose|amount)\s+(of\s+)?(insulin|medication|medicine)\b',
            r'\b(prescri(be|ption)|medication|medicine|drug)\s+(for|to treat)\b',
            r'\b(blood sugar|blood glucose|a1c|hba1c)\s+(level|target|range|control|management)\b',
            r'\b(manage|control|lower|reduce)\s+(my\s+)?(blood sugar|blood glucose|diabetes)\b',
            r'\b(diagnos|treat|cure|medication for|medicine for)\s+(diabetes|cancer|heart disease|hypertension)\b',
            r'\b(should i (take|stop|change))\s+(my\s+)?(medication|medicine|insulin|metformin)\b',
            # Supplement/vitamin + symptom (medical self-treatment)
            r'\bshould i take\b.*\b(supplement|vitamin)\b.*\b(headache|migraine|pain|ache|dizz|nausea|fatigue|tired|insomnia|anxiety|depression)\b',
            r'\bshould i take\b.*\b(headache|migraine|pain|ache|dizz|nausea|fatigue|tired|insomnia|anxiety|depression)\b.*\b(supplement|vitamin)\b',
        ]
        
        msg_lower_check = message.lower().strip()
        for pattern in MEDICAL_BLOCK_PATTERNS:
            if re.search(pattern, msg_lower_check, re.IGNORECASE):
                print(f"🚫 MEDICAL BLOCKED: {message[:50]}...")
                medical_response = """⚠️ **Important Health Notice**

I understand you're asking about medication, dosage, or medical treatment. This is outside my scope of practice as a nutrition guidance assistant.

**I cannot provide advice on:**
- Medication dosages (including insulin)
- Blood sugar/glucose management
- Medical treatments or prescriptions
- Adjusting or stopping medications

**Please consult:**
- Your doctor or endocrinologist
- A registered pharmacist
- Your healthcare team

**What I CAN help with:**
- General nutrition information
- Healthy eating patterns
- Meal planning (without medical modifications)
- Scientific research about nutrients

Is there a nutrition-related question I can help you with instead?"""
                
                return ChatOut(
                    response=medical_response,
                    agent="NourishGraph",
                    intent="medical_blocked",
                    safety_level="blocked",
                    safety_flags=["medical_query"],
                )
        
        # Save user message (scoped)
        chat_id = data.chat_id
        db.save_chat_message(role="user", content=message, chat_id=chat_id, user_id=user_id)
        
        # ============================================
        # USE LANGGRAPH IF AVAILABLE
        # ============================================
        if HAS_LANGGRAPH and run_agent:
            try:
                # Get profile for context - prefer frontend profile if available
                if data.profile:
                    user_profile = data.profile
                else:
                    profile = db.get_profile(user_id=user_id)
                    user_profile = profile.to_dict() if profile else {}
                
                # Get recent chat history for context (last 10 messages)
                raw_history = db.get_chat_history(limit=10, user_id=user_id)
                # Reverse to get chronological order (oldest first)
                # and format for the agent
                chat_history = [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in reversed(raw_history)
                ]
                print(f"   📜 Chat history: {len(chat_history)} messages")
                
                # Choose between Supervisor mode and standard routing
                if USE_SUPERVISOR and run_supervisor:
                    print(f"🎯 Supervisor processing: {message[:50]}...")
                    result = run_supervisor(message, user_profile=user_profile, chat_history=chat_history)
                else:
                    print(f"🤖 LangGraph processing: {message[:50]}...")
                    result = run_agent(message, user_profile=user_profile, chat_history=chat_history, user_id=user_id)
                
                response_text = result.get("final_response", "Could not process the message.")
                
                # Clean LLM response - remove fake links and artifacts
                response_text = clean_llm_response(response_text)
                
                intent = result.get("intent", "chat")
                tools_used = result.get("tools_used", [])
                
                # Extract sources from context (for science queries)
                # Only include papers that were actually mentioned in the response
                sources = extract_sources_from_result(result, response_text)

                # If tools proposed a write, expose it via output contract
                requires_confirmation = False
                pending = None
                if mm is not None:
                    pending_meal = mm.get_pending_meal()
                    pending_profile = mm.get_pending_profile_update()
                    if pending_meal:
                        requires_confirmation = True
                        pending = {
                            "type": "meal_log",
                            "proposed": pending_meal,
                            "confirm_text": "CONFIRM",
                            "cancel_text": "CANCEL",
                        }
                    elif pending_profile:
                        requires_confirmation = True
                        pending_type = "profile_update"
                        if pending_profile.get("clear"):
                            pending_type = "profile_clear"
                        elif pending_profile.get("clear_meals"):
                            pending_type = "meals_clear"
                        pending = {
                            "type": pending_type,
                            "proposed": pending_profile,
                            "confirm_text": "CONFIRM",
                            "cancel_text": "CANCEL",
                        }
                
                # Add safety disclaimer if needed (TA5)
                if HAS_SAFETY and safety_result and safety_result.requires_disclaimer:
                    response_text = add_safety_disclaimer(response_text, safety_result)
                
                # Extract evidence level and confidence (for science queries)
                evidence_level = result.get("evidence_level") or result.get("context", {}).get("evidence_level")
                confidence_score = result.get("confidence", 0.7)
                
                # Infer evidence level from sources if not explicitly set
                if not evidence_level and sources and len(sources) > 0:
                    # A: 3+ papers, B: 2 papers, C: 1 paper, D: 0 papers
                    num_sources = len(sources)
                    if num_sources >= 3:
                        evidence_level = "A"
                    elif num_sources == 2:
                        evidence_level = "B"
                    elif num_sources == 1:
                        evidence_level = "C"
                
                # Save response
                db.save_chat_message(
                    role="assistant",
                    content=response_text,
                    intent=intent,
                    tools_used=tools_used,
                    chat_id=chat_id,
                    user_id=user_id,
                )
                
                # Check if profile was updated (signal frontend to reload)
                profile_was_updated = (
                    intent == "profile" and 
                    not requires_confirmation and
                    any(t in tools_used for t in ["save_user_profile", "update_user_profile"])
                )
                
                # Extract nutritional calculations for visual display
                # Skip calculations when safety flags are present (irrelevant to safety queries)
                calculations = None
                if not (safety_result and safety_result.flags):
                    calculations = extract_calculations_from_profile(user_profile, intent, message)
                
                return ChatOut(
                    response=response_text,
                    agent="NourishGraph",
                    intent=intent,
                    tools_used=tools_used,
                    sources=sources if sources else None,
                    evidence_level=evidence_level,
                    confidence=confidence_score if intent == "science" else None,
                    requires_confirmation=requires_confirmation,
                    pending=pending,
                    safety_level=safety_result.level.value if safety_result and intent != 'medical_blocked' else None,
                    safety_flags=safety_result.flags if safety_result and safety_result.flags and intent != 'medical_blocked' else None,
                    profile_updated=profile_was_updated,
                    calculations=calculations,
                )
                
            except Exception as e:
                print(f"[ERROR] LangGraph: {e}")
                traceback.print_exc()
                raise HTTPException(status_code=500, detail="LangGraph processing failed")
        
        # ============================================
        # SIMPLE MODE (FALLBACK)
        # ============================================
        else:
            raise HTTPException(status_code=503, detail="LangGraph not available")
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        return ChatOut(response="Error processing. Please try again.", agent="NourishGraph")


# ================================================================
# ENDPOINTS - STREAMING CHAT (SSE)
# ================================================================

async def stream_chat_response(message: str, user_id: int, user_profile: dict = None, chat_id: str = None):
    """
    Generator for Server-Sent Events (SSE) streaming.
    
    Simulates word-by-word streaming for better UX.
    """
    try:
        db = check_db()
        
        # Initialize memory manager for confirmation flow
        mm = None
        if HAS_MEMORY and get_memory_manager:
            try:
                mm = get_memory_manager(user_id)
            except Exception:
                mm = None
        
        # Request-scoped context for tools (user scoping + write gating)
        try:
            from app.runtime.request_context import current_user_id, allow_writes, memory_manager as mm_var
            current_user_id.set(user_id)
            allow_writes.set(False)
            if mm is not None:
                mm_var.set(mm)
        except Exception:
            pass
        
        # ============================================================
        # CONFIRMATION GATE (explicit commits only)
        # ============================================================
        msg_lower = message.strip().lower()
        
        if msg_lower in {"confirm", "confirmar", "yes", "sim"} and mm is not None:
            # Commit pending meal
            pending_meal = mm.confirm_pending_meal()
            if pending_meal:
                try:
                    meal = db.log_meal(user_id=user_id, **pending_meal)
                    response = f"✅ Meal logged: {pending_meal.get('description', '')}"
                    yield f"event: start\ndata: {json.dumps({'status': 'processing'})}\n\n"
                    yield f"event: intent\ndata: {json.dumps({'intent': 'meal_log'})}\n\n"
                    yield f"event: chunk\ndata: {json.dumps({'text': response})}\n\n"
                    yield f"event: done\ndata: {json.dumps({'response': response, 'intent': 'meal_log', 'profile_updated': False})}\n\n"
                    return
                except ValueError as e:
                    # Food validation failed
                    response = f"❌ {str(e)}"
                    yield f"event: start\ndata: {json.dumps({'status': 'processing'})}\n\n"
                    yield f"event: intent\ndata: {json.dumps({'intent': 'error'})}\n\n"
                    yield f"event: chunk\ndata: {json.dumps({'text': response})}\n\n"
                    yield f"event: done\ndata: {json.dumps({'response': response, 'intent': 'error', 'profile_updated': False})}\n\n"
                    return

            # Commit pending profile update/clear
            pending_profile = mm.confirm_pending_profile_update()
            if pending_profile:
                if pending_profile.get("clear"):
                    db.clear_profile(user_id=user_id)
                    response = "Profile cleared successfully."
                    yield f"event: start\ndata: {json.dumps({'status': 'processing'})}\n\n"
                    yield f"event: intent\ndata: {json.dumps({'intent': 'profile_clear'})}\n\n"
                    yield f"event: chunk\ndata: {json.dumps({'text': response})}\n\n"
                    yield f"event: done\ndata: {json.dumps({'response': response, 'intent': 'profile_clear', 'profile_updated': True})}\n\n"
                    return
                    
                if pending_profile.get("clear_meals"):
                    deleted = db.clear_meals(user_id=user_id)
                    response = f"Meal history cleared ({deleted} meals deleted)."
                    yield f"event: start\ndata: {json.dumps({'status': 'processing'})}\n\n"
                    yield f"event: intent\ndata: {json.dumps({'intent': 'meals_clear'})}\n\n"
                    yield f"event: chunk\ndata: {json.dumps({'text': response})}\n\n"
                    yield f"event: done\ndata: {json.dumps({'response': response, 'intent': 'meals_clear', 'profile_updated': False})}\n\n"
                    return
                    
                updates = pending_profile.get("updates") or {}
                if updates:
                    # Normalize restrictions and preferences to lists
                    if "restrictions" in updates and isinstance(updates["restrictions"], str):
                        updates["restrictions"] = [updates["restrictions"]] if updates["restrictions"] else None
                    if "preferences" in updates and isinstance(updates["preferences"], str):
                        updates["preferences"] = [updates["preferences"]] if updates["preferences"] else None
                    
                    # Normalize gender to single char (DB expects CHAR(1))
                    if "gender" in updates:
                        g = str(updates["gender"]).strip().lower()
                        if g in ("male", "masculino", "homem", "m"):
                            updates["gender"] = "M"
                        elif g in ("female", "feminino", "mulher", "f"):
                            updates["gender"] = "F"
                    
                    db.save_profile(user_id=user_id, **updates)
                    
                    # Build summary of what was updated
                    updated_fields = []
                    if updates.get("name"):
                        updated_fields.append(f"Name: {updates['name']}")
                    if updates.get("age"):
                        updated_fields.append(f"Age: {updates['age']} years")
                    if updates.get("weight"):
                        updated_fields.append(f"Weight: {updates['weight']} kg")
                    if updates.get("height"):
                        updated_fields.append(f"Height: {updates['height']} cm")
                    if updates.get("gender"):
                        updated_fields.append(f"Gender: {'Female' if updates['gender'] == 'F' else 'Male'}")
                    if updates.get("goal"):
                        updated_fields.append(f"Goal: {updates['goal']}")
                    if updates.get("activity"):
                        updated_fields.append(f"Activity: {updates['activity']}")
                    
                    summary = "\n".join([f"• {f}" for f in updated_fields]) if updated_fields else "Profile data"
                    response = f"Profile updated successfully.\n\n{summary}"
                    
                    profile_agent_info = {"type": "profile", "name": "Profile Manager", "icon": "👤", "description": "Manages and updates your personal health profile"}
                    yield f"event: start\ndata: {json.dumps({'status': 'processing'})}\n\n"
                    yield f"event: agent\ndata: {json.dumps({'agent': profile_agent_info, 'confidence': 1.0, 'tools_used': ['profile_update']})}\n\n"
                    yield f"event: intent\ndata: {json.dumps({'intent': 'profile_update'})}\n\n"
                    yield f"event: chunk\ndata: {json.dumps({'text': response})}\n\n"
                    yield f"event: done\ndata: {json.dumps({'response': response, 'intent': 'profile_update', 'profile_updated': True, 'agent': profile_agent_info})}\n\n"
                    return

            # Nothing pending
            response = "Nothing pending to confirm."
            yield f"event: start\ndata: {json.dumps({'status': 'processing'})}\n\n"
            yield f"event: intent\ndata: {json.dumps({'intent': 'confirmation'})}\n\n"
            yield f"event: chunk\ndata: {json.dumps({'text': response})}\n\n"
            yield f"event: done\ndata: {json.dumps({'response': response, 'intent': 'confirmation'})}\n\n"
            return

        if msg_lower in {"cancel", "cancelar", "no", "não", "nao"} and mm is not None:
            meal = mm.confirm_pending_meal()  # clears
            prof = mm.confirm_pending_profile_update()  # clears
            if meal or prof:
                response = "Pending action discarded."
            else:
                response = "Nothing pending to cancel."
            yield f"event: start\ndata: {json.dumps({'status': 'processing'})}\n\n"
            yield f"event: intent\ndata: {json.dumps({'intent': 'confirmation'})}\n\n"
            yield f"event: chunk\ndata: {json.dumps({'text': response})}\n\n"
            yield f"event: done\ndata: {json.dumps({'response': response, 'intent': 'confirmation'})}\n\n"
            return
        
        # ============================================
        # DIRECT PROFILE DATA EXTRACTION (STREAMING)
        # Extract age, weight, height, gender from natural language
        # ============================================
        import re
        profile_updates = {}
        
        # Extract age
        age_match = re.search(r"(?:i'?m|i am|age|tenho)\s*(\d{1,3})(?:\s*(?:years?\s*old|anos))?|(\d{1,3})\s*(?:years?\s*old|anos)", msg_lower)
        if age_match:
            age_val = int(age_match.group(1) or age_match.group(2))
            if 1 <= age_val <= 120:
                profile_updates["age"] = age_val
        
        # Extract weight
        weight_match = re.search(r"(?:weigh|peso|weight)\s*(\d+(?:\.\d+)?)\s*(?:kg|kilos?)?|(\d+(?:\.\d+)?)\s*kg", msg_lower)
        if weight_match:
            weight_val = float(weight_match.group(1) or weight_match.group(2))
            if 20 <= weight_val <= 500:
                profile_updates["weight"] = weight_val
        
        # Extract height
        height_match = re.search(r"(\d{1,2})[.,](\d{2})\s*m(?:eters?)?|(\d{2,3})\s*cm|(\d{1,2})\s*m\s*(\d{2})|(?:height|altura)\s*(\d{2,3})", msg_lower)
        if height_match:
            if height_match.group(1) and height_match.group(2):
                height_val = int(height_match.group(1)) * 100 + int(height_match.group(2))
            elif height_match.group(3):
                height_val = int(height_match.group(3))
            elif height_match.group(4) and height_match.group(5):
                height_val = int(height_match.group(4)) * 100 + int(height_match.group(5))
            elif height_match.group(6):
                height_val = int(height_match.group(6))
            else:
                height_val = None
            if height_val and 50 <= height_val <= 280:
                profile_updates["height"] = height_val
        
        # Extract gender
        if re.search(r'\b(female|woman|mulher|feminino)\b', msg_lower):
            profile_updates["gender"] = 'F'
        elif re.search(r'\b(male|man|homem|masculino)\b', msg_lower):
            profile_updates["gender"] = 'M'
        
        # If we extracted profile data, create pending update
        if profile_updates and mm is not None:
            mm.confirm_pending_profile_update()  # Clear old
            mm.set_pending_profile_update({"updates": profile_updates, "created_at": datetime.now().isoformat()})
            
            summary_parts = []
            if profile_updates.get("age"):
                summary_parts.append(f"• **Age**: {profile_updates['age']} years")
            if profile_updates.get("weight"):
                summary_parts.append(f"• **Weight**: {profile_updates['weight']} kg")
            if profile_updates.get("height"):
                summary_parts.append(f"• **Height**: {profile_updates['height']} cm")
            if profile_updates.get("gender"):
                summary_parts.append(f"• **Gender**: {'Female' if profile_updates['gender'] == 'F' else 'Male'}")
            
            summary = "\n".join(summary_parts)
            response = f"**Profile Update**\n\nProposed changes:\n{summary}\n\nReply **CONFIRM** to save or **CANCEL** to discard."
            
            profile_agent_info = {"type": "profile", "name": "Profile Manager", "icon": "👤", "description": "Manages and updates your personal health profile"}
            yield f"event: start\ndata: {json.dumps({'status': 'processing'})}\n\n"
            yield f"event: agent\ndata: {json.dumps({'agent': profile_agent_info, 'confidence': 1.0, 'tools_used': ['profile_update']})}\n\n"
            yield f"event: intent\ndata: {json.dumps({'intent': 'profile_update'})}\n\n"
            yield f"event: chunk\ndata: {json.dumps({'text': response})}\n\n"
            yield f"event: done\ndata: {json.dumps({'response': response, 'intent': 'profile_update', 'requires_confirmation': True, 'pending': {'type': 'profile_update', 'proposed': profile_updates}, 'agent': profile_agent_info})}\n\n"
            return
        
        # Safety check
        safety_result = None
        if HAS_SAFETY:
            safety_result = check_input_safety(message)
            if safety_result.level == SafetyLevel.CRITICAL:
                yield f"event: error\ndata: {json.dumps({'message': safety_result.redirect_message})}\n\n"
                return
        
        # ============================================
        # MEDICAL QUERY BLOCKING (FA6 - Safety Boundaries)
        # Block medication dosage queries BEFORE LangGraph
        # ============================================
        MEDICAL_BLOCK_PATTERNS = [
            r'\b(dosage|dose|how much|how many)\s+(of\s+)?(insulin|metformin|ozempic|wegovy|medication|medicine|drug|pills?)\b',
            r'\b(insulin|metformin|ozempic|wegovy|semaglutide|tirzepatide|mounjaro)\s+(dosage|dose|amount|units?|injection)\b',
            r'\b(correct|right|proper|recommended|safe)\s+(dosage|dose|amount)\s+(of\s+)?(insulin|medication|medicine)\b',
            r'\b(prescri(be|ption)|medication|medicine|drug)\s+(for|to treat)\b',
            r'\b(blood sugar|blood glucose|a1c|hba1c)\s+(level|target|range|control|management)\b',
            r'\b(manage|control|lower|reduce)\s+(my\s+)?(blood sugar|blood glucose|diabetes)\b',
            r'\b(diagnos|treat|cure|medication for|medicine for)\s+(diabetes|cancer|heart disease|hypertension)\b',
            r'\b(should i (take|stop|change))\s+(my\s+)?(medication|medicine|insulin|metformin)\b',
            # Supplement/vitamin + symptom (medical self-treatment)
            r'\bshould i take\b.*\b(supplement|vitamin)\b.*\b(headache|migraine|pain|ache|dizz|nausea|fatigue|tired|insomnia|anxiety|depression)\b',
            r'\bshould i take\b.*\b(headache|migraine|pain|ache|dizz|nausea|fatigue|tired|insomnia|anxiety|depression)\b.*\b(supplement|vitamin)\b',
        ]
        
        for pattern in MEDICAL_BLOCK_PATTERNS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                print(f"🚫 MEDICAL BLOCKED (stream): {message[:50]}...")
                medical_response = """⚠️ **Important Health Notice**

I understand you're asking about medication, dosage, or medical treatment. This is outside my scope of practice as a nutrition guidance assistant.

**I cannot provide advice on:**
- Medication dosages (including insulin)
- Blood sugar/glucose management
- Medical treatments or prescriptions
- Adjusting or stopping medications

**Please consult:**
- Your doctor or endocrinologist
- A registered pharmacist
- Your healthcare team

**What I CAN help with:**
- General nutrition information
- Healthy eating patterns
- Meal planning (without medical modifications)
- Scientific research about nutrients

Is there a nutrition-related question I can help you with instead?"""
                
                yield f"event: start\ndata: {json.dumps({'status': 'processing'})}\n\n"
                yield f"event: intent\ndata: {json.dumps({'intent': 'medical_blocked'})}\n\n"
                yield f"event: chunk\ndata: {json.dumps({'text': medical_response})}\n\n"
                yield f"event: done\ndata: {json.dumps({'response': medical_response, 'intent': 'medical_blocked', 'safety_level': 'blocked'})}\n\n"
                return
        
        # Send start event
        yield f"event: start\ndata: {json.dumps({'status': 'processing'})}\n\n"
        
        # Get chat history
        raw_history = db.get_chat_history(limit=10, user_id=user_id)
        chat_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in reversed(raw_history)
        ]
        
        # Process with LangGraph (non-streaming, then simulate streaming)
        from app.graph.graph import run_agent
        result = run_agent(message, user_profile, chat_history, user_id=user_id)
        
        intent = result.get("intent", "chat")
        final_response = result.get("final_response", "")
        confidence = result.get("confidence", 0.85)
        tools_used = result.get("tools_used", [])
        
        # Get context details for transparency
        context = result.get("context", {})
        reasoning_steps = context.get("reasoning_steps", [])
        
        # Map intent to friendly agent name
        agent_names = {
            "science": {"type": "science", "name": "Science Expert", "icon": "🧬", "description": "Searches scientific literature for evidence-based answers"},
            "nutrition": {"type": "nutrition", "name": "Nutrition Expert", "icon": "🥗", "description": "Calculates your nutritional needs based on your profile"},
            "profile": {"type": "profile", "name": "Profile Manager", "icon": "👤", "description": "Manages and updates your personal health profile"},
            "meal_planner": {"type": "meal", "name": "Meal Planner", "icon": "🍽️", "description": "Creates personalized meal plans based on your goals"},
            "chat": {"type": "chat", "name": "Health Assistant", "icon": "💬", "description": "Provides general nutrition guidance and wellness tips"},
        }
        agent_info = agent_names.get(intent, agent_names["chat"])
        
        # Check if profile agent set a pending update (for CONFIRM flow)
        requires_confirmation = False
        pending = None
        if mm is not None and intent == "profile":
            pending_profile = mm.get_pending_profile_update()
            if pending_profile:
                requires_confirmation = True
                # Flatten: extract 'updates' dict so frontend sees {weight: 65} not {updates: {weight: 65}}
                proposed = pending_profile.get("updates", pending_profile) if isinstance(pending_profile, dict) else pending_profile
                pending = {
                    "type": "profile_update",
                    "proposed": proposed,
                }
        
        # Send agent info (for transparency UI)
        yield f"event: agent\ndata: {json.dumps({'agent': agent_info, 'confidence': confidence, 'tools_used': tools_used})}\n\n"
        
        # Send intent
        yield f"event: intent\ndata: {json.dumps({'intent': intent})}\n\n"
        
        # Clean response
        final_response = clean_llm_response(final_response)
        
        # Add safety disclaimer if needed
        if HAS_SAFETY and safety_result and safety_result.requires_disclaimer:
            final_response = add_safety_disclaimer(final_response, safety_result)
        
        # Stream response word by word for smooth UX
        words = final_response.split(' ')
        chunk = ""
        for i, word in enumerate(words):
            chunk += word + ' '
            # Send every 3-5 words for smooth effect
            if len(chunk) > 30 or i == len(words) - 1:
                yield f"event: chunk\ndata: {json.dumps({'text': chunk})}\n\n"
                chunk = ""
                await asyncio.sleep(0.02)  # 20ms delay for smooth streaming
        
        # Extract and send sources
        sources = extract_sources_from_result(result, final_response)
        if sources:
            # Convert Pydantic models to dicts for JSON serialization
            sources_dicts = [s.model_dump() if hasattr(s, 'model_dump') else s.dict() for s in sources[:5]]
            yield f"event: sources\ndata: {json.dumps({'sources': sources_dicts})}\n\n"
        else:
            sources_dicts = []
        
        # Extract calculations for visual display
        # Skip calculations when safety flags are present (irrelevant to safety queries)
        calculations = None
        if not (HAS_SAFETY and safety_result and safety_result.flags):
            calculations = extract_calculations_from_profile(user_profile, intent, message)
        
        # Send done event with all transparency data
        done_data = {
            'response': final_response, 
            'intent': intent, 
            'sources': sources_dicts,
            'agent': agent_info,
            'confidence': confidence,
            'tools_used': tools_used,
        }
        if requires_confirmation:
            done_data['requires_confirmation'] = True
        if pending:
            done_data['pending'] = pending
        if calculations:
            done_data['calculations'] = calculations
        # Include safety fields so frontend can show SafetyMessage component
        # Skip for medical_blocked intent - the block response IS the safety message
        if HAS_SAFETY and safety_result and safety_result.flags and intent != 'medical_blocked':
            done_data['safety_level'] = safety_result.level.value
            done_data['safety_flags'] = safety_result.flags
        
        yield f"event: done\ndata: {json.dumps(done_data)}\n\n"
        
        # Save to chat history
        db.save_chat_message(role="user", content=message, chat_id=chat_id, user_id=user_id)
        db.save_chat_message(
            role="assistant",
            content=final_response,
            intent=intent,
            chat_id=chat_id,
            user_id=user_id,
        )
        
    except Exception as e:
        traceback.print_exc()
        yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"


@app.post("/chat/stream", tags=["Chat"])
async def chat_stream(data: ChatIn, user_id: int = Depends(require_auth)):
    """
    Streaming chat with NourishGraph assistant using Server-Sent Events (SSE).
    
    Returns a stream of events:
    - `start`: Processing started
    - `intent`: Detected intent (science, nutrition, profile, chat)
    - `tool`: Tool being executed
    - `chunk`: Response text chunk (for progressive display)
    - `sources`: Scientific sources (if applicable)
    - `done`: Final response complete
    - `error`: Error occurred
    
    Example client code (JavaScript):
    ```javascript
    const eventSource = new EventSource('/chat/stream', { method: 'POST', body: ... });
    eventSource.addEventListener('chunk', (e) => {
        const data = JSON.parse(e.data);
        appendText(data.text);
    });
    eventSource.addEventListener('done', (e) => {
        const data = JSON.parse(e.data);
        console.log('Complete:', data.response);
    });
    ```
    """
    message = (data.message or "").strip()
    
    if not message:
        return StreamingResponse(
            iter([f"event: error\ndata: {json.dumps({'message': 'Empty message'})}\n\n"]),
            media_type="text/event-stream"
        )
    
    user_profile = data.profile if data.profile else None
    
    chat_id = data.chat_id

    return StreamingResponse(
        stream_chat_response(message, user_id, user_profile, chat_id=chat_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

# ================================================================
# ENDPOINTS - PAPERS/PDFs
# ================================================================

@app.get("/papers/{filepath:path}", tags=["Papers"])
async def serve_paper(filepath: str):
    """
    Serve a PDF paper file.
    
    Args:
        filepath: Path to the PDF file (e.g., "papers_pdf/filename.pdf")
    
    Returns:
        PDF file
    """
    print(f"📄 Request for paper: {filepath}")
    
    # Handle different path formats
    if filepath.startswith("papers_pdf/"):
        # Full path provided
        pdf_path = ROOT_DIR / filepath
    else:
        # Just filename provided
        pdf_path = ROOT_DIR / "papers_pdf" / filepath
    
    print(f"📂 Looking for file at: {pdf_path}")
    
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"Paper not found: {filepath}")
    
    if not pdf_path.suffix.lower() == ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name
    )


@app.get("/papers", tags=["Papers"])
async def list_papers():
    """
    List all available papers with metadata.
    
    Returns:
        List of papers with title, authors, abstract, etc.
    """
    try:
        from app.rag_hybrid import _PAPERS
        
        papers = []
        for paper in _PAPERS:
            filename = paper.get("filename", "")
            papers.append({
                "id": paper.get("id"),
                "title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "year": paper.get("year"),
                "abstract": paper.get("abstract", "")[:300] + "..." if len(paper.get("abstract", "")) > 300 else paper.get("abstract", ""),
                "source": paper.get("source", ""),
                "path": f"papers_pdf/{filename}" if filename else None
            })
        
        return {"papers": papers, "total": len(papers)}
    
    except ImportError:
        return {"papers": [], "total": 0, "error": "RAG not available"}


@app.get("/download-paper/{filename:path}", tags=["Papers"])
async def download_paper(filename: str):
    """
    Download a PDF paper file by filename.
    
    Args:
        filename: Paper filename (e.g., "Omega-3_fatty_acids.pdf" or just the title)
    
    Returns:
        PDF file for download
    """
    import urllib.parse
    
    # Decode URL-encoded filename
    filename = urllib.parse.unquote(filename)
    
    # Try to find the paper
    papers_dir = ROOT_DIR / "papers" / "pdf"
    
    # Clean the filename - remove common prefixes/suffixes
    search_name = filename.replace(".pdf", "").replace(".txt", "")
    
    # Try direct match first
    pdf_path = papers_dir / f"{search_name}.pdf"
    if pdf_path.exists():
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=pdf_path.name,
            headers={"Content-Disposition": f'attachment; filename="{pdf_path.name}"'}
        )
    
    # Try fuzzy matching by searching for similar filenames
    if papers_dir.exists():
        search_lower = search_name.lower()
        for pdf_file in papers_dir.glob("*.pdf"):
            file_lower = pdf_file.stem.lower()
            # Check if search term is contained in filename or vice versa
            if search_lower in file_lower or file_lower in search_lower:
                return FileResponse(
                    path=str(pdf_file),
                    media_type="application/pdf",
                    filename=pdf_file.name,
                    headers={"Content-Disposition": f'attachment; filename="{pdf_file.name}"'}
                )
            # Also check first few words
            search_words = search_lower.split()[:3]
            file_words = file_lower.replace("_", " ").replace("-", " ").split()[:3]
            if search_words and file_words and search_words[0] == file_words[0]:
                return FileResponse(
                    path=str(pdf_file),
                    media_type="application/pdf",
                    filename=pdf_file.name,
                    headers={"Content-Disposition": f'attachment; filename="{pdf_file.name}"'}
                )
    
    # Try to find by paper metadata
    try:
        from app.rag_hybrid import _PAPERS
        for paper in _PAPERS:
            paper_filename = paper.get("filename", "")
            paper_title = paper.get("title", "")
            if (search_name.lower() in paper_filename.lower() or 
                search_name.lower() in paper_title.lower() or
                paper_filename.lower() in search_name.lower()):
                pdf_file = papers_dir / paper_filename
                if pdf_file.exists():
                    return FileResponse(
                        path=str(pdf_file),
                        media_type="application/pdf",
                        filename=pdf_file.name,
                        headers={"Content-Disposition": f'attachment; filename="{pdf_file.name}"'}
                    )
    except ImportError:
        pass
    
    raise HTTPException(status_code=404, detail=f"Paper not found: {filename}")


# ================================================================
# STATIC FILES (Frontend in Production)
# ================================================================

# Check if static directory exists (production build)
STATIC_DIR = ROOT_DIR / "static"
if STATIC_DIR.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")
    
    # Serve favicon
    @app.get("/favicon.svg", include_in_schema=False)
    async def serve_favicon():
        """Serve the favicon."""
        favicon_file = STATIC_DIR / "favicon.svg"
        if favicon_file.exists():
            return FileResponse(str(favicon_file), media_type="image/svg+xml")
        raise HTTPException(status_code=404, detail="Favicon not found")
    
    @app.get("/favicon.ico", include_in_schema=False)
    async def serve_favicon_ico():
        """Serve the favicon as ICO (redirect to SVG)."""
        favicon_file = STATIC_DIR / "favicon.svg"
        if favicon_file.exists():
            return FileResponse(str(favicon_file), media_type="image/svg+xml")
        raise HTTPException(status_code=404, detail="Favicon not found")
    
    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes."""
        # Only block paths that are actual backend API sub-routes (have a /)
        # or specific backend-only endpoints. Frontend routes like /chat, /profile
        # must be served index.html for SPA client-side routing to work.
        api_only_prefixes = ['api/', 'docs', 'redoc', 'openapi.json', 'db-diagnostics', 'health']
        # Also block exact POST-only endpoints accessed via GET with sub-paths
        api_sub_paths = ['chat/stream', 'chat/send', 'meals/', 'foods/', 'papers/', 'history/', 'stats/', 'auth/']
        
        if any(full_path == p or full_path.startswith(p) for p in api_only_prefixes):
            raise HTTPException(status_code=404, detail="Not found")
        if any(full_path.startswith(p) for p in api_sub_paths):
            raise HTTPException(status_code=404, detail="Not found")
        
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file), media_type="text/html")
        raise HTTPException(status_code=404, detail="Frontend not found")


# ================================================================
# MAIN
# ================================================================

@app.post("/memory/clear", tags=["Memory"])
async def clear_memory_endpoint(user_id: str, session_id: str = None):
    """Clear conversation memory for a user."""
    if HAS_MEMORY and get_memory_manager:
        try:
            clear_user_memory(int(user_id), session_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="user_id must be a valid integer")
        return {"status": "success", "message": "Memory cleared."}
    return {"status": "error", "message": "Memory manager not available."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=True)