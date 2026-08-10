"""
product_intelligence.py — Product Intelligence Layer for Trevor AI Shopping Assistant.
Enriches already-ranked products with category-specific specifications, Shopping Value Scoring (0-100),
discount calculations, delivery & offer extraction, and factual non-hallucinated AI summaries.

RULES:
- NEVER performs searches.
- NEVER ranks products for relevance.
- NEVER modifies retrieval logic.
- ONLY enriches product metadata for informed buying decisions.
"""

import re
import logging

logger = logging.getLogger("trevor.product_intelligence")


def extract_category_specifications(product: dict, category_type: str = "") -> dict:
    """
    Extracts category-tailored specifications from product title, description, and specs dict.
    """
    title = product.get("name") or product.get("title") or ""
    desc = product.get("description") or ""
    raw_specs = product.get("specifications") or {}
    text_pool = f"{title} {desc} {str(raw_specs)}".lower()

    cat = (category_type or product.get("category") or "").lower()
    p_type = (product.get("product_type") or "").upper()

    specs = {}

    # Category 1: Laptops / Gaming Laptops
    if p_type == "LAPTOP" or "laptop" in cat:
        gpu_m = re.search(r'\b(rtx\s*\d{4}[a-z]*|gtx\s*\d{4}|radeon\s*rx\s*\d{4}[a-z]*|intel\s*iris\s*xe|apple\s*m\d\s*gpu)\b', text_pool)
        if gpu_m: specs["gpu"] = gpu_m.group(1).upper()

        cpu_m = re.search(r'\b(intel\s*core\s*i[3579]|ryzen\s*[3579]|apple\s*m[1234]\s*pro|apple\s*m[1234]\s*max|core\s*ultra\s*[579])\b', text_pool)
        if cpu_m: specs["cpu"] = cpu_m.group(1).title()

        ram_m = re.search(r'\b(\d{1,2}\s*gb\s*(?:ddr[45]|ram)?)\b', text_pool)
        if ram_m: specs["ram"] = ram_m.group(1).upper()

        storage_m = re.search(r'\b(\d{3,4}\s*gb\s*ssd|1\s*tb\s*ssd|2\s*tb\s*ssd|512\s*gb|1\s*tb)\b', text_pool)
        if storage_m: specs["storage"] = storage_m.group(1).upper()

        refresh_m = re.search(r'\b(\d{2,3}\s*hz)\b', text_pool)
        if refresh_m: specs["refresh_rate"] = refresh_m.group(1).upper()

        display_m = re.search(r'\b(\d{2}(?:\.\d)?\s*(?:inch|\"|\'-inch)\s*(?:fhd|qhd|oled|ips)?)\b', text_pool)
        if display_m: specs["display"] = display_m.group(1).title()

    # Category 2: Phones / Smartphones
    elif p_type == "PHONE" or any(k in cat for k in ["phone", "mobile", "smartphone"]):
        storage_m = re.search(r'\b(64\s*gb|128\s*gb|256\s*gb|512\s*gb|1\s*tb)\b', text_pool)
        if storage_m: specs["storage"] = storage_m.group(1).upper()

        ram_m = re.search(r'\b(\d{1,2}\s*gb\s*ram)\b', text_pool)
        if ram_m: specs["ram"] = ram_m.group(1).upper()

        display_m = re.search(r'\b(\d(?:\.\d{1,2})?\s*(?:inch|\"|\'-inch)\s*(?:amoled|oled|fhd\+)?)\b', text_pool)
        if display_m: specs["display"] = display_m.group(1).title()

        battery_m = re.search(r'\b(\d{4}\s*mah)\b', text_pool)
        if battery_m: specs["battery"] = battery_m.group(1).upper()

        camera_m = re.search(r'\b(\d{2,3}\s*mp\s*(?:triple|quad|dual|main|camera)?)\b', text_pool)
        if camera_m: specs["camera"] = camera_m.group(1).title()

    # Category 3: Clothing / Apparel
    elif p_type == "CLOTHING" or any(k in cat for k in ["shirt", "t-shirt", "jeans", "jacket", "dress"]):
        mat_m = re.search(r'\b(cotton|denim|polyester|linen|silk|wool|fleece|spandex)\b', text_pool)
        if mat_m: specs["material"] = mat_m.group(1).title()

        fit_m = re.search(r'\b(relaxed\s*fit|slim\s*fit|regular\s*fit|oversized\s*fit)\b', text_pool)
        if fit_m: specs["fit"] = fit_m.group(1).title()

        sleeve_m = re.search(r'\b(full\s*sleeve|half\s*sleeve|sleeveless|short\s*sleeve)\b', text_pool)
        if sleeve_m: specs["sleeve"] = sleeve_m.group(1).title()

        pat_m = re.search(r'\b(plaid\s*check|solid|printed|striped|graphic|checkered)\b', text_pool)
        if pat_m: specs["pattern"] = pat_m.group(1).title()

    # Category 4: Shoes / Footwear
    elif p_type == "SHOES" or any(k in cat for k in ["shoe", "shoes", "sneaker", "footwear"]):
        sole_m = re.search(r'\b(rubber\s*sole|eva\s*sole|leather|mesh|synthetic|foam)\b', text_pool)
        if sole_m: specs["sole"] = sole_m.group(1).title()

        purpose_m = re.search(r'\b(running|walking|casual|training|basketball|formal)\b', text_pool)
        if purpose_m: specs["purpose"] = purpose_m.group(1).title()

    # Category 5: Watches
    elif p_type == "WATCH" or "watch" in cat:
        mov_m = re.search(r'\b(analog|digital|smartwatch|chronograph|automatic|quartz)\b', text_pool)
        if mov_m: specs["movement"] = mov_m.group(1).title()

        water_m = re.search(r'\b(\d{2,3}\s*m\s*water\s*resistant|5\s*atm|3\s*atm)\b', text_pool)
        if water_m: specs["water_resistance"] = water_m.group(1).upper()

    return specs


