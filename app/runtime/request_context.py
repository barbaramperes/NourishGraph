"""Request-scoped context for tools.

We use contextvars so LangChain tools (which are global callables) can still
access per-request state like the authenticated user_id and whether DB writes
are allowed.

This keeps write boundaries explicit and prevents accidental cross-user writes.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional, Any


current_user_id: ContextVar[Optional[int]] = ContextVar("current_user_id", default=None)
allow_writes: ContextVar[bool] = ContextVar("allow_writes", default=False)

# MemoryManager is optional to avoid import cycles at import time.
memory_manager: ContextVar[Optional[Any]] = ContextVar("memory_manager", default=None)


def get_user_id(default: int = 1) -> int:
    user_id = current_user_id.get()
    return int(user_id) if user_id is not None else default


def writes_allowed() -> bool:
    return bool(allow_writes.get())


def get_memory_manager() -> Optional[Any]:
    return memory_manager.get()
