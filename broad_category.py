"""
broad_category.py — Broad Category Understanding & Subcategory Expansion Engine.
Distinguishes between Specific Product Queries (e.g. "Gaming Laptop", "Water Heater", "Garden Hose")
and Broad Category Queries (e.g. "Gardening Equipment", "Computer Accessories", "Kitchen Appliances").
Expands broad queries into candidate subcategories for diversified retrieval.
"""

import re
import logging

logger = logging.getLogger("trevor.broad_category")

# Configurable Mapping of Broad Categories to Subcategory Search Queries
BROAD_CATEGORY_MAP = {
    "gardening": [
        "garden tools set",
        "garden hose",
        "watering can",
        "pruning shears",
        "garden sprayer",
        "grass trimmer",
        "garden gloves",
        "garden rake",
        "garden shovel",
        "plant pots"
    ],
    "computer accessories": [
        "mechanical keyboard",
        "gaming mouse",
        "webcam",
        "monitor",
        "SSD",
        "USB hub",
        "laptop stand",
        "speakers",
        "headphones"
    ],
    "kitchen appliances": [
        "air fryer",
        "microwave oven",
        "mixer grinder",
        "induction stove",
        "electric kettle",
        "toaster",
        "hand blender",
        "rice cooker"
    ],
    "office accessories": [
        "office chair",
        "desk organizer",
        "monitor stand",
        "whiteboard",
        "ergonomic mouse",
        "desk lamp"
    ],
    "gym equipment": [
        "dumbbells",
        "resistance bands",
        "yoga mat",
        "treadmill",
        "pull up bar",
        "skipping rope"
    ],
    "fitness equipment": [
        "dumbbells",
        "resistance bands",
        "yoga mat",
        "treadmill",
        "pull up bar"
    ],
    "home decor": [
        "wall clock",
        "table lamp",
        "canvas painting",
        "curtains",
        "decorative vase",
        "scented candles"
    ],
    "photography gear": [
        "camera tripod",
        "camera lens",
        "camera bag",
        "ring light",
        "sd card",
        "camera flash"
    ],
    "camping equipment": [
        "camping tent",
        "sleeping bag",
        "camping lantern",
        "portable stove",
        "camping chair"
    ],
    "pet supplies": [
        "dog food",
        "cat litter",
        "pet bed",
        "dog leash",
        "pet grooming brush"
    ],
    "travel accessories": [
        "neck pillow",
        "packing cubes",
        "luggage tag",
        "passport holder",
        "travel adapter"
    ],
    "beauty products": [
        "face serum",
        "sunscreen",
        "moisturizer",
        "hair dryer",
        "face wash"
    ]
}

# Explicit Specific Products that must NEVER trigger broad expansion
SPECIFIC_PRODUCTS = {
    "garden hose", "water heater", "geyser", "gaming laptop", "pressure washer",
    "mixer grinder", "air fryer", "electric kettle", "microwave", "rice cooker",
    "iphone", "macbook", "smartwatch", "running shoes", "sneakers", "t-shirt",
    "jeans", "dumbbells", "yoga mat", "treadmill", "mechanical keyboard", "gaming mouse"
}


def is_broad_category_query(query: str, category: str = "") -> tuple[bool, str | None]:
    """
    Deterministically classifies whether a query represents a broad category vs specific product.
    Returns (is_broad: bool, category_key: str | None).
    """
    if not query:
        return False, None

    q_lower = query.lower().strip()
    cat_lower = (category or "").lower().strip()
    full_text = f"{cat_lower} {q_lower}"

    # Safety check: Specific products MUST NOT trigger broad expansion
    for sp in SPECIFIC_PRODUCTS:
        if re.search(r'\b' + re.escape(sp) + r'\b', q_lower):
            return False, None

    for b_key in BROAD_CATEGORY_MAP.keys():
        words = b_key.split()
        if all(re.search(r'\b' + re.escape(w) + r'\b', full_text) for w in words):
            logger.info(f"[BroadCategory] Detected Broad Category Query: '{query}' -> Key: '{b_key}'")
            return True, b_key

    broad_triggers = ["equipment", "equipments", "accessories", "appliances", "supplies", "gear", "decor", "products"]
    for trg in broad_triggers:
        if re.search(r'\b' + re.escape(trg) + r'\b', q_lower):
            if "garden" in q_lower or "gardening" in q_lower:
                return True, "gardening"
            elif "computer" in q_lower or "pc" in q_lower or "laptop" in q_lower:
                return True, "computer accessories"
            elif "kitchen" in q_lower:
                return True, "kitchen appliances"
            elif "gym" in q_lower or "workout" in q_lower or "fitness" in q_lower:
                return True, "gym equipment"
            elif "office" in q_lower:
                return True, "office accessories"
            elif "photo" in q_lower or "photography" in q_lower or "camera" in q_lower:
                return True, "photography gear"
            elif "camp" in q_lower or "camping" in q_lower:
                return True, "camping equipment"
            elif "pet" in q_lower or "pets" in q_lower:
                return True, "pet supplies"
            elif "travel" in q_lower:
                return True, "travel accessories"

    return False, None


def expand_broad_category(category_key: str, budget: int = None, max_candidates: int = 4) -> list[str]:
    """
    Returns list of subcategory candidate search strings for a broad category.
    Appends budget if provided.
    """
    candidates = BROAD_CATEGORY_MAP.get(category_key.lower(), [])
    if not candidates:
        return []

    result = []
    for sub in candidates[:max_candidates]:
        if budget:
            result.append(f"{sub} under {budget}")
        else:
            result.append(sub)

    logger.info(f"[BroadCategory] Expanded '{category_key}' into candidates: {result}")
    return result
