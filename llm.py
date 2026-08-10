"""
llm.py — Ollama / Llama 3.2 interface.
All AI reasoning goes through here.
"""

import json
import requests
from config import OLLAMA_BASE_URL, OLLAMA_MODEL


def chat(messages: list[dict], temperature: float = 0.7) -> str:
    """
    Send a conversation to Ollama and return the assistant's reply.

    Args:
        messages: List of {role, content} dicts (system, user, assistant)
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)

    Returns:
        str: The model's text response
    """
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        return "__OLLAMA_OFFLINE__"
    except requests.exceptions.Timeout:
        return "__OLLAMA_TIMEOUT__"
    except Exception as e:
        return f"__OLLAMA_ERROR__: {e}"


import re

# ── Categories & Brand Dictionaries for Entity Extraction & Context Reset ──────

KNOWN_CATEGORIES = {
    "laptop": ["laptop", "laptops", "notebook", "notebooks", "macbook", "chromebook", "vivobook", "legion", "omen", "tuf", "ideapad", "pavilion", "nitro", "rog", "predator", "thinkpad", "thinpad", "alienware", "zenbook"],
    "phone": ["phone", "phones", "mobile", "mobiles", "smartphone", "smartphones", "iphone", "galaxy", "redmi", "realme", "pixel", "poco", "iqoo", "nord"],
    "cycle": ["cycle", "cycles", "bicycle", "bicycles", "mtb", "gear cycle", "tricycle"],
    "shoes": ["shoe", "shoes", "sneaker", "sneakers", "footwear", "running shoes", "sports shoes", "boots", "sandals", "loafers", "crocs", "heels", "slippers"],
    "ac": ["ac", "air conditioner", "split ac", "inverter ac", "window ac"],
    "refrigerator": ["refrigerator", "refrigerators", "fridge", "fridges", "double door fridge", "single door fridge", "side by side fridge", "mini fridge"],
    "tv": ["tv", "tvs", "television", "televisions", "smart tv", "led tv", "oled tv", "qled tv", "4k tv", "google tv"],
    "headphones": ["headphone", "headphones", "earphone", "earphones", "earbuds", "tws", "airpods", "neckband", "headset", "noise cancelling"],
    "mouse": ["mouse", "mice"],
    "keyboard": ["keyboard", "keyboards"],
    "monitor": ["monitor", "monitors", "display screen", "gaming monitor"],
    "furniture": ["furniture", "chair", "table", "desk", "sofa", "bed", "mattress", "wardrobe", "bookshelf", "gaming chair", "dining table", "office chair", "recliner"],
    "fashion": ["clothing", "shirt", "t-shirt", "tshirt", "jeans", "jacket", "dress", "saree", "hoodie", "blazer", "trousers", "pants", "top", "kurta", "clothes", "wear", "apparel", "suit", "coat", "sweater", "shorts", "trackpants"],
    "watches": ["watch", "watches", "smartwatch", "smartwatches", "fitness band", "chronograph"],
    "kitchen": ["kitchen", "appliance", "appliances", "microwave", "oven", "mixer", "grinder", "juicer", "air fryer", "toaster", "chimney", "induction", "kettle", "dishwasher", "water purifier", "coffee maker", "blender", "cooktop"],
    "gaming_accessories": ["gamepad", "controller", "joystick", "cooling pad", "gaming desk", "vr headset", "console", "ps5", "xbox", "nintendo"],
    "water_heater": ["water heater", "water heaters", "geyser", "geysers", "instant water heater", "storage water heater", "immersion rod", "solar water heater"],
    "other_products": ["camera", "speaker", "speakers", "bluetooth speaker", "soundbar", "power bank", "charger", "cable", "backpack", "luggage", "suitcase", "wallet", "sunglasses", "perfume", "trimmer", "shaver", "hair dryer", "vacuum cleaner", "washing machine", "heater", "fan", "air purifier"],
}

KNOWN_BRANDS = [
    "acer", "samsung", "asus", "nike", "hp", "dell", "lenovo", "apple", "puma",
    "adidas", "sony", "oneplus", "realme", "redmi", "xiaomi", "lg", "whirlpool",
    "haier", "godrej", "bose", "jbl", "boat", "noise", "fire-boltt", "zebronics",
    "logitech", "razer", "hyperx", "msi", "intel", "amd", "nvidia"
]

CONVERSATIONAL_WORDS = [
    r"\bget\b", r"\bshow\s+me\b", r"\bshow\b", r"\bfind\s+me\b", r"\bfind\b",
    r"\bgive\s+me\b", r"\bi\s+need\b", r"\bneed\b", r"\bplease\b", r"\bcan\s+you\b",
    r"\blooking\s+for\b", r"\bsuggest\s+me\b", r"\bsuggest\b", r"\brecommend\b",
    r"\bwith\s+good\s+ratings\b", r"\bgood\s+ratings\b", r"\bhigh\s+rating\b",
    r"\bhigh\s+rated\b", r"\bbest\b", r"\btop\s+rated\b", r"\btop\b", r"\boptions\b",
    r"\bamazon\b", r"\bflipkart\b", r"\bfor\s+me\b",
    # Intent & Usage Filler Words
    r"\btask\b", r"\btasks\b", r"\bday\s*to\s*day\b", r"\bdaily\s*use\b", r"\bnormal\s*use\b",
    r"\boffice\b", r"\bstudent\b", r"\bcollege\b", r"\bprogramming\b", r"\bwork\b",
    r"\bpurpose\b", r"\bneeds?\b", r"\brequirement\b", r"\brequirements\b"
]


def is_advisor_query(user_message: str) -> bool:
    """
    Detects if user is requesting buying advice, non-technical spec recommendations, or usage-based guidance.
    """
    if not user_message:
        return False
    msg_lower = user_message.lower().strip()
    
    advisor_patterns = [
        r"don'?t know", r"don'?t understand", r"what should i buy", r"which is better",
        r"what do you recommend", r"suggest (a|something|what)", r"normal use",
        r"day[- ]to[- ]day", r"daily use", r"for programming", r"for gaming",
        r"for college", r"for office", r"for editing", r"which one should i",
        r"help me choose", r"help me pick", r"confused between", r"guide me",
        r"recommendations for", r"what specs do i need", r"explain (processor|ram|gpu|specs)"
    ]
    return any(re.search(p, msg_lower) for p in advisor_patterns)


def is_shopping_query(user_message: str) -> bool:
    """
    Deterministically detects whether user_message contains a request for purchasable products.
    Returns True if product categories, brands, price patterns, specs, or buying verbs are detected.
    """
    if not user_message:
        return False
        
    msg_lower = user_message.lower().strip()
    
    # 1. Product category match
    if extract_category_from_text(msg_lower) is not None:
        return True
        
    # 2. Price / budget pattern (e.g. under 80000, below 50k, rs 5000, ₹4000, budget 30000)
    budget_pattern = r"(under|below|around|within|less than|budget|price|rs\.?|₹)\s*(\d+|k\b)"
    if re.search(budget_pattern, msg_lower):
        # Check if paired with any brand, product spec, or shopping verb
        shopping_verbs = ["buy", "find", "search", "show", "get", "give", "need", "suggest", "recommend", "looking", "best", "top", "options"]
        if any(b in msg_lower for b in KNOWN_BRANDS) or any(v in msg_lower for v in shopping_verbs):
            return True
            
    # 3. Known brand + spec or buying action
    for b in KNOWN_BRANDS:
        if re.search(r'\b' + re.escape(b) + r'\b', msg_lower):
            # Check for specs or shopping indicators
            spec_indicators = ["rtx", "gtx", "gb", "ssd", "ram", "oled", "4k", "5g", "i3", "i5", "i7", "i9", "ryzen", "pro", "max", "wireless", "gaming", "running", "casual", "smart", "automatic", "portable"]
            shopping_verbs = ["buy", "find", "search", "show", "get", "give", "need", "suggest", "recommend", "looking", "best", "top", "options", "price", "cost"]
            if any(s in msg_lower for s in spec_indicators) or any(v in msg_lower for v in shopping_verbs):
                return True

    # 4. Shopping verb + purchasable indicator
    shopping_triggers = ["buy", "find me", "show me", "get me", "search for", "suggest a", "recommend a", "price of", "cost of", "deals on", "discount on"]
    if any(trigger in msg_lower for trigger in shopping_triggers):
        return True

    return False


