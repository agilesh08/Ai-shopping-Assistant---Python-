"""
category_manager.py — Category Transition Manager for Trevor AI Shopping Assistant.
Detects category switches across turns (e.g. Laptop -> Water Heater) vs category refinements (e.g. Laptop -> ASUS Laptop).
Resets shopping context on category transition while retaining user-level preferences (marketplace, language).
"""

import logging
import re

logger = logging.getLogger("trevor.category_manager")

# Root Category Family Mapping
CATEGORY_FAMILIES = {
    "LAPTOP": {"laptop", "gaming laptop", "notebook", "macbook", "ultrabook", "chromebook"},
    "PHONE": {"phone", "smartphone", "mobile", "flagship phone", "iphone", "android phone"},
    "HEADPHONES": {"headphone", "headphones", "earbuds", "earphones", "airpods", "headset", "tws"},
    "WATER_HEATER": {"water heater", "geyser", "instant water heater", "storage water heater", "immersion rod"},
    "TV": {"tv", "television", "smart tv", "led tv", "oled tv"},
    "APPLIANCE": {"refrigerator", "ac", "air conditioner", "washing machine", "microwave"},
    "CLOTHING": {"shirt", "t-shirt", "tshirt", "jeans", "jacket", "dress", "pants", "clothing", "apparel"},
    "SHOES": {"shoe", "shoes", "sneaker", "sneakers", "running shoes", "footwear", "boots"},
    "WATCH": {"watch", "smartwatch", "chronograph"}
}


def get_root_category_family(cat_str: str, p_type: str = "") -> str:
    """
    Determines the root category family string for a category or product type.
    """
    if p_type:
        p_upper = p_type.upper().strip()
        if p_upper in CATEGORY_FAMILIES:
            return p_upper
        elif p_upper == "WATER_HEATER" or "WATER" in p_upper or "GEYSER" in p_upper:
            return "WATER_HEATER"

    if not cat_str:
        return "UNKNOWN"

    cat_lower = cat_str.lower().strip()

    for fam, terms in CATEGORY_FAMILIES.items():
        if any(term in cat_lower for term in terms):
            return fam

    return cat_str.upper() if cat_str else "UNKNOWN"


def is_category_transition(prev_cat: str, prev_ptype: str, new_cat: str, new_ptype: str) -> bool:
    """
    Compares previous vs new category and product type.
    Returns True if user switched to a completely different root category family.
    """
    if not prev_cat and not prev_ptype:
        return False

    if not new_cat and not new_ptype:
        return False

    prev_fam = get_root_category_family(prev_cat, prev_ptype)
    new_fam = get_root_category_family(new_cat, new_ptype)

    if prev_fam == "UNKNOWN" or new_fam == "UNKNOWN":
        return False

    return prev_fam != new_fam


def handle_category_transition(session: dict, new_cat: str, new_ptype: str = "") -> tuple[dict, bool]:
    """
    Checks for category transition. If detected, clears category-specific context
    (brand, model, series, filters, specifications, search results, candidates) while
    retaining user-level preferences (marketplace, language, history).
    Logs diagnostic details.
    """
    prev_cat = session.get("category") or ""
    prev_ptype = session.get("product_type") or ""

    transition_occurred = is_category_transition(prev_cat, prev_ptype, new_cat, new_ptype)

    logger.info(f"[CategoryManager] Previous Category: '{prev_cat}' | New Category: '{new_cat}' | Context Reset: {'Yes' if transition_occurred else 'No'}")
    print(f"[CategoryManager] Previous Category: '{prev_cat or 'None'}' | New Category: '{new_cat or 'None'}' | Context Reset: {'Yes' if transition_occurred else 'No'}")

    if transition_occurred:
        session["brand"] = None
        session["series"] = None
        session["model"] = None
        session["budget"] = None
        session["color"] = None
        session["storage"] = None
        session["ram"] = None
        session["cpu"] = None
        session["gpu"] = None
        session["display"] = None
        session["battery"] = None
        session["gender"] = None
        session["size"] = None
        session["purpose"] = None
        session["specifications"] = {}
        session["active_filters"] = {}
        session["last_search_query"] = None
        session["search_query"] = None
        session["last_search_results"] = []

        session["category"] = new_cat
        if new_ptype:
            session["product_type"] = new_ptype

    return session, transition_occurred
