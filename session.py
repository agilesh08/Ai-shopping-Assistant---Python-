"""
session.py — Per-user conversation state management.
Stores context in memory (dict keyed by chat_id).
"""

from typing import Dict, Any
import memory_engine

_sessions: Dict[int, Dict[str, Any]] = {}


def get_session(chat_id: int) -> Dict[str, Any]:
    """Get or create a session for a given chat_id."""
    if chat_id not in _sessions:
        mem_state = memory_engine.memory_engine.get_session(chat_id)
        _sessions[chat_id] = {
            "history": [],           # List of {role, content} for Llama context
            "mode": None,            # "shopping" | "styling" | None
            "awaiting_amazon": False, # True after styling advice, waiting for yes/no
            "styling_context": {},   # Accumulated styling preferences
            "shopping_state": mem_state,  # Memory Engine session state
        }
    return _sessions[chat_id]


def reset_session(chat_id: int) -> None:
    """Reset a user's session (e.g., on /start)."""
    _sessions[chat_id] = {
        "history": [],
        "mode": None,
        "awaiting_amazon": False,
        "styling_context": {},
        "shopping_state": None,
    }


def add_message(chat_id: int, role: str, content: str) -> None:
    """Append a message to the conversation history."""
    session = get_session(chat_id)
    session["history"].append({"role": role, "content": content})
    # Keep last 20 messages to avoid context overflow
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]