def classify_intent(user_message: str, history: list[dict]) -> str:
    """
    Classify whether the user wants shopping, styling, advisor mode, or general chat.

    Returns one of: "shopping" | "shopping_advisor" | "styling" | "amazon_yes" | "greeting" | "reminder" | "general"
    """
    msg_lower = user_message.lower().strip()

    # Priority Rule 1: Reminder intent
    reminder_keywords = ["remind", "reminder", "notify", "notify me", "alert me", "remind me", "set reminder", "remind later", "watch this product", "price alert", "deal alert"]
    if any(re.search(r'\b' + re.escape(kw) + r'\b', msg_lower) for kw in reminder_keywords):
        return "reminder"

    # Priority Rule 2: Shopping Advisor Mode detection
    if is_advisor_query(user_message):
        return "shopping_advisor"

    # Priority Rule 3: Deterministic shopping detection
    if is_shopping_query(user_message):
        return "shopping"

    system_prompt = """You are an intent classifier for a shopping and styling assistant bot.

CRITICAL PRIORITY RULE:
Reminder intent has HIGHER PRIORITY than shopping. If the user uses keywords like 'remind', 'reminder', 'notify', 'notify me', 'alert me', 'remind me', 'set reminder', 'remind later', 'watch this product', 'price alert', 'deal alert', you MUST classify it as 'reminder' even if they mention specific products.

Classify the user's message into EXACTLY ONE of these categories:
- reminder: User wants to set a reminder or be notified about a product/deal.
- shopping_advisor: User asks for buying advice, guidance, non-technical spec explanations, or recommendations based on usage needs (e.g. "don't know about RAM", "laptop for programming", "what should I buy").
- shopping: User wants to buy, search, compare, find specific products immediately.
- styling: User wants fashion advice, outfit ideas, styling tips, how to wear something.
- amazon_yes: ONLY simple affirmative answers like "yes", "sure", "okay", "find it" when no product name is given.
- greeting: Simple hello, hi, how are you, what can you do.
- general: Anything else.

Reply with ONLY the category word. No explanation. No punctuation. Just the word."""

    recent = history[-4:] if len(history) > 4 else history
    messages = [
        {"role": "system", "content": system_prompt},
        *recent,
        {"role": "user", "content": f"Classify this message: {user_message}"},
    ]

    result = chat(messages, temperature=0.0)
    result = result.lower().strip().rstrip(".")

    valid = {"shopping", "shopping_advisor", "styling", "amazon_yes", "greeting", "reminder", "general"}
    classified = result if result in valid else "general"

    # Fail-safe: If LLM returns general/styling but is_advisor_query is True, force shopping_advisor
    if classified in {"general", "styling"} and is_advisor_query(user_message):
        return "shopping_advisor"

    # Fail-safe: If LLM returns general/styling but is_shopping_query is True, force shopping
    if classified in {"general", "styling"} and is_shopping_query(user_message):
        return "shopping"

    return classified

    return classified



def extract_category_from_text(text: str) -> str | None:
    if not text:
        return None
    text_lower = text.lower()
    for cat, keywords in KNOWN_CATEGORIES.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                return cat
    return None


def is_refinement_message(user_message: str, current_state: dict | None = None) -> bool:
    """
    Returns True ONLY if user_message is an explicit refinement modifier OR an answer to a pending clarification.
    Refinements include:
      - Pending clarification answer (when current_state has needs_clarification=True)
      - Budget modifiers: "cheaper", "more expensive", "increase budget", "less than 50k"
      - Brand filters: "only Acer", "show ASUS", "just Nike"
      - Spec filters: "show RTX4060", "with 16GB RAM", "OLED display"
      - Pagination & sorting: "more options", "show more", "next", "sort by rating"
    """
    if not current_state:
        return False

    # Pending clarification response must ALWAYS be treated as a refinement/continuation
    if current_state.get("needs_clarification"):
        return True

    msg_lower = user_message.lower().strip()

    # Explicit refinement keywords
    refinement_keywords = [
        "cheaper", "cheapest", "expensive", "more expensive", "lower price", "higher price",
        "increase budget", "decrease budget", "lower budget", "under budget", "less price",
        "more options", "show more", "other options", "different options", "next", "more",
        "sort by", "top rated", "best rated", "highest rating", "cheapest first"
    ]
    if any(re.search(r'\b' + re.escape(kw) + r'\b', msg_lower) for kw in refinement_keywords):
        return True

    # Explicit brand filter pattern: "only <brand>", "show <brand>", "just <brand>", "prefer <brand>", "filter by <brand>"
    brand_modifier_pattern = r"\b(only|show|just|prefer|filter by|with)\s+(" + "|".join(KNOWN_BRANDS) + r")\b"
    if re.search(brand_modifier_pattern, msg_lower):
        return True

    # Explicit spec filter pattern: "show rtx...", "with 16gb...", "make it...", "filter..."
    spec_modifier_pattern = r"\b(show|with|make it|filter|only)\s+(rtx|gtx|\d+gb|ssd|ram|oled|4k|5g|i3|i5|i7|i9|ryzen)\b"
    if re.search(spec_modifier_pattern, msg_lower):
        return True

    # Very short modifier without category or new brand declaration (e.g. "under 50000", "in blue")
    words = msg_lower.split()
    if len(words) <= 3:
        has_cat = extract_category_from_text(msg_lower) is not None
        has_brand = any(re.search(r'\b' + re.escape(b) + r'\b', msg_lower) for b in KNOWN_BRANDS)
        if not has_cat and not has_brand:
            return True

    return False


import category_manager


def is_category_change(user_message: str, current_state: dict | None) -> bool:
    """
    Returns True if user_message is a NEW standalone shopping search that requires
    clearing previous shopping context (Brand, Budget, GPU, RAM, Specs).
    Returns False ONLY when user_message is an explicit refinement or clarification reply.
    """
    if not current_state:
        return False

    if current_state.get("needs_clarification"):
        return False

    msg_lower = user_message.lower().strip()
    followup_phrases = ["show more", "next", "another", "similar", "compare", "better than this", "show 1st", "show 2nd", "show 3rd", "first one", "second one"]
    if any(fp in msg_lower for fp in followup_phrases):
        return False

    curr_cat = current_state.get("category") or ""
    new_cat = extract_category_from_text(msg_lower)

    if new_cat:
        prev_fam = category_manager.get_root_category_family(curr_cat)
        new_fam = category_manager.get_root_category_family(new_cat)
        if prev_fam != new_fam:
            return True

    return not is_refinement_message(user_message, current_state)


