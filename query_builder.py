"""
query_builder.py — Python Search Query Builder for Trevor AI Shopping Assistant.
Constructs compact, highly optimized Amazon marketplace queries from structured vision metadata.
"""

import re
import logging

logger = logging.getLogger("trevor.query_builder")


def build_amazon_search_query(vision_data: dict) -> str:
    """
    Constructs a clean, compact Amazon search query from structured vision metadata.
    Priority order: Brand -> Series -> Model -> Category -> Variant -> (Color for clothing only).
    Never prepends weak visual terms like 'Unisex', 'Black', 'Multi-Color' to electronics.
    """
    if not isinstance(vision_data, dict):
        return ""

    tokens = []

    def clean_val(val):
        if val is None:
            return None
        s = str(val).strip()
        if s.lower() in {"none", "null", "unknown", "n/a", ""}:
            return None
        return s

    category = clean_val(vision_data.get("category"))
    sub_category = clean_val(vision_data.get("sub_category")) or clean_val(vision_data.get("series"))
    brand = clean_val(vision_data.get("brand"))
    model = clean_val(vision_data.get("model"))
    variant = clean_val(vision_data.get("variant"))
    p_type = clean_val(vision_data.get("product_type")) or ""

    gender = clean_val(vision_data.get("gender"))
    style = clean_val(vision_data.get("style") or vision_data.get("occasion"))
    pattern = clean_val(vision_data.get("pattern"))
    p_color = clean_val(vision_data.get("primary_color") or vision_data.get("color"))
    s_color = clean_val(vision_data.get("secondary_color"))
    material = clean_val(vision_data.get("material"))
    sleeve = clean_val(vision_data.get("sleeve"))
    collar = clean_val(vision_data.get("collar"))
    fit = clean_val(vision_data.get("fit"))

    is_electronic = p_type.upper() in {"PHONE", "LAPTOP", "TV", "APPLIANCE", "HEADPHONES", "WATCH"} or \
                    any(k in (category or "").lower() for k in ["laptop", "phone", "tv", "refrigerator", "ac", "headphone", "watch", "camera"])

    if is_electronic:
        # Priority for Electronics: Brand -> Series -> Model -> Category -> Variant
        if brand: tokens.append(brand.title())
        if sub_category and sub_category.lower() not in (brand or "").lower(): tokens.append(sub_category.title())
        if model and model.lower() not in " ".join(tokens).lower(): tokens.append(model.title())
        if category and category.lower() not in " ".join(tokens).lower(): tokens.append(category.title())
        if variant: tokens.append(variant)
    else:
        # Priority for Fashion/Clothing: Gender -> Style -> Pattern -> Category -> Brand -> Model -> Color -> Material -> Sleeve -> Fit
        if gender: tokens.append(gender.title())
        if style: tokens.append(style.title())
        if pattern: tokens.append(pattern.title())
        if brand: tokens.append(brand.title())
        if model: tokens.append(model.title())
        if category and category.lower() not in " ".join(tokens).lower(): tokens.append(category.title())
        if p_color: tokens.append(p_color.title())
        if s_color and s_color.lower() != (p_color or "").lower(): tokens.append(s_color.title())
        if material: tokens.append(material.title())
        if sleeve: tokens.append(sleeve.title())
        if collar: tokens.append(collar.title())
        if fit:
            fit_str = fit.title()
            if "fit" not in fit_str.lower(): fit_str += " Fit"
            tokens.append(fit_str)

    # Word deduplication preserving sequence
    seen_words = set()
    final_words = []
    for token in tokens:
        for word in token.split():
            w_clean = re.sub(r'[^\w\d\-]', '', word)
            w_lower = w_clean.lower()
            if w_lower and w_lower not in seen_words:
                seen_words.add(w_lower)
                final_words.append(word)

    query = " ".join(final_words).strip()
    logger.info(f"[QueryBuilder] Built Amazon query: '{query}'")
    return query


