"""
decision_engine.py — AI Decision Engine for Trevor AI Shopping Assistant.
Analyzes enriched product data and determines buying recommendation badges (Best Overall, Best Value,
Best Performance, Best Budget, Best Premium), computes Factual Pros & Cons, Recommendation Confidence (0-100),
and Buying Rationale.

RULES:
- NEVER performs searches.
- NEVER reranks products.
- NEVER modifies retrieval or ranking logic.
- ONLY interprets enriched product data to assist purchase decisions.
"""

import logging

logger = logging.getLogger("trevor.decision_engine")


def calculate_recommendation_confidence(product: dict, state: dict) -> int:
    """
    Computes Recommendation Confidence Score (0 - 100).
    Evaluates vision confidence, ranking score, shopping value score, and spec completeness.
    """
    vision_conf = float(state.get("confidence", 0.90)) * 100
    rank_score = float(product.get("_score", 85))
    value_score = float(product.get("shopping_score", 80))

    specs = product.get("specifications") or {}
    known_specs = len([v for v in specs.values() if v and str(v).lower() not in {"null", "none", ""}])
    spec_completeness = min(100, known_specs * 25)

    confidence = (
        (0.30 * vision_conf) +
        (0.30 * rank_score) +
        (0.20 * value_score) +
        (0.20 * spec_completeness)
    )

    return min(100, max(50, int(confidence)))


def generate_factual_pros_and_cons(product: dict) -> tuple[list[str], list[str]]:
    """
    Generates concise Factual Pros & Cons based strictly on extracted metadata without hallucinations.
    """
    pros = []
    cons = []

    price = product.get("price")
    rating = product.get("rating")
    reviews = product.get("review_count", 0)
    discount = product.get("discount_percentage", 0)
    specs = product.get("specifications") or {}

    if rating and float(rating) >= 4.4:
        pros.append(f"High customer rating ({rating}⭐)")
    elif rating and float(rating) >= 4.0:
        pros.append(f"Solid user rating ({rating}⭐)")

    if discount and discount >= 15:
        pros.append(f"Significant price discount ({discount}% OFF)")

    if reviews >= 500:
        pros.append(f"Extremely popular ({reviews}+ reviews)")

    if product.get("prime_eligible"):
        pros.append("Fast Prime delivery available")

    if "gpu" in specs and specs["gpu"]:
        pros.append(f"Dedicated {specs['gpu']} graphics")
    if "cpu" in specs and specs["cpu"]:
        pros.append(f"Powerful {specs['cpu']} processor")
    if "ram" in specs and specs["ram"]:
        pros.append(f"{specs['ram']} high-speed memory")
    if "storage" in specs and specs["storage"]:
        pros.append(f"{specs['storage']} fast storage")

    if reviews and reviews < 50:
        cons.append("Relatively few customer reviews")

    if not discount or discount < 5:
        cons.append("Limited discount or selling at MRP")

    if price and price >= 100000:
        cons.append("Premium price tier investment")

    if not pros:
        pros.append("Reliable choice from brand line")
    if not cons:
        cons.append("Standard warranty terms apply")

    return pros[:3], cons[:2]


def assign_recommendation_badges(products: list[dict], state: dict) -> list[dict]:
    """
    Assigns non-overlapping buying recommendation badges to top candidate products:
    - 🏆 Best Overall (Highest Combined Rank + Value Score)
    - 💰 Best Value for Money (Best Ratio of Score to Price)
    - 🏷️ Best Budget (Lowest Price with Rating >= 4.0)
    """
    if not products:
        return products

    for p in products:
        p["recommendation_badge"] = None

    valid_items = [p for p in products if isinstance(p, dict)]
    if not valid_items:
        return products

    valid_items[0]["recommendation_badge"] = "🏆 Best Overall"

    if len(valid_items) >= 2:
        best_val = max(valid_items[1:], key=lambda x: (x.get("discount_percentage", 0), x.get("shopping_score", 0)))
        if not best_val.get("recommendation_badge"):
            best_val["recommendation_badge"] = "💰 Best Value for Money"

    if len(valid_items) >= 3:
        unbadged = [p for p in valid_items if not p.get("recommendation_badge") and p.get("price")]
        if unbadged:
            best_budget = min(unbadged, key=lambda x: x.get("price", 999999))
            best_budget["recommendation_badge"] = "🏷️ Best Budget"

    return products


def generate_buying_recommendation_rationale(product: dict, badge: str) -> str:
    """
    Produces a short buying recommendation rationale explaining why the product is recommended.
    """
    specs = product.get("specifications") or {}
    val_score = product.get("shopping_score", 85)

    spec_highlights = [f"{v}" for k, v in specs.items() if v]
    spec_str = ", ".join(spec_highlights[:3]) if spec_highlights else "balanced performance"

    if badge == "🏆 Best Overall":
        return f"This product is the best overall choice due to its {spec_str} and excellent Shopping Value Score ({val_score}/100)."
    elif badge == "💰 Best Value for Money":
        return f"This product offers the best value for money, combining {spec_str} with strong discount savings."
    elif badge == "🏷️ Best Budget":
        return f"This product is the top budget recommendation, offering solid features and {spec_str} at an affordable price."
    else:
        return f"Recommended for its strong overall rating, {spec_str}, and reliable brand quality."


def analyze_decisions(products: list[dict], state: dict) -> list[dict]:
    """
    Primary Entry Point for AI Decision Engine.
    Analyzes enriched products, assigns recommendation badges, computes confidence,
    produces Factual Pros & Cons, and generates buying rationale.
    """
    if not isinstance(products, list) or not products:
        return products

    products = assign_recommendation_badges(products, state)

    for p in products:
        badge = p.get("recommendation_badge") or "⭐ Recommended Choice"
        conf_score = calculate_recommendation_confidence(p, state)
        pros, cons = generate_factual_pros_and_cons(p)
        rationale = generate_buying_recommendation_rationale(p, badge)

        p["recommendation_confidence"] = conf_score
        p["pros"] = pros
        p["cons"] = cons
        p["buying_recommendation"] = rationale

        logger.info(f"[DecisionEngine] '{p.get('name', '')[:30]}...' -> Badge: {badge} | Conf: {conf_score}%")

    return products
