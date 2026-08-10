"""
memory_engine.py — Conversation Memory & Preference Engine for Trevor AI Shopping Assistant.
Maintains per-user structured shopping session state across turns, merges incremental constraints,
resolves ordinal references ("1st one", "compare 1st and 3rd"), and manages session timeouts.

RULES:
- NEVER performs searches.
- NEVER ranks products.
- NEVER modifies retrieval, ranking, product intelligence, or decision engine logic.
- ONLY stores, updates, and retrieves structured shopping context per user.
"""

import time
import re
import logging

import category_manager

logger = logging.getLogger("trevor.memory_engine")

SESSION_TIMEOUT_SECONDS = 1800  # Default 30 minutes


def create_empty_session_state() -> dict:
    """Returns a fresh, empty structured shopping session dictionary."""
    return {
        "category": None,
        "brand": None,
        "model": None,
        "series": None,
        "budget": None,
        "color": None,
        "storage": None,
        "ram": None,
        "cpu": None,
        "gpu": None,
        "display": None,
        "battery": None,
        "gender": None,
        "size": None,
        "purpose": None,
        "marketplace": "amazon",
        "last_search_query": None,
        "last_search_results": [],
        "active_filters": {},
        "sort_preference": "relevance",
        "last_updated_timestamp": time.time(),
        "history": []
    }


class ConversationMemoryEngine:
    def __init__(self, timeout_seconds: int = SESSION_TIMEOUT_SECONDS):
        self.sessions = {}
        self.timeout_seconds = timeout_seconds

    def get_session(self, chat_id: int) -> dict:
        """
        Retrieves active session state for chat_id or initializes a new state if expired/absent.
        """
        now = time.time()
        session = self.sessions.get(chat_id)

        if not session or (now - session.get("last_updated_timestamp", 0) > self.timeout_seconds):
            logger.info(f"[MemoryEngine] Initializing fresh session for chat_id={chat_id}")
            session = create_empty_session_state()
            self.sessions[chat_id] = session
        else:
            session["last_updated_timestamp"] = now

        return session

    def update_session(self, chat_id: int, updates: dict) -> dict:
        """
        Merges incremental preference updates into active session state without overwriting untouched fields.
        Detects category transitions and resets context when switching root category families.
        """
        session = self.get_session(chat_id)

        if not isinstance(updates, dict):
            return session

        new_cat = updates.get("category") or ""
        new_ptype = updates.get("product_type") or ""

        if new_cat or new_ptype:
            session, _ = category_manager.handle_category_transition(session, new_cat, new_ptype)

        for k, v in updates.items():
            if v is not None and str(v).strip().lower() not in {"null", "none", ""}:
                session[k] = v

        session["last_updated_timestamp"] = time.time()
        logger.info(f"[MemoryEngine] Updated session for chat_id={chat_id} | Keys updated: {list(updates.keys())}")
        return session

    def save_search_results(self, chat_id: int, query: str, products: list[dict]):
        """
        Stores the last search query and returned product candidates in session state.
        """
        session = self.get_session(chat_id)
        session["last_search_query"] = query
        session["last_search_results"] = products or []
        session["last_updated_timestamp"] = time.time()
        logger.info(f"[MemoryEngine] Saved {len(products or [])} search results for chat_id={chat_id}")

    def resolve_product_reference(self, chat_id: int, text: str) -> list[dict]:
        """
        Resolves conversational ordinal references like 'first product', '2nd one', 'compare 1st and 3rd'.
        Returns list of matching product dicts from last_search_results.
        """
        session = self.get_session(chat_id)
        last_prods = session.get("last_search_results") or []
        if not last_prods:
            return []

        text_lower = text.lower()
        indices = []

        patterns = [
            (r'\b(first|1st|one|1)\b', 0),
            (r'\b(second|2nd|two|2)\b', 1),
            (r'\b(third|3rd|three|3)\b', 2),
            (r'\b(fourth|4th|four|4)\b', 3),
            (r'\b(fifth|5th|five|5)\b', 4)
        ]

        if "compare" in text_lower or "both" in text_lower:
            for pat, idx in patterns:
                if re.search(pat, text_lower):
                    indices.append(idx)
        else:
            for pat, idx in patterns:
                if re.search(pat, text_lower):
                    indices.append(idx)
                    break

        resolved = []
        for idx in indices:
            if 0 <= idx < len(last_prods):
                resolved.append(last_prods[idx])

        logger.info(f"[MemoryEngine] Resolved {len(resolved)} product references for text='{text}'")
        return resolved

    def clear_inactive_sessions(self):
        """Purges expired sessions older than timeout_seconds."""
        now = time.time()
        expired = [cid for cid, s in self.sessions.items() if now - s.get("last_updated_timestamp", 0) > self.timeout_seconds]
        for cid in expired:
            del self.sessions[cid]
        if expired:
            logger.info(f"[MemoryEngine] Purged {len(expired)} expired sessions.")


memory_engine = ConversationMemoryEngine()