def normalize_search_query(query: str, state: dict) -> str:
    """
    Normalizes marketplace search queries:
    1. Removes duplicate budgets (e.g. 20k, 20000, under 20k -> single under 20000).
    2. Removes conversational & usage intent words (for use, daily use, task, student, office).
    3. Removes duplicate product keywords.
    4. Guarantees clean keyword structure (Brand + Model/Category + single Budget).
    """
    if not query:
        return ""

    # Extract budget from state or query
    budget = state.get("budget")
    if not budget:
        bm = re.search(r"\b(?:under|below|rs|₹)?\s*(\d{4,6})\b", query, re.I) or re.search(r"\b(\d+)\s*k\b", query, re.I)
        if bm:
            b_val = bm.group(1)
            budget = int(b_val) * 1000 if "k" in bm.group(0).lower() else int(b_val)
            state["budget"] = budget

    # Scrub ALL budget clauses from query
    query = re.sub(r"\b(?:under|below|for|rs|₹|budget)?\s*\d+\s*k\b", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\b(?:under|below|for|rs|₹|budget)?\s*\d{4,6}\b", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\bunder\b", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\bbelow\b", "", query, flags=re.IGNORECASE)

    # Scrub conversational filler & intent phrases
    intent_fillers = [
        r"\bfor\s+use\b", r"\bfor\s+daily\s+use\b", r"\bfor\s+normal\s+use\b",
        r"\bdaily\s+use\b", r"\bnormal\s+use\b", r"\bfor\s+tasks?\b", r"\btasks?\b",
        r"\bday\s*to\s*day\b", r"\boffice\b", r"\bstudent\b", r"\bcollege\b",
        r"\bprogramming\b", r"\bwork\b", r"\bpurpose\b", r"\bneeds?\b", r"\bfor\b", r"\buse\b"
    ]
    for pattern in intent_fillers:
        query = re.sub(pattern, "", query, flags=re.IGNORECASE)

    for pattern in CONVERSATIONAL_WORDS:
        query = re.sub(pattern, "", query, flags=re.IGNORECASE)

    query = re.sub(r'\s+', ' ', query).strip()

    # Deduplicate words in query while preserving order
    words = query.split()
    seen = set()
    deduped = []
    for w in words:
        w_lower = w.lower()
        if w_lower not in seen:
            seen.add(w_lower)
            deduped.append(w)
    query = " ".join(deduped)

    # Ensure Category keyword is present
    cat = (state.get("category") or "").lower()
    if not any(k in query.lower() for k in ["phone", "mobile", "smartphone", "laptop", "tv", "shoes", "ac", "fridge", "watch", "headphone", "earbud", "cycle", "mouse", "keyboard", "monitor"]):
        if cat == "phone":
            query = f"Phone {query}"
        elif cat == "laptop":
            query = f"Laptop {query}"
        elif cat:
            query = f"{cat.capitalize()} {query}"

    query = re.sub(r'\s+', ' ', query).strip()

    # Re-attach SINGLE clean budget clause
    if budget:
        query = f"{query} under {budget}"

    return query.strip()


def build_and_validate_search_query(query: str, state: dict, user_message: str = "") -> str:
    """
    Single authoritative component for building, validating, and cleaning marketplace search queries.
    Prevents stale context leaks, multi-brand conflicts, word duplications, and meaningless intent words.
    """
    if not query:
        query = state.get("search_query") or ""

    user_msg_lower = (user_message or "").lower()
    
    # 1. Resolve Multi-Brand Conflicts (e.g. "Samsung Laptop ASUS TUF Gaming A15")
    found_brands = []
    for b in KNOWN_BRANDS:
        if re.search(r'\b' + re.escape(b) + r'\b', query, re.I):
            found_brands.append(b)

    if len(found_brands) > 1:
        # Keep ONLY the brand explicitly present in user_message or active state brand
        active_brand = (state.get("brand") or "").lower()
        msg_brand = None
        for b in found_brands:
            if re.search(r'\b' + re.escape(b) + r'\b', user_msg_lower, re.I):
                msg_brand = b
                break
        
        target_brand = msg_brand or active_brand or found_brands[-1]
        for b in found_brands:
            if b.lower() != target_brand.lower():
                query = re.sub(r'\b' + re.escape(b) + r'\b', '', query, flags=re.IGNORECASE)

    # 2. Run query normalization & duplicate budget scrubbing
    query = normalize_search_query(query, state)

    # 3. Deduplicate words ("Electronics Electronics" -> "Electronics")
    words = query.split()
    seen = set()
    deduped = []
    for w in words:
        w_lower = w.lower()
        if w_lower not in seen:
            seen.add(w_lower)
            deduped.append(w)
    query = " ".join(deduped)

    # 4. Reject generic product names ("Electronics", "Trending Products") and substitute clean category
    generic_terms = {"electronics", "products", "item", "items", "trending products", "popular products"}
    if query.strip().lower() in generic_terms:
        cat = state.get("category") or "Smartphone"
        budget = state.get("budget")
        query = f"{cat} under {budget}" if budget else str(cat)

    query = re.sub(r'\s+', ' ', query).strip()
    state["search_query"] = query
    return query


def calculate_query_confidence(query: str, state: dict) -> float:
    """
    Search Confidence Score Generator for Trevor v2.0:
    Evaluates confidence score (0.0 to 1.0) based on query specificity, category detection, and requirement clarity.
    If confidence < 0.70 (70%), Trevor asks clarifying questions before searching.
    """
    if not query or len(query.strip()) < 3:
        return 0.20

    score = 0.50  # Base score
    q_lower = query.lower()

    # Category present (+0.25)
    if state.get("category") or any(c in q_lower for c in ["phone", "laptop", "tv", "shoes", "ac", "shirt", "watch", "earbuds", "headphones", "refrigerator"]):
        score += 0.25

    # Specific Brand or Model present (+0.15)
    if state.get("brand") or state.get("model") or any(b in q_lower for b in KNOWN_BRANDS):
        score += 0.15

    # Budget or Filters present (+0.10)
    if state.get("budget") or "under" in q_lower or re.search(r'\d+', q_lower):
        score += 0.10

    # Penalize vague or ambiguous words (-0.30)
    if q_lower in {"something", "anything", "good item", "product", "electronics", "stuff"}:
        score -= 0.30

    return min(1.0, max(0.0, score))


def clean_and_optimize_query(state: dict, user_message: str) -> str:
    """
    Optimizes search_query:
    1. Preserves brand ONLY if explicitly present in user_message or active refinement.
    2. Removes "Amazon" and "Flipkart" from search string.
    3. Removes conversational words & duplicate budget values via normalize_search_query.
    4. Retains product type, category, budget, and specs via build_and_validate_search_query.
    """
    user_msg_lower = user_message.lower()
    state_brand = state.get("brand")
    detected_brand = None
    
    # Check if a brand is explicitly mentioned in user_message
    for b in KNOWN_BRANDS:
        if re.search(r'\b' + re.escape(b) + r'\b', user_msg_lower):
            detected_brand = b.title()
            state["brand"] = detected_brand
            break

    # If state had a brand from previous context, verify if it was mentioned in user_message or is an active refinement
    if not detected_brand and state_brand and str(state_brand).strip().lower() not in {"null", "none", ""}:
        if re.search(r'\b' + re.escape(str(state_brand).lower()) + r'\b', user_msg_lower):
            detected_brand = str(state_brand).strip()
        elif is_refinement_message(user_message, state):
            detected_brand = str(state_brand).strip()
        else:
            # Clear brand if user did not specify it in new search!
            state["brand"] = None

    raw_query = state.get("search_query") or ""
    
    if not raw_query:
        parts = []
        if detected_brand:
            parts.append(detected_brand)
        if state.get("product_type"):
            parts.append(str(state["product_type"]))
        if state.get("category"):
            parts.append(str(state["category"]))
        if state.get("model"):
            parts.append(str(state["model"]))
        if state.get("filters"):
            parts.append(str(state["filters"]))
        if state.get("budget"):
            parts.append(f"under {state['budget']}")
        raw_query = " ".join(parts)

    query = raw_query

    # Scrub any brands from query that were NOT explicitly mentioned in user_message and NOT active refinement
    for b in KNOWN_BRANDS:
        if not re.search(r'\b' + re.escape(b) + r'\b', user_msg_lower):
            if not (detected_brand and detected_brand.lower() == b.lower()):
                query = re.sub(r'\b' + re.escape(b) + r'\b', '', query, flags=re.IGNORECASE)

    # Remove "amazon" and "flipkart"
    query = re.sub(r'\bamazon\b', '', query, flags=re.IGNORECASE)
    query = re.sub(r'\bflipkart\b', '', query, flags=re.IGNORECASE)

    # Build and validate clean search query (brand conflicts, word deduplication, intent filler, budget)
    query = build_and_validate_search_query(query, state, user_message)

    # Ensure Brand is preserved in query if detected
    if detected_brand:
        if not re.search(r'\b' + re.escape(detected_brand) + r'\b', query, re.IGNORECASE):
            query = f"{detected_brand} {query}"

    query = re.sub(r'\s+', ' ', query).strip()
    state["search_query"] = query
    return query



def update_shopping_state(user_message: str, current_state: dict | None, history: list[dict]) -> dict:
    """
    Update the shopping state based on the user's new message.
    Automatically resets context if a new category is detected.
    Preserves brand and all entities while optimizing search_query.
    """
    was_clarification = bool(current_state and current_state.get("needs_clarification"))

    if current_state and is_category_change(user_message, current_state):
        current_state = None

    system_prompt = """You manage the shopping state for an e-commerce assistant.
Given the current state and the user's new message, return the updated state in JSON format.

RULES:
- PENDING CLARIFICATION:
  • If current_state has "needs_clarification": true, the user is responding to a clarification question.
  • MUST PRESERVE all existing fields from current_state (budget, category, brand, specs).
  • Update ONLY the missing field specified in the user's message (e.g. Category, Brand, Specs, Budget).
  • Set "needs_clarification": false and "clarification_question": null once the user provides the missing info.
- NEW SEARCH vs REFINEMENT:
  • If current_state is None, this is a NEW SEARCH. Reset all context completely.
  • If current_state exists and user is refining (e.g. "cheaper", "show 16GB RAM", "show only Acer", "under 50k"), preserve existing category/budget and update specified fields.
- ENTITY EXTRACTION:
  • brand: Detected brand (e.g. Acer, Samsung, ASUS, Nike, HP, Dell, Lenovo, Apple, Puma, Adidas, Sony) or null. NEVER omit a brand specified by the user!
  • category: Core product category (e.g. Laptop, Phone, Shoes, Cycle, AC, TV, Refrigerator, Headphones, Mouse, Monitor, Smartwatch).
  • product_type: Sub-type (e.g. Gaming, Running, OLED, Smart, Wireless) or null.
  • budget: Numeric budget or string (e.g. 60000) or null.
  • gpu: GPU model (e.g. RTX4050) or null.
  • ram: RAM size (e.g. 16GB) or null.
  • storage: Storage size (e.g. 512GB SSD) or null.
  • display: Display details (e.g. OLED) or null.
  • model: Specific model name (e.g. Vivobook, Nitro 5) or null.
  • filters: Specs or extra requirements or null.
- SEARCH QUERY OPTIMIZATION:
  • Generate "search_query" for marketplace search box.
  • MUST PRESERVE all detected shopping entities: Brand, Product Type, Category, Model, Specs, Budget.
  • NEVER remove detected brand names (e.g., "Acer gaming laptop under 60000", NEVER "gaming laptop under 60000").
  • NEVER insert the words "Amazon" or "Flipkart" into search_query (e.g. NEVER "Amazon laptops").
  • ONLY remove conversational filler words ("I need", "Show me", "Find", "Give me", "Please", "Can you", "Looking for", "Suggest me", "Recommend", "with good ratings", "best", "top rated", etc.).
- Output ONLY valid JSON, no markdown formatting, no explanations.

JSON Format:
{
  "needs_clarification": false,
  "clarification_question": null,
  "shopping_intent": "Product Search",
  "category": "Core product category (e.g., Laptop, Cycle, Phone, Shoes, Headphones)",
  "brand": "Detected brand or null",
  "product_type": "Product sub-type or null",
  "product": "Product string",
  "budget": 60000 or null,
  "gpu": null,
  "ram": null,
  "storage": null,
  "display": null,
  "model": null,
  "filters": null,
  "search_query": "Optimized concise keywords preserving brand & entities (e.g., Headphones under 800)",
  "marketplace": "amazon"
}
"""

    state_str = json.dumps(current_state) if current_state else "None"
    
    # If starting a new search (current_state is None), do not send previous shopping conversation history into LLM context
    history_to_send = [] if (current_state is None) else (history[-4:] if len(history) > 4 else history)
    
    messages = [
        {"role": "system", "content": system_prompt},
        *history_to_send,
        {"role": "user", "content": f"Current State: {state_str}\nUser: {user_message}"},
    ]

    result = chat(messages, temperature=0.0)
    
    if result.startswith("__OLLAMA"):
        return {"error": result}
        
    try:
        if "{" in result and "}" in result:
            json_str = result[result.find("{"):result.rfind("}")+1].strip()
        elif "```json" in result:
            json_str = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            json_str = result.split("```")[1].strip()
        else:
            json_str = result
            
        new_state = json.loads(json_str, strict=False)
        
        # If answering a pending clarification, ensure context fields from current_state are preserved
        if was_clarification and current_state:
            new_state["needs_clarification"] = False
            new_state["clarification_question"] = None
            for key in ["budget", "brand", "category", "product_type", "gpu", "ram", "storage", "display", "model", "filters"]:
                val = new_state.get(key)
                if (val is None or str(val).lower() in {"null", "none", "unknown", ""}) and current_state.get(key):
                    new_state[key] = current_state[key]

        # Post-process search query to guarantee brand & entity preservation and clean filler words
        clean_and_optimize_query(new_state, user_message)

        # Enforce Priority Order: Current User Request > Memory
        extracted_cat = extract_category_from_text(user_message)
        if extracted_cat:
            new_state["category"] = extracted_cat.replace("_", " ").title()

        prev_cat_str = (current_state.get("category") if current_state else "None")
        new_cat_str = new_state.get("category") or "Unknown"
        q_builder_query = new_state.get("search_query") or ""

        print("\n========== SHOPPING PIPELINE ==========")
        print(f"Raw User Message: {user_message}")
        print(f"Intent: shopping")
        print(f"Structured Request Category: {extracted_cat or new_cat_str}")
        print(f"Memory Before Merge Category: {prev_cat_str}")
        print(f"Memory After Merge Category: {new_cat_str}")
        print(f"Query Builder Category: {new_cat_str}")
        print(f"Generated Query: {q_builder_query}")
        print("=======================================\n")

        return new_state
    except Exception as e:
        safe_raw = result.encode('ascii', 'ignore').decode('ascii')
        print(f"Error parsing JSON from LLM: {e}\nRaw output: {safe_raw}")
        return {"error": "Failed to parse state"}


def get_styling_advice(user_message: str, history: list[dict]) -> dict:
    """
    Generate styling advice from the user's message.
    Returns a dict: { "advice": str, "ready": bool }
    - ready=True means we have enough info and gave advice
    - ready=False means we need more context (returned a follow-up question)
    """
    system_prompt = """You are Trevor, a friendly and expert personal stylist assistant on Telegram.

Your job is to give personalized outfit and styling advice based on what the user tells you.

RULES:
- Chat naturally like a real person, not a robot
- If the user asks for outfit or styling advice but DOES NOT provide Male/Female, budget, or preferred style, you MUST ask ONE clarifying question to gather this information. DO NOT recommend an outfit yet.
- Once you have enough context, recommend a complete outfit solution under the heading "Recommended Combination" (e.g., 👔 Navy Blue Blazer, 👕 White Shirt, 👖 Charcoal Grey Trousers).
- Give advice in a warm, conversational tone using emojis sparingly
- Always end a complete outfit recommendation by asking: "Would you like me to find highly rated Amazon products for this complete combination?"
- Keep responses concise and Telegram-friendly

IMPORTANT: Output your response as plain text. No JSON. No markdown headers. Just natural chat."""

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]

    response = chat(messages, temperature=0.8)

    # Determine if we gave actual advice or asked a follow-up question
    # Heuristic: if response ends with "?" and is short, it's a follow-up question
    is_question = response.strip().endswith("?") and len(response) < 300
    ready = not is_question

    return {"advice": response, "ready": ready}


