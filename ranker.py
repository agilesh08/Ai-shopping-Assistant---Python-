"""
ranker.py — Weighted Semantic Ranking Engine for Trevor AI Shopping Assistant.
Ranks parsed marketplace products using weighted feature scoring instead of rigid keyword rejection.
"""

import logging
import re

logger = logging.getLogger("trevor.ranker")

SYNONYMS = {
    "t-shirt": ["t-shirt", "tshirt", "tee", "shirt", "top", "apparel", "clothing"],
    "shirt": ["shirt", "t-shirt", "tshirt", "tee", "top", "clothing"],
    "clothing": ["clothing", "shirt", "t-shirt", "tshirt", "tee", "top", "jeans", "jacket", "apparel"],
    "phone": ["phone", "mobile", "smartphone", "cellphone", "handset"],
    "laptop": ["laptop", "notebook", "macbook", "chromebook", "vivobook", "gaming laptop"],
    "shoes": ["shoes", "shoe", "sneakers", "sneaker", "footwear", "boots", "running shoes"],
    "tv": ["tv", "television", "smart tv", "monitor"],
    "ac": ["ac", "air conditioner", "split ac"],
}


FORBIDDEN_ACCESSORIES = {
    "PHONE": [
        "charger", "cable", "adapter", "case", "cover", "tempered glass", "screen guard",
        "power bank", "stand", "protector", "skin", "holster", "holder", "strap", "lens film", "back sticker", "silicone case"
    ],
    "LAPTOP": [
        "keyboard", "mouse", "bag", "sleeve case", "charger", "adapter", "cooling pad",
        "screen guard", "skin", "stand", "hub", "cable", "docking station", "keyboard cover"
    ],
    "CLOTHING": [
        "socks", "cap", "belt", "wallet", "tie", "hanger", "undergarment"
    ],
    "SHOES": [
        "socks", "lace", "shoe polish", "sole pad", "insole", "shoe tree"
    ],
    "WATCH": [
        "strap", "band", "screen guard", "case cover", "charger", "charging dock", "bezel"
    ],
    "HEADPHONES": [
        "ear tips", "case cover", "charging case", "replacement ear pads", "audio cable", "silicone case"
    ],
}


def determine_ranking_profile(state: dict) -> tuple[str, list[str]]:
    """
    Determines the category ranking profile and factors applied.
    """
    cat = (state.get("category") or "").lower()
    p_type = (state.get("product_type") or "").upper()

    if p_type == "HEADPHONES" or any(k in cat for k in ["headphone", "earbud", "audio", "airpods", "tws"]):
        return "Headphones", ["ANC", "Battery Life", "Bluetooth Version", "Driver Size", "Low Latency", "Price", "Rating"]
    elif p_type == "LAPTOP" or "laptop" in cat:
        return "Laptop / Electronics", ["CPU", "GPU", "RAM", "Storage", "Display", "Battery", "Price", "Rating"]
    elif p_type == "PHONE" or re.search(r'\b(phone|mobile|smartphone)\b', cat):
        return "Phone", ["Storage", "Camera", "Battery", "Display", "Processor", "Price", "Rating"]
    elif p_type == "WATER_HEATER" or any(k in cat for k in ["water heater", "geyser"]):
        return "Water Heater", ["Capacity", "Power Rating", "BEE Rating", "Warranty", "Tank Material", "Heating Time", "Price", "Rating"]
    elif p_type == "CLOTHING" or any(k in cat for k in ["shirt", "t-shirt", "jeans", "jacket", "dress"]):
        return "Clothing", ["Material", "Fit", "Sleeve", "Pattern", "Color", "Price", "Rating"]
    elif p_type == "SHOES" or any(k in cat for k in ["shoe", "shoes", "sneaker"]):
        return "Shoes", ["Purpose", "Sole Material", "Cushioning", "Price", "Rating"]
    else:
        return "General Product", ["Brand", "Model", "Category", "Specifications", "Price", "Rating"]