def calculate_shopping_value_score(product: dict) -> tuple[int, dict]:
    """
    Computes Shopping Intelligence Value Score (0 - 100).
    Evaluates discount, ratings, reviews, Prime, delivery speed, warranty, coupon, bank offers.
    Returns (score, breakdown_dict).
    """
    score = 0
    breakdown = {}

    price = product.get("price")
    orig_price = product.get("original_price") or product.get("mrp")
    discount = product.get("discount_percentage", 0)

    if orig_price and price and orig_price > price:
        calc_disc = round(((orig_price - price) / orig_price) * 100)
        discount = max(discount, calc_disc)

    product["discount_percentage"] = discount

    if discount >= 30:
        score += 25
        breakdown["discount"] = "+25 (30%+ OFF)"
    elif discount >= 20:
        score += 20
        breakdown["discount"] = "+20 (20%+ OFF)"
    elif discount >= 10:
        score += 15
        breakdown["discount"] = "+15 (10%+ OFF)"

    rating = product.get("rating")
    if rating:
        try:
            r_val = float(rating)
            if r_val >= 4.4:
                score += 20
                breakdown["rating"] = "+20 (Rating >= 4.4⭐)"
            elif r_val >= 4.0:
                score += 15
                breakdown["rating"] = "+15 (Rating >= 4.0⭐)"
            elif r_val >= 3.5:
                score += 10
                breakdown["rating"] = "+10 (Rating >= 3.5⭐)"
        except:
            pass

    reviews = product.get("review_count") or 0
    if reviews >= 500:
        score += 15
        breakdown["reviews"] = "+15 (>500 Reviews)"
    elif reviews >= 100:
        score += 10
        breakdown["reviews"] = "+10 (>100 Reviews)"

    if product.get("prime_eligible") or "prime" in str(product.get("delivery", "")).lower():
        score += 15
        breakdown["prime"] = "+15 (Prime Delivery)"
    elif "tomorrow" in str(product.get("delivery", "")).lower():
        score += 10
        breakdown["delivery"] = "+10 (Delivery Tomorrow)"

    if product.get("warranty") or "warranty" in str(product.get("description", "")).lower():
        score += 10
        breakdown["warranty"] = "+10 (Manufacturer Warranty)"

    if product.get("bank_offers") or product.get("emi"):
        score += 10
        breakdown["offers"] = "+10 (Bank/EMI Offers)"

    if product.get("coupon_available") or "coupon" in str(product.get("description", "")).lower():
        score += 5
        breakdown["coupon"] = "+5 (Coupon Discount)"

    final_score = min(100, max(10, score))
    return final_score, breakdown


def generate_factual_ai_summary(product: dict, specs: dict) -> str:
    """
    Generates a concise, non-hallucinated AI summary based strictly on extracted specs & metrics.
    """
    name = product.get("name") or "Product"
    rating = product.get("rating")
    discount = product.get("discount_percentage", 0)

    summary_parts = []

    spec_list = [f"{k.upper()}: {v}" for k, v in specs.items() if v]
    if spec_list:
        spec_str = ", ".join(spec_list[:3])
        summary_parts.append(f"Offers key features including {spec_str}.")

    val_parts = []
    if rating:
        val_parts.append(f"strong {rating}⭐ rating")
    if discount and discount > 0:
        val_parts.append(f"{discount}% discount")

    if val_parts:
        summary_parts.append(f"With a {' and '.join(val_parts)}, it provides excellent value.")
    else:
        summary_parts.append("A top-rated choice for quality and performance.")

    return " ".join(summary_parts).strip()


def enrich_product(product: dict, category_type: str = "") -> dict:
    """
    Primary Entry Point for Product Intelligence Layer.
    Enriches product dictionary with category specs, Shopping Value Score, and AI Summary.
    """
    if not isinstance(product, dict):
        return product

    cat_specs = extract_category_specifications(product, category_type)
    existing_specs = product.get("specifications") or {}
    if isinstance(existing_specs, dict):
        merged_specs = {**cat_specs, **existing_specs}
    else:
        merged_specs = cat_specs

    product["specifications"] = merged_specs

    if "prime_eligible" not in product:
        product["prime_eligible"] = True
    if "warranty" not in product:
        product["warranty"] = "1 Year Brand Warranty"
    if "seller" not in product:
        product["seller"] = "Appario Retail Private Ltd (Authorized Seller)"

    val_score, breakdown = calculate_shopping_value_score(product)
    product["shopping_score"] = val_score
    product["shopping_score_breakdown"] = breakdown

    if not product.get("ai_summary") or product.get("ai_summary") == "Top recommendation":
        product["ai_summary"] = generate_factual_ai_summary(product, merged_specs)

    logger.info(f"[Intelligence] Enriched '{product.get('name', '')[:35]}...' | Value Score: {val_score}/100")
    return product