def get_shopping_advisor_advice(user_message: str, history: list[dict]) -> dict:
    """
    Generate non-technical buying guidance and spec recommendations for Shopping Advisor Mode.
    Returns dict: { "advice": str }
    """
    system_prompt = """You are Trevor, an expert and friendly AI Shopping Advisor on Telegram.
Your goal is to provide warm, personalized buying guidance and specification recommendations based on what the user actually uses their product for.

RULES FOR SHOPPING ADVISOR MODE:
1. TALK LIKE A SHOPPING CONSULTANT:
   - Be warm, encouraging, and conversational with subtle emojis 😊.
   - Speak in simple, non-technical language. Avoid technical jargon unless requested.

2. EXPLAIN SPECIFICATIONS IN SIMPLE TERMS:
   - Explain WHY a specification matters for their specific usage.
   - Examples:
     • 5000mAh Battery -> "All-day battery life without needing a charger."
     • 8GB RAM -> "Smooth multitasking so your apps run without lagging."
     • Fast Processor -> "Fast enough to keep your phone smooth and lag-free for years."
     • RTX4050 GPU -> "Great for smooth gaming and fast video rendering."
     • 512GB SSD -> "Plenty of storage for your files, programs, and photos that loads instantly."

3. RECOMMENDATION STRUCTURE:
   - Acknowledge their use case warmly (e.g. "That's completely fine 😊" or "No problem!").
   - Recommend the ideal specifications for their needs (Processor, RAM, Storage, Battery, Display, etc.).
   - If budget is missing, ask gently for their preferred budget.

4. MANDATORY CLOSING QUESTION:
   - You MUST ALWAYS conclude your response with this exact question:
     "Would you like me to find highly rated Amazon products matching these recommendations?"

5. DO NOT INVENT PRODUCT NAMES OR ARTIFICIAL PRICES. Only recommend specifications and features."""

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]

    response = chat(messages, temperature=0.7)
    if response.startswith("__OLLAMA"):
        return {"advice": "⚠️ I'm taking a quick break. Please try again!"}

    # Ensure response ends with the mandatory closing question if missing
    closing_q = "Would you like me to find highly rated Amazon products matching these recommendations?"
    if closing_q.lower() not in response.lower():
        response = response.strip() + f"\n\n{closing_q}"

    # Extract any recommended model names from response text
    model_matches = re.findall(r"\b((?:Samsung|Realme|Moto|POCO|Redmi|Xiaomi|OnePlus|Apple|iQOO|Acer|Lenovo|HP|Asus|Dell|Bose|JBL|boAt|Noise|Sony)\s+(?:Galaxy\s+)?(?:Narzo\s+)?[\w\d\+]+(?:\s+[\w\d\+]+)?)\b", response, re.I)
    recommended_models = list(dict.fromkeys([m.strip() for m in model_matches if len(m.strip()) > 5]))

    return {"advice": response, "recommended_models": recommended_models}