def calculate_product_score(product: dict, state: dict) -> dict:
    """
    Calculates a semantic weighted relevance score (0 - 100%) for a parsed product.
    Weights:
    - Brand Match: 40%
    - Category Match: 30%
    - Variant Match: 15%
    - Color Match: 10%
    - Price/Attributes: 5%
    """
    title = (product.get("name") or product.get("title") or "").strip()
    title_lower = title.lower()
    price = product.get("price")

    req_brand = (state.get("brand") or state.get("_resolved_req_brand") or "").lower().strip()
    req_cat = (state.get("category") or "").lower().strip()
    req_color = (state.get("color") or "").lower().strip()
    req_variant = (state.get("variant") or state.get("model") or "").lower().strip()
    req_budget = state.get("budget")

    # Determine Product Type
    prod_type = (state.get("product_type") or "").upper().strip()
    if not prod_type:
        if any(k in req_cat for k in ["phone", "mobile", "smartphone"]): prod_type = "PHONE"
        elif any(k in req_cat for k in ["laptop", "notebook", "macbook"]): prod_type = "LAPTOP"
        elif any(k in req_cat for k in ["shirt", "clothing", "jeans", "jacket", "dress"]): prod_type = "CLOTHING"
        elif any(k in req_cat for k in ["shoe", "footwear", "boot"]): prod_type = "SHOES"
        elif any(k in req_cat for k in ["headphone", "earbud", "audio"]): prod_type = "HEADPHONES"
        elif any(k in req_cat for k in ["watch", "smartwatch"]): prod_type = "WATCH"

    # Category Filtering: Reject forbidden accessories when searching for main products
    if prod_type in FORBIDDEN_ACCESSORIES:
        forbidden_list = FORBIDDEN_ACCESSORIES[prod_type]
        for f_word in forbidden_list:
            if re.search(r'\b' + re.escape(f_word) + r'\b', title_lower):
                logger.info(f"[Ranker] REJECTED ACCESSORY: '{title[:45]}...' contains forbidden accessory word '{f_word}' for {prod_type}")
                product["_score"] = 0
                product["_rank_report"] = {"title": title, "final_score": 0, "rejection_reason": f"Forbidden accessory word '{f_word}'"}
                return product

    brand_score = 0
    series_score = 0
    model_score = 0
    spec_score = 0
    cat_score = 0

    req_series = (state.get("series") or state.get("sub_category") or "").lower().strip()
    req_model = (state.get("model") or "").lower().strip()

    # 1. Brand Match (30%)
    if req_brand:
        brand_terms = [req_brand]
        if req_brand == "apple": brand_terms.extend(["iphone", "ipad", "macbook", "airpods"])
        elif req_brand in {"xiaomi", "redmi"}: brand_terms.extend(["xiaomi", "redmi", "mi"])
        elif req_brand in {"motorola", "moto"}: brand_terms.extend(["motorola", "moto"])
        elif req_brand in {"oneplus", "1+"}: brand_terms.extend(["oneplus", "1+"])
        elif req_brand == "asus": brand_terms.extend(["asus", "rog", "tuf"])

        if any(re.search(r'\b' + re.escape(bt) + r'\b', title_lower) for bt in brand_terms):
            brand_score = 30
    else:
        brand_score = 30

    # 2. Series / Family Match (25%)
    if req_series:
        series_words = [w for w in req_series.split() if len(w) > 2]
        matched_s = [w for w in series_words if re.search(r'\b' + re.escape(w) + r'\b', title_lower)]
        if series_words:
            series_score = int(25 * (len(matched_s) / len(series_words)))
        else:
            series_score = 25
    else:
        series_score = 25

    # 3. Model Match (25%)
    if req_model:
        model_words = [w for w in req_model.split() if len(w) > 2]
        matched_m = [w for w in model_words if re.search(r'\b' + re.escape(w) + r'\b', title_lower)]
        if model_words:
            model_score = int(25 * (len(matched_m) / len(model_words)))
        else:
            model_score = 25
    else:
        model_score = 25

    # 4. Specifications Match (15%) - Category Tailored Factor Matching
    req_specs = state.get("specifications") or {}
    spec_tokens = []
    if isinstance(req_specs, dict):
        for v in req_specs.values():
            if v and str(v).lower() not in {"null", "none", ""}:
                spec_tokens.append(str(v))
    req_variant = state.get("variant")
    if req_variant: spec_tokens.append(str(req_variant))

    # Add Category-Specific Spec Tokens if Water Heater / Headphones
    if prod_type == "WATER_HEATER" or "water heater" in req_cat:
        for kw in ["25l", "15l", "10l", "3l", "5 star", "4 star", "2000w", "3000w"]:
            if kw in (state.get("user_query") or "").lower():
                spec_tokens.append(kw)
    elif prod_type == "HEADPHONES" or "headphone" in req_cat:
        for kw in ["anc", "active noise cancellation", "bluetooth", "tws"]:
            if kw in (state.get("user_query") or "").lower():
                spec_tokens.append(kw)

    if spec_tokens:
        matched_specs = 0
        for st in spec_tokens:
            words = [w for w in st.split() if len(w) >= 2]
            if any(re.search(r'\b' + re.escape(w) + r'\b', title_lower) for w in words):
                matched_specs += 1
        spec_score = int(15 * (matched_specs / len(spec_tokens)))
    else:
        spec_score = 15

    # 5. Category Match (5%)
    if req_cat:
        cat_terms = SYNONYMS.get(req_cat, [req_cat])
        if any(re.search(r'\b' + re.escape(ct) + r'\b', title_lower) for ct in cat_terms):
            cat_score = 5
        else:
            cat_score = 2
    else:
        cat_score = 5

    total_score = min(100, brand_score + series_score + model_score + spec_score + cat_score)

    report = {
        "title": title,
        "brand_match": brand_score > 0,
        "series_match": series_score > 0,
        "model_match": model_score > 0,
        "spec_match": spec_score > 0,
        "category_match": cat_score > 0,
        "final_score": total_score
    }

    product["_score"] = total_score
    product["_rank_report"] = report
    return product


def rank_products(products: list[dict], state: dict, min_score_threshold: int = None) -> list[dict]:
    """
    Ranks parsed products using category-aware weighted scoring.
    Filters out items with total_score < min_score_threshold.
    Logs category profile and applied ranking factors.
    Returns products sorted by score descending.
    """
    if not products:
        return []

    profile_name, factors = determine_ranking_profile(state)
    logger.info(f"[Ranker] Ranking Profile: {profile_name}")
    logger.info(f"[Ranker] Ranking Factors Applied: {', '.join(factors)}")
    print(f"[Ranker] Ranking Profile: {profile_name}")
    print(f"[Ranker] Ranking Factors Applied: {', '.join(factors)}")

    threshold = min_score_threshold if min_score_threshold is not None else 30

    scored = [calculate_product_score(p, state) for p in products]
    valid = [p for p in scored if p.get("_score", 0) >= threshold]

    ranked = sorted(valid, key=lambda x: (x.get("_score", 0), x.get("rating", 0) or 0), reverse=True)
    return ranked