def generate_category_queries(vision_data: dict) -> list[tuple[str, bool]]:
    """
    Category-Specific Search Query Strategy (Stage 6):
    Builds progressive search candidates tailored specifically for:
    - Electronics/Laptops: Brand -> Series -> Model -> Storage/RAM/GPU -> Category
    - Phones: Brand -> Series -> Storage -> Variant -> Category
    - Clothing: Gender -> Brand -> Category -> Fit -> Sleeve -> Pattern
    - Shoes: Brand -> Series -> Gender -> Purpose -> Category
    - Watches: Brand -> Series -> Dial -> Category
    Returns list of (query_string, is_exact_attempt) tuples.
    """
    if not isinstance(vision_data, dict):
        return [("Products", False)]

    def clean(val):
        if val is None: return None
        s = str(val).strip()
        if s.lower() in {"none", "null", "unknown", "n/a", ""}: return None
        return s

    p_type = (clean(vision_data.get("product_type")) or "").upper()
    category = clean(vision_data.get("category")) or "Product"
    brand = clean(vision_data.get("brand"))
    series = clean(vision_data.get("series") or vision_data.get("sub_category"))
    model = clean(vision_data.get("model"))
    variant = clean(vision_data.get("variant"))
    gender = clean(vision_data.get("gender"))
    pattern = clean(vision_data.get("pattern"))
    fit = clean(vision_data.get("fit"))
    sleeve = clean(vision_data.get("sleeve"))
    style = clean(vision_data.get("style") or vision_data.get("occasion"))
    p_color = clean(vision_data.get("primary_color") or vision_data.get("color"))

    specs = vision_data.get("specifications") or {}
    storage = clean(specs.get("storage") or specs.get("Storage"))
    ram = clean(specs.get("ram") or specs.get("RAM"))
    gpu = clean(specs.get("gpu") or specs.get("GPU"))

    candidates = []
    seen = set()

    def clean_query_words(raw_parts: list[str]) -> str:
        words = []
        seen_words = set()
        for part in raw_parts:
            if not part: continue
            for w in part.split():
                w_lower = re.sub(r'[^\w\d\-]', '', w).lower()
                if w_lower and w_lower not in seen_words:
                    seen_words.add(w_lower)
                    words.append(w)
        return " ".join(words)

    def add_cand(raw_parts: list[str], is_exact: bool):
        q_clean = clean_query_words(raw_parts)
        q_key = q_clean.lower()
        if q_key and q_key not in seen:
            seen.add(q_key)
            candidates.append((q_clean, is_exact))

    # Strategy 1: Electronics / Laptops
    if p_type == "LAPTOP" or "laptop" in category.lower():
        add_cand([brand, series, model, gpu, ram, category], is_exact=True)
        add_cand([model or series, category], is_exact=True)
        add_cand([brand, series, category], is_exact=False)
        add_cand([brand, category], is_exact=False)
        add_cand([category], is_exact=False)

    # Strategy 2: Phones / Smartphones
    elif p_type == "PHONE" or any(k in category.lower() for k in ["phone", "mobile", "smartphone"]):
        add_cand([brand, series, model, storage or variant, category], is_exact=True)
        add_cand([brand, model or series], is_exact=True)
        add_cand([brand, series, category], is_exact=False)
        add_cand([brand, category], is_exact=False)

    # Strategy 3: Clothing / Fashion
    elif p_type == "CLOTHING" or any(k in category.lower() for k in ["shirt", "t-shirt", "jeans", "jacket", "dress"]):
        add_cand([gender, brand, category, fit, sleeve, pattern], is_exact=True)
        add_cand([gender, category, pattern, p_color], is_exact=True)
        add_cand([brand, category], is_exact=False)

    # Strategy 4: Shoes / Footwear
    elif p_type == "SHOES" or any(k in category.lower() for k in ["shoe", "shoes", "sneaker", "footwear"]):
        add_cand([brand, series or model, gender, style, category], is_exact=True)
        add_cand([brand, category, style], is_exact=False)

    # Strategy 5: Watches
    elif p_type == "WATCH" or "watch" in category.lower():
        add_cand([brand, series, model, category], is_exact=True)
        add_cand([brand, category], is_exact=False)

    # Default Fallback Strategy
    else:
        add_cand([brand, series, model, category], is_exact=True)
        add_cand([brand, category], is_exact=False)

    return candidates if candidates else [("Products", False)]


def build_identified_product_name(vision_data: dict) -> str:
    """
    Constructs a clean human-readable product display name WITHOUT 'None' or 'Unknown'.
    Example:
    Input: gender='men', style='casual', pattern='plaid check', category='shirt'
    Output: "Men's Casual Plaid Check Shirt"
    Input: brand='Apple', model='iPhone 16 Pro', color='White Titanium'
    Output: "White Apple iPhone 16 Pro"
    """
    if not isinstance(vision_data, dict):
        return "Product"

    def clean_val(val):
        if val is None:
            return None
        s = str(val).strip()
        if s.lower() in {"none", "null", "unknown", "n/a", ""}:
            return None
        return s

    brand = clean_val(vision_data.get("brand"))
    model = clean_val(vision_data.get("model"))
    color = clean_val(vision_data.get("primary_color") or vision_data.get("color"))
    category = clean_val(vision_data.get("category")) or "Product"
    gender = clean_val(vision_data.get("gender"))
    style = clean_val(vision_data.get("style"))
    pattern = clean_val(vision_data.get("pattern"))

    # If Brand or Model is present (e.g. Apple iPhone 16 Pro)
    if brand or model:
        parts = []
        if color: parts.append(color.title())
        if brand: parts.append(brand.title())
        if model: parts.append(model.title())
        return " ".join(parts).strip()

    # If unbranded item, build descriptive title (e.g. Men's Casual Plaid Check Shirt)
    desc_parts = []
    if gender:
        g_str = gender.title()
        if not g_str.endswith("'s"):
            g_str += "'s"
        desc_parts.append(g_str)
    if style:
        desc_parts.append(style.title())
    if pattern:
        desc_parts.append(pattern.title())
    desc_parts.append(category.title())

    return " ".join(desc_parts).strip()