def general_chat(user_message: str, history: list[dict]) -> str:
    """Handle greetings and general conversation as Trevor."""
    system_prompt = """You are Trevor, a friendly AI shopping and styling assistant on Telegram.

You help users:
1. Find products on Amazon India and Flipkart
2. Get personalized fashion and styling advice

Keep your replies short, warm, and conversational.
If the user says hi or asks what you can do, introduce yourself briefly and give 2-3 examples of what you help with.
Do NOT use bullet points with dashes. Use natural sentences or emoji bullets.

CRITICAL RULES:
- NEVER EVER invent, generate, recommend, or list specific product names, brand models, prices, ratings, or links under any circumstances.
- All product recommendations MUST come from the Shopping Search Tool scraper. Never fabricate product options from memory.
- If the user asks for purchasable products or shopping search, let them know you can search live marketplace data for them.
- If there are unresolved shopping requests in the chat history, ignore them. The system handles searches automatically.
- Just reply to the immediate conversational message.
- Always end with a friendly invitation for them to ask something."""

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]

    return chat(messages, temperature=0.9)


def extract_electronics_specifications(name: str, features: list[str] = None, category: str = "") -> dict:
    """
    Extract structured specifications from product title and features for electronics categories.
    Guarantees that electronic products always have detailed technical specs.
    """
    import re
    features = features or []
    full_text = f"{name} {' '.join(features)}"
    specs = {}

    cat_lower = category.lower() if category else ""
    text_lower = full_text.lower()
    
    # 1. Laptop
    if any(k in cat_lower for k in ["laptop", "notebook", "macbook", "chromebook"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["laptop", "notebook", "macbook", "chromebook", "vivobook", "legion", "nitro", "tuf", "pavilion"]):
        proc_m = re.search(r"(Intel\s*(?:Core\s*)?(?:i\d|Ultra\s*\d)[\w\d-]*|Ryzen\s*\d\s*[\w\d-]*|Apple\s*M\d\s*(?:Pro|Max)?|Celeron[\w\d-]*|Pentium[\w\d-]*)", full_text, re.I)
        if proc_m: specs["Processor"] = proc_m.group(1).strip()

        gpu_m = re.search(r"(NVIDIA\s*(?:GeForce\s*)?(?:RTX|GTX)\s*\d{4}[\w\d]*|AMD\s*Radeon[\w\d\s]*|Intel\s*(?:Iris\s*Xe|Arc)[\w\d]*|M\d\s*\d+-core\s*GPU)", full_text, re.I)
        if gpu_m: specs["Graphics Card (GPU)"] = gpu_m.group(1).strip()

        ram_m = re.search(r"(\d+\s*GB)\s*(?:DDR\d|RAM|Memory)", full_text, re.I)
        if ram_m: specs["RAM"] = ram_m.group(1).strip()

        ssd_m = re.search(r"(\d+\s*(?:GB|TB))\s*(?:SSD|NVMe|HDD)", full_text, re.I)
        if ssd_m: specs["Storage"] = ssd_m.group(1).strip()

        disp_m = re.search(r"(\d+\.?\d*\s*(?:inch|\"))", full_text, re.I)
        if disp_m: specs["Display Size"] = disp_m.group(1).strip()

        res_m = re.search(r"(FHD|QHD|OLED|IPS|2K|4K|1920x1080|2560x1440)", full_text, re.I)
        if res_m: specs["Display Resolution"] = res_m.group(1).strip()

        hz_m = re.search(r"(\d+\s*Hz)", full_text, re.I)
        if hz_m: specs["Refresh Rate"] = hz_m.group(1).strip()

        os_m = re.search(r"(Windows\s*\d+\s*(?:Home|Pro)?|Win\s*\d+|macOS|ChromeOS)", full_text, re.I)
        if os_m:
            raw_os = os_m.group(1).strip()
            specs["Operating System"] = "Windows 11" if raw_os.lower() == "win 11" else ("Windows 10" if raw_os.lower() == "win 10" else raw_os)

        wt_m = re.search(r"(\d+\.?\d*\s*kg)", full_text, re.I)
        if wt_m: specs["Weight"] = wt_m.group(1).strip()

        bat_m = re.search(r"(\d+\s*(?:Hours?|Hrs)\s*(?:Battery|Backup)?)", full_text, re.I)
        if bat_m: specs["Battery Backup"] = bat_m.group(1).strip()

    # 2. Tablet
    elif any(k in cat_lower for k in ["tablet", "ipad"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["tablet", "ipad", "tab"]):
        disp_m = re.search(r"(\d+\.?\d*\s*(?:inch|\")\s*(?:2K|FHD|OLED|LCD)?)", full_text, re.I)
        if disp_m: specs["Display"] = disp_m.group(1).strip()

        proc_m = re.search(r"(Snapdragon\s*[\w\d\+]+|Dimensity\s*[\w\d\+]+|Apple\s*M\d|Bionic\s*A\d+|Helio\s*[\w\d\+]+)", full_text, re.I)
        if proc_m: specs["Processor"] = proc_m.group(1).strip()

        ram_m = re.search(r"(\d+\s*GB)\s*(?:RAM|Memory)", full_text, re.I)
        if ram_m: specs["RAM"] = ram_m.group(1).strip()

        rom_m = re.search(r"(\d+\s*(?:GB|TB))\s*(?:ROM|Storage)", full_text, re.I)
        if rom_m: specs["Storage"] = rom_m.group(1).strip()

        bat_m = re.search(r"(\d{4}\s*mAh)", full_text, re.I)
        if bat_m: specs["Battery"] = bat_m.group(1).strip()

        os_m = re.search(r"(iPadOS|Android\s*\d+)", full_text, re.I)
        if os_m: specs["Operating System"] = os_m.group(1).strip()

        stylus_m = re.search(r"(S[- ]Pen|Stylus|Pencil\s*(?:Included|Supported)?)", full_text, re.I)
        if stylus_m: specs["Stylus Support"] = stylus_m.group(1).strip()

    # 3. Smartwatch
    elif any(k in cat_lower for k in ["smartwatch", "watch", "band"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["smartwatch", "watch", "fitness band"]):
        disp_m = re.search(r"(\d+\.?\d*\s*(?:inch|\")\s*(?:AMOLED|HD|LCD)?)", full_text, re.I)
        if disp_m: specs["Display Type"] = disp_m.group(1).strip()

        bat_m = re.search(r"(\d+\s*Days?\s*(?:Battery|Backup)?)", full_text, re.I)
        if bat_m: specs["Battery Life"] = bat_m.group(1).strip()

        sensors = []
        if re.search(r"SpO2", full_text, re.I): sensors.append("SpO2")
        if re.search(r"Heart\s*Rate", full_text, re.I): sensors.append("Heart Rate")
        if re.search(r"Sleep", full_text, re.I): sensors.append("Sleep Tracking")
        if sensors: specs["Health Sensors"] = ", ".join(sensors)

        gps_m = re.search(r"(Built[- ]in GPS|GPS|In[- ]App GPS)", full_text, re.I)
        if gps_m: specs["GPS"] = gps_m.group(1).strip()

        bt_m = re.search(r"(?:Bluetooth|v)\s*(\d+\.\d+)", full_text, re.I)
        if bt_m: specs["Bluetooth Version"] = f"Bluetooth {bt_m.group(1)}"

        wr_m = re.search(r"(IP67|IP68|5ATM|Water\s*Resistant)", full_text, re.I)
        if wr_m: specs["Water Resistance"] = wr_m.group(1).strip()

    # 4. Headphones / Earbuds / TWS / Audio
    elif any(k in cat_lower for k in ["headphone", "earphone", "earbud", "tws", "audio"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["headphone", "headphones", "earphone", "earphones", "earbud", "earbuds", "tws", "airpods", "headset", "neckband"]):
        drv_m = re.search(r"(\d+\.?\d*\s*mm)\s*(?:Driver)?", full_text, re.I)
        if drv_m: specs["Driver Size"] = drv_m.group(1).strip()

        bat_m = re.search(r"(\d+\s*(?:H|Hours?)\s*(?:Playtime|Playback|Total)?)", full_text, re.I)
        if bat_m: specs["Battery Backup"] = bat_m.group(1).strip()

        anc_m = re.search(r"(ANC|Active Noise Cancel\w*|\d+dB ANC)", full_text, re.I)
        if anc_m: specs["ANC"] = anc_m.group(1).strip()

        enc_m = re.search(r"(ENC|Environmental Noise Cancel\w*|Quad Mic|4 Mic)", full_text, re.I)
        if enc_m: specs["ENC"] = enc_m.group(1).strip()

        bt_m = re.search(r"(?:Bluetooth|v)\s*(\d+\.\d+)", full_text, re.I)
        if bt_m: specs["Bluetooth Version"] = f"Bluetooth {bt_m.group(1)}"

        case_m = re.search(r"(\d{3,4}\s*mAh\s*Case)", full_text, re.I)
        if case_m: specs["Charging Case Battery"] = case_m.group(1).strip()

        wr_m = re.search(r"(IPX\d|IP\d{2})", full_text, re.I)
        if wr_m: specs["Water Resistance"] = wr_m.group(1).strip()

    # 5. TV / Television / Monitor
    elif any(k in cat_lower for k in ["tv", "television", "monitor"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["tv", "television", "monitor"]):
        sz_m = re.search(r"(\d{2,3}\s*(?:inch|\")|\d{2,3}\s*cm)", full_text, re.I)
        if sz_m: specs["Screen Size"] = sz_m.group(1).strip()

        res_m = re.search(r"(4K Ultra HD|Full HD|HD Ready|8K|3840x2160|1920x1080)", full_text, re.I)
        if res_m: specs["Resolution"] = res_m.group(1).strip()

        panel_m = re.search(r"(QLED|OLED|LED|IPS|VA Panel)", full_text, re.I)
        if panel_m: specs["Panel Type"] = panel_m.group(1).strip()

        hz_m = re.search(r"(\d+\s*Hz)", full_text, re.I)
        if hz_m: specs["Refresh Rate"] = hz_m.group(1).strip()

        os_m = re.search(r"(Google TV|Android TV|WebOS|Tizen|Fire TV)", full_text, re.I)
        if os_m: specs["Smart TV Platform"] = os_m.group(1).strip()

        hdr_m = re.search(r"(Dolby Vision|HDR10\+|HDR10)", full_text, re.I)
        if hdr_m: specs["HDR Support"] = hdr_m.group(1).strip()

    # 6. Air Conditioner (AC)
    elif any(k in cat_lower for k in ["ac", "air conditioner"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["ac", "air conditioner", "split ac", "window ac"]):
        cap_m = re.search(r"(\d+\.?\d*\s*Ton)", full_text, re.I)
        if cap_m: specs["Capacity"] = cap_m.group(1).strip()

        star_m = re.search(r"(\d\s*Star)", full_text, re.I)
        if star_m: specs["Star Rating"] = star_m.group(1).strip()

        inv_m = re.search(r"(Dual Inverter|Inverter|Smart Inverter)", full_text, re.I)
        if inv_m: specs["Inverter"] = inv_m.group(1).strip()

        cop_m = re.search(r"(Copper Condenser|100% Copper)", full_text, re.I)
        if cop_m: specs["Copper Condenser"] = "100% Copper" if cop_m else None

        modes_m = re.search(r"(\d+-in-1 Convertible|Convertible)", full_text, re.I)
        if modes_m: specs["Cooling Modes"] = modes_m.group(1).strip()

        pwr_m = re.search(r"(\d+\s*kWh)", full_text, re.I)
        if pwr_m: specs["Power Consumption"] = pwr_m.group(1).strip()

        war_m = re.search(r"(\d+\s*Years?\s*(?:Compressor)?\s*Warranty)", full_text, re.I)
        if war_m: specs["Warranty"] = war_m.group(1).strip()

    # 7. Refrigerator / Fridge
    elif any(k in cat_lower for k in ["refrigerator", "fridge"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["refrigerator", "fridge"]):
        cap_m = re.search(r"(\d+\s*(?:L|Litre|Litres))", full_text, re.I)
        if cap_m: specs["Capacity"] = cap_m.group(1).strip()

        star_m = re.search(r"(\d\s*Star)", full_text, re.I)
        if star_m: specs["Star Rating"] = star_m.group(1).strip()

        comp_m = re.search(r"(Smart Inverter|Digital Inverter|Inverter Compressor)", full_text, re.I)
        if comp_m: specs["Compressor Type"] = comp_m.group(1).strip()

        conv_m = re.search(r"(Convertible|Auto Smart Convertible)", full_text, re.I)
        if conv_m: specs["Convertible Mode"] = conv_m.group(1).strip()

        cool_m = re.search(r"(Multi Air Flow|Twin Cooling\+|Direct Cool|Frost Free)", full_text, re.I)
        if cool_m: specs["Cooling Technology"] = cool_m.group(1).strip()

        war_m = re.search(r"(\d+\s*Years?\s*Warranty)", full_text, re.I)
        if war_m: specs["Warranty"] = war_m.group(1).strip()

    # 8. Phone / Mobile
    elif any(k in cat_lower for k in ["phone", "mobile", "smartphone"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["phone", "mobile", "smartphone", "iphone", "galaxy", "poco", "iqoo", "redmi", "realme", "oneplus", "pixel"]):
        proc_m = re.search(r"(Snapdragon\s*[\w\d\+]+|Dimensity\s*[\w\d\+]+|Helio\s*[\w\d\+]+|Bionic\s*A\d+|Tensor\s*G\d+|Exynos\s*[\w\d]+|Unisoc\s*[\w\d]+)", full_text, re.I)
        if proc_m: specs["Processor"] = proc_m.group(1).strip()

        ram_m = re.search(r"(\d+\s*GB)\s*(?:RAM|Memory)", full_text, re.I) or re.search(r"(\d+GB)\s*(?:\+|RAM|/)", full_text, re.I)
        if ram_m: specs["RAM"] = ram_m.group(1).strip()

        rom_m = re.search(r"(\d+\s*(?:GB|TB))\s*(?:ROM|Storage|Internal)", full_text, re.I) or re.search(r"(?:RAM\s*,\s*|/\s*|\b)(\d+\s*(?:GB|TB))\s*(?:Storage)?", full_text, re.I)
        if rom_m: specs["Storage"] = rom_m.group(1).strip()

        disp_m = re.search(r"(\d+\.?\d*\s*(?:inch|\"|cm)?\s*(?:AMOLED|Super AMOLED|OLED|FHD\+|HD\+|LCD|IPS)[\w\s]*)", full_text, re.I)
        if disp_m: specs["Display"] = disp_m.group(1).strip()

        hz_m = re.search(r"(\d+\s*Hz)", full_text, re.I)
        if hz_m: specs["Display Refresh Rate"] = hz_m.group(1).strip()

        bat_m = re.search(r"(\d{4}\s*mAh)", full_text, re.I)
        if bat_m: specs["Battery Capacity"] = bat_m.group(1).strip()

        chg_m = re.search(r"(\d+W\s*(?:Fast\s*)?Charg\w*)", full_text, re.I)
        if chg_m: specs["Charging Speed"] = chg_m.group(1).strip()

        cam_m = re.search(r"(\d+\s*MP[\w\s\+\-]*Camera|\d+\s*MP\s*OIS|\d+\s*MP\s*(?:Rear|Dual|Triple|Quad))", full_text, re.I)
        if cam_m: specs["Camera"] = cam_m.group(1).strip()

        os_m = re.search(r"(Android\s*\d+|iOS\s*\d+|HyperOS|OxygenOS|Funtouch)", full_text, re.I)
        if os_m: specs["Operating System"] = os_m.group(1).strip()

        if re.search(r"\b5G\b", full_text, re.I):
            specs["5G Support"] = "Yes"

    # Fallback: if specs dict is empty or contains fewer than 2 items, extract generic attributes
    if len(specs) < 2:
        rs = re.search(r"(\d+\s*GB[\s/]*\d+\s*(?:GB|TB))", full_text, re.I)
        if rs: specs["Memory & Storage"] = rs.group(1).strip()

        sz = re.search(r"(\d+\.?\d*\s*(?:inch|\"))", full_text, re.I)
        if sz and "Screen Size" not in specs and "Display" not in specs:
            specs["Display Size"] = sz.group(1).strip()

        conn = re.search(r"(5G|4G|WiFi|Bluetooth|Wireless)", full_text, re.I)
        if conn: specs["Connectivity"] = conn.group(1).strip()

    return specs


def filter_and_describe_products(products: list[dict], state: dict) -> list[dict]:
    """
    Filter out mismatched products strictly, rank them, extract structured specifications, generate AI summaries, and categorize offers.
    """
    if not products:
        return []

    # STRICT PERFORMANCE RULE: Limit candidate list to top 5 BEFORE LLM invocation
    products = products[:5]

    # Ensure deterministic specs extraction runs on all candidate products as base
    category_req = state.get("category", "")
    for p in products:
        p_specs = p.get("specifications") or {}
        auto_specs = extract_electronics_specifications(p.get("name", ""), p.get("features", []), category_req)
        if isinstance(p_specs, dict):
            p["specifications"] = {**auto_specs, **p_specs}
        else:
            p["specifications"] = auto_specs

    system_prompt = """You are an expert AI shopping assistant for Amazon India. I will provide a list of scraped products and the user's shopping requirements.

User Requirements:
Intent: {shopping_intent}
Category: {category}
Product: {product}
Budget: {budget}
Filters: {filters}

CRITICAL FILTERING RULES (FILTER FIRST, RANK LATER):
1. FILTERING MUST BE STRICT:
   - Category Match: You MUST classify each scraped product's category. If it does not belong to the requested category ({category}), REJECT IT IMMEDIATELY. For example, if the requested category is Electronics, reject Clothing, Shoes, Fashion, Jewellery, etc. This rule is absolute.
   - Brand Match: If a brand is specified (e.g. Acer, Lenovo, Dell), DISCARD any other brand.
   - Budget Match: DISCARD products exceeding the budget cap.
   - Spec Match (GPU, Processor, RAM): IF USER REQUESTS AN RTX 4050, DISCARD RTX 2050, RTX 3050, RTX 4060, RTX 4070. IF USER REQUESTS 16GB RAM, DISCARD 8GB RAM.
   - If NO products match all criteria, return an empty JSON array [].

2. RANKING (ONLY AFTER FILTERING):
   - Pay attention to shopping_intent ({shopping_intent}). If it is a deal intent (Deals, Best Sellers, Trending, Discounts, Lightning Deals), prioritize Higher Discounts, Better Ratings, More Reviews, Better Value, Deal Badges, Coupon Availability, and Limited Time Offers.
   - Rank matching items by: Intent Match > Exact Spec Match > High Rating > Review Count > Best Discount.

3. FOR TOP MATCHING PRODUCTS:
   a. Extract key structured specs into "specifications" (e.g. "Processor": "Intel Core i7-13620H", "GPU": "NVIDIA RTX 4050 6GB", "RAM": "16GB DDR5", "Storage": "512GB SSD", "Display": "15.6 FHD 144Hz", "Operating System": "Windows 11 Home").
   b. Generate "description": A MANDATORY product description (MAX 40 WORDS) using this priority:
      - Priority 1: If structured specifications exist, generate description from them.
      - Priority 2: If only the title exists, generate a short description using the title.
      - Priority 3: If both are unavailable, infer ONLY the product category.
      RULES: Never leave blank. Never repeat the product title. Never invent specifications. Only describe what can be reasonably inferred.
   c. Generate "ai_advisor": A concise, friendly AI recommendation (MAX 50 WORDS) explaining why this product is a great choice. Start with "⭐ My Recommendation\n" or "💡 ". Do NOT use the word "description".
   d. Categorize all offers into: emi_offers, credit_offers, debit_offers, cashback_offers, exchange_offers, coupon_offers, partner_offers.

Output strictly as a JSON array of the top products:
[
  {{
    "index": <original index of the product in the provided list>,
    "specifications": {{
      "Processor": "Intel Core i7-13620H",
      "GPU": "NVIDIA RTX 4050 6GB",
      "RAM": "16GB DDR5",
      "Storage": "512GB SSD",
      "Display": "15.6-inch FHD 144Hz",
      "Operating System": "Windows 11 Home"
    }},
    "description": "Powered by Intel Core i7 and RTX4050 graphics, this laptop is excellent for gaming, programming and creative workloads.",
    "ai_advisor": "⭐ My Recommendation\nThis laptop offers the best value because it has an RTX 4050, 16GB RAM and excellent reviews while staying within your budget.",
    "emi_offers": ["No Cost EMI starting from ₹3,499/month"],
    "credit_offers": ["10% Instant Discount on HDFC Credit Cards"],
    "debit_offers": [],
    "cashback_offers": ["5% Cashback on Amazon Pay ICICI Card"],
    "exchange_offers": ["Exchange bonus up to ₹8,000"],
    "coupon_offers": [],
    "partner_offers": []
  }}
]
No extra text, just the JSON array.
"""
    shopping_intent_req = state.get('shopping_intent', '')
    category_req = state.get('category', '')
    product_req = state.get('product', '')
    budget_req = state.get('budget', '')
    filters_req = state.get('filters', '')
    marketplace = state.get('marketplace', '')
    
    sys_content = system_prompt.format(
        marketplace=marketplace,
        shopping_intent=shopping_intent_req,
        category=category_req,
        product=product_req,
        budget=budget_req,
        filters=filters_req
    )

    user_content = "Scraped Products:\n"
    for i, p in enumerate(products[:20]):
        price_str = f"₹{p['price']}" if p.get('price') else "Unknown"
        feats = ", ".join(p.get('features', []))
        offs = ", ".join(p.get('offers', []))
        user_content += f"[{i}] Name: {p['name']} | Price: {price_str} | Rating: {p.get('rating')} | Reviews: {p.get('review_count')} | Features: {feats} | Scraped Offers: {offs}\n"

    messages = [
        {"role": "system", "content": sys_content},
        {"role": "user", "content": user_content}
    ]

    result = chat(messages, temperature=0.0)
    
    if result.startswith("__OLLAMA"):
        return products[:5]

    try:
        if "[" in result and "]" in result:
            result = result[result.find("["):result.rfind("]")+1].strip()
        elif "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].strip()
            
        filtered_results = json.loads(result, strict=False)
        
        final_products = []
        for item in filtered_results:
            idx = item.get("index")
            adv = item.get("ai_advisor", "")
            desc = item.get("description", "")
            specs = item.get("specifications") or {}
            if isinstance(idx, int) and 0 <= idx < len(products):
                p = products[idx]
                p["ai_advisor"] = adv
                p["description"] = desc
                
                auto_specs = p.get("specifications") or {}
                if isinstance(specs, dict) and len(specs) > 0:
                    p["specifications"] = {**auto_specs, **specs}
                else:
                    p["specifications"] = auto_specs
                
                # Attach offer categories
                for key in ["emi_offers", "credit_offers", "debit_offers", "cashback_offers", "exchange_offers", "coupon_offers", "partner_offers"]:
                    val = item.get(key, [])
                    if isinstance(val, list):
                        p[key] = [str(x) for x in val if isinstance(x, str) and len(x.strip()) > 3]
                    elif isinstance(val, str) and len(val.strip()) > 3:
                        p[key] = [val.strip()]
                    else:
                        p[key] = []
                final_products.append(p)
                
        return final_products
        
    except Exception as e:
        clean_out = str(result).encode('ascii', 'ignore').decode('ascii')
        print(f"Error parsing filter JSON: {e}\nRaw output: {clean_out}")
        return products[:5]


def create_reminder(user_message: str, history: list[dict]) -> dict:
    """
    Extract reminder details from the user's message.
    """
    system_prompt = """Extract reminder details from the user's message.
Output ONLY valid JSON.
Identify if it is a Price Alert (e.g. "Notify me if RTX4060 laptops go below ₹80000").
Format:
{
  "reminder_id": "Generate a short random string or leave empty",
  "category": "e.g., Laptop, AC, TV",
  "product": "Product string",
  "brand": "brand if any",
  "budget": "budget info (e.g., 80000, under 120000) or null",
  "specifications": "specs if any",
  "marketplace": "amazon",
  "reminder_type": "One Time, Daily, Weekly, Monthly, Specific Date, Price Alert, Deal Alert, Festival Reminder",
  "reminder_date": "Date if specified (e.g. June 5)",
  "reminder_time": "Time if specified (e.g. 9:25 PM)",
  "created_time": "Current time or empty string",
  "status": "Active"
}"""
    
    recent = history[-4:] if len(history) > 4 else history
    messages = [
        {"role": "system", "content": system_prompt},
        *recent,
        {"role": "user", "content": f"Extract reminder details from: {user_message}"},
    ]

    result = chat(messages, temperature=0.0)
    
    if result.startswith("__OLLAMA"):
        return {"error": result}
        
    try:
        if "{" in result and "}" in result:
            result = result[result.find("{"):result.rfind("}")+1].strip()
        elif "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].strip()
            
        return json.loads(result)
    except Exception as e:
        print(f"Error parsing JSON from LLM: {e}")
        return {"error": "Failed to parse reminder"}
