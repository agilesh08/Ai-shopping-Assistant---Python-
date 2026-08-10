"""
formatter.py — Format bot responses for Telegram (plain text, emoji-friendly).
"""

import html
import logging
import random
import re
import time

logger = logging.getLogger("trevor.formatter")

PLATFORM_ICONS = {
    "amazon": "🛒",
    "flipkart": "🔵",
}

PLATFORM_LABELS = {
    "amazon": "Amazon",
    "flipkart": "Flipkart",
}

IMAGE_ACK_MESSAGES = [
    "📸 Image received successfully!\n👀 I'm analyzing the product in your image...\n✨ Once I identify it, I'll automatically find the best matching products for you. Please wait a few seconds 😊",
    "📷 Nice! Let me inspect that image for you...\n✨ Identifying the product and searching Amazon...",
    "🔍 Looking closely at your image...\n👀 I'm extracting the product details right now!",
    "👀 I think I can identify this product!\n✨ Finding similar products on Amazon for you...",
    "🛍️ Image received! Searching the marketplace for matching items..."
]

def get_random_image_ack_message() -> str:
    """Returns a random friendly acknowledgment message when an image is received."""
    return random.choice(IMAGE_ACK_MESSAGES)


def get_image_intro(product_name: str = "", category: str = "", is_exact_match: bool = True) -> str:
    """Generates a warm, human-like introduction for image recognition results."""
    clean_pname = ""
    if product_name:
        clean_pname = re.sub(r'\b(None|Unknown|null)\b', '', product_name, flags=re.I).strip()
        clean_pname = re.sub(r'\s+', ' ', clean_pname)

    if is_exact_match:
        if clean_pname:
            clean_name = html.escape(clean_pname)
            return f"📸 I found a <b>{clean_name}</b> in your image.\n\n✨ I searched Amazon for the closest matching products and found these top results:"
        return "📸 I analyzed your image and found these top matching products on Amazon:"
    else:
        if clean_pname:
            clean_name = html.escape(clean_pname)
            return f"⚠️ I couldn't find the exact <b>{clean_name}</b> model from your image on Amazon.\n\nHowever, I found these closely related products that match your search:"
        return "⚠️ I couldn't find the exact product shown in your image on Amazon. However, I found these closely related products from the same category:"


def format_price(price: int | None) -> str:
    if price is None:
        return "Price not listed"
    return f"₹{price:,}"

def format_rating(rating: float | None, reviews: int) -> str:
    if rating is None:
        return "No rating yet"
    if reviews > 0:
        return f"{rating}⭐ ({reviews:,} reviews)"
    return f"{rating}⭐"

def get_friendly_intro(user_query: str = "", category: str = "", state: dict = None) -> str:
    """
    Generates a warm, friendly, natural contextual introduction.
    Explicit category parameter takes absolute priority over user_query string.
    """
    cat_lower = (category or (state.get("category") if state else "") or "").lower().strip()
    q_lower = (user_query or "").lower().strip()

    if state and state.get("is_broad_category"):
        broad_key = (state.get("broad_category_key") or "").replace("_", " ").title()
        if "Garden" in broad_key or "gardening" in q_lower:
            return "🌱 I found some highly rated gardening equipment across different categories.\n\nHere are the best options:"
        elif "Computer" in broad_key or "computer" in q_lower:
            return "💻 I found top-rated computer accessories across different categories.\n\nHere are the best options:"
        elif "Kitchen" in broad_key or "kitchen" in q_lower:
            return "🍳 I found top-rated kitchen appliances across different categories.\n\nHere are the best options:"
        elif broad_key:
            return f"✨ I found top-rated {broad_key} across different categories.\n\nHere are the best options:"

    # Priority 1: Check explicit category parameter
    if cat_lower:
        if any(k in cat_lower for k in ["water heater", "geyser"]):
            return "♨️ Here are the top water heaters and geysers that match your requirements!"
        elif any(k in cat_lower for k in ["headphone", "earbud", "audio", "tws", "earphone"]):
            return "🎧 Here are some headphones that should give you a great listening experience!"
        elif any(k in cat_lower for k in ["phone", "mobile", "smartphone"]):
            return "📱 Here are the top smartphones I found for you that match your requirements!"
        elif any(k in cat_lower for k in ["laptop", "notebook", "macbook"]):
            return "💻 Here are the top laptops I found for your needs and budget!"
        elif any(k in cat_lower for k in ["tv", "television", "monitor"]):
            return "📺 Here are the top TVs I found for your home viewing experience!"
        elif any(k in cat_lower for k in ["ac", "fridge", "refrigerator"]):
            return "❄️ Here are the best cooling appliances that match your requirements!"
        elif any(k in cat_lower for k in ["shoe", "sneaker", "clothing", "shirt", "dress"]):
            return "✨ I found these stylish picks that match your requirements!"

    # Priority 2: Fallback to user_query string inspection
    full_text = f"{cat_lower} {q_lower}"
    def matches_any(keywords):
        return any(re.search(r'\b' + re.escape(k) + r'\b', full_text) for k in keywords)

    if matches_any(["water heater", "water heaters", "geyser", "geysers", "immersion rod"]):
        return "♨️ Here are the top water heaters and geysers that match your requirements!"
    elif matches_any(["headphone", "headphones", "earbud", "earbuds", "audio", "tws", "earphone", "earphones"]):
        return "🎧 Here are some headphones that should give you a great listening experience!"
    elif matches_any(["phone", "phones", "mobile", "mobiles", "smartphone", "smartphones"]):
        return "📱 Here are the top smartphones I found for you that match your requirements!"
    elif matches_any(["laptop", "laptops", "macbook", "notebook"]):
        return "💻 Here are the top laptops I found for your needs and budget!"
    elif matches_any(["tv", "television", "monitor"]):
        return "📺 Here are the top TVs I found for your home viewing experience!"
    elif matches_any(["ac", "fridge", "refrigerator"]):
        return "❄️ Here are the best cooling appliances that match your requirements!"
    elif matches_any(["shoe", "shoes", "sneaker", "clothing", "fashion", "dress", "shirt"]):
        return "✨ I found these stylish picks that match your requirements!"

    return random.choice([
        "🎉 Here are the best options I found for you!",
        "🔥 These products offer the best value right now.",
        "⭐ Based on your needs, these are my top recommendations.",
        "💯 I found these highly-rated products for you!"
    ])


def format_products(
    products: list[dict],
    user_query: str,
    platform: str = "amazon",
    is_image_search: bool = False,
    identified_product: str = "",
    is_exact_match: bool = True,
    category: str = "",
    state: dict = None
) -> str:
    """
    Format product list into a clean Telegram message matching the exact new card design.
    Uses deep copy of products to prevent stale reference mutations.
    """
    if not products:
        return format_no_results(user_query, platform)

    clean_products = [dict(p) for p in products if isinstance(p, dict)]
    if not clean_products:
        return format_no_results(user_query, platform)

    cat = category or (state.get("category") if state else "") or ""
    icon = PLATFORM_ICONS.get(platform, "🛍")
    label = PLATFORM_LABELS.get(platform, platform.title())
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    if is_image_search:
        intro = get_image_intro(identified_product, category=cat, is_exact_match=is_exact_match)
    else:
        intro = get_friendly_intro(user_query, category=cat, state=state)

    lines = [f"{intro}\n"]

    for i, p in enumerate(products):
        num = number_emojis[i] if i < 5 else f"{i+1}."
        name = html.escape(p.get("name", "Unknown Product"))
        price_val = p.get("price")
        price = format_price(price_val)
        disc_pct = p.get("discount_percentage")
        price_line = f"{price}"
        if disc_pct and disc_pct > 0:
            price_line += f" <b>({disc_pct}% OFF)</b>"

        val_score = p.get("shopping_score")
        score_line = f" 🔥 <b>Shopping Value Score: {val_score}/100</b>" if val_score else ""
        rating = format_rating(p.get("rating"), p.get("review_count", 0))
        url = p.get("url", "")

        badge = p.get("recommendation_badge")
        badge_header = f"<b>{html.escape(badge)}</b>\n" if badge else ""

        conf = p.get("recommendation_confidence")
        conf_str = f" • 🎯 <b>Confidence: {conf}%</b>" if conf else ""

        block = [
            "━━━━━━━━━━━━━━━━━━",
            "",
            f"{badge_header}{num} <b>{name}</b>{score_line}",
            "",
            "💰 Price",
            f"{price_line}",
            "",
            "⭐ Rating",
            f"{rating}{conf_str}",
            ""
        ]

        # Pros & Cons
        pros = p.get("pros", [])
        cons = p.get("cons", [])
        if pros or cons:
            block.append("📊 AI Decision Analysis")
            for pro in pros[:3]:
                block.append(f"  ✅ <b>Pro</b>: {html.escape(pro)}")
            for con in cons[:2]:
                block.append(f"  ⚠️ <b>Con</b>: {html.escape(con)}")
            block.append("")

        # Delivery & Prime
        deliv = p.get("delivery_date") or p.get("delivery")
        prime_str = " (Prime)" if p.get("prime_eligible") else ""
        if deliv:
            block.append(f"🚚 <b>Delivery</b>: {html.escape(str(deliv))}{prime_str}")
            block.append("")
        
        specs = p.get("specifications")
        if isinstance(specs, dict) and len(specs) > 0:
            block.append("⚙ Specifications")
            for k, v in specs.items():
                if v and str(v).strip():
                    block.append(f"• <b>{html.escape(str(k)).upper()}</b>: {html.escape(str(v))}")
            block.append("")
        elif isinstance(specs, list) and len(specs) > 0:
            placeholders = {"processor name", "ram detail", "storage detail", "graphics card", "display info", "processor", "ram", "storage", "graphics", "display"}
            valid_specs = [s for s in specs if isinstance(s, str) and s.strip().lower() not in placeholders and len(s.strip()) > 2]
            if valid_specs:
                block.append("⚙ Specifications")
                for s in valid_specs:
                    block.append(f"• {html.escape(s)}")
                block.append("")

        # Render Categorized Offer Sections
        offer_categories = [
            ("emi_offers", "💳 EMI Options"),
            ("credit_offers", "🏦 Credit Card Offers"),
            ("debit_offers", "💳 Debit Card Offers"),
            ("cashback_offers", "💰 Cashback Offers"),
            ("exchange_offers", "🔄 Exchange Offers"),
            ("coupon_offers", "🎁 Coupon Offers"),
            ("partner_offers", "⭐ Partner Offers"),
        ]

        has_cat = False
        for key, header in offer_categories:
            cat_offers = p.get(key, [])
            if cat_offers and isinstance(cat_offers, list):
                valid_cat = [o for o in cat_offers if isinstance(o, str) and len(o.strip()) > 3]
                if valid_cat:
                    has_cat = True
                    block.append(header)
                    for o in valid_cat[:4]:
                        block.append(f"• {html.escape(o)}")
                    block.append("")

        # Fallback if no categorized offers exist
        if not has_cat and price_val and price_val >= 8000:
            emi = p.get("emi")
            offers = p.get("offers", [])
            if emi and isinstance(emi, str) and len(emi.strip()) > 3:
                block.append("💳 EMI Options")
                block.append(f"• {html.escape(emi)}")
                block.append("")
            if offers and isinstance(offers, list):
                valid_offers = [o for o in offers if isinstance(o, str) and len(o.strip()) > 3]
                if valid_offers:
                    block.append("🏦 Bank & Card Offers")
                    for o in valid_offers[:4]:
                        block.append(f"• {html.escape(o)}")
                    block.append("")

        # Render AI Summary
        summary = html.escape(p.get("ai_summary") or p.get("description") or p.get("ai_advisor") or "")
        if summary:
            # Clean off ⭐ My Recommendation header if present for AI Summary title consistency
            clean_summary = re.sub(r"^(⭐ My Recommendation|💡 AI Recommendation|🤖 AI Advisor)\s*", "", summary).strip()
            block.append("📝 AI Summary")
            block.append(f"{clean_summary}")
            block.append("")

        if url:
            block.append("🔗 Buy Now")
            block.append(f'<a href="{url}">{label} URL</a>')
            block.append("")

        lines.append("\n".join(block))

    lines.append("━━━━━━━━━━━━━━━━━━\n")
    lines.append(
        "💬 If you'd like, I can also compare these products side-by-side or recommend the best value-for-money option."
    )

    return "\n".join(lines)


def format_platform_prompt(query: str) -> str:
    """Message shown before platform selection buttons."""
    return (
        "🔍 Got it! Where would you like to search?\n\n"
        "Pick a platform 👇"
    )


def format_no_results(query: str, platform: str = "amazon") -> str:
    return (
        "😔 I couldn't find matching products on Amazon right now.\n\n"
        "Would you like to adjust your budget or change some requirements?\n"
        "Just tell me what you want and I'll search again!"
    )


def format_no_brand_results(brand: str, query: str, platform: str = "amazon") -> str:
    clean_brand = html.escape(brand)
    return (
        f"😔 I couldn't find a {clean_brand} product matching your requested budget.\n\n"
        "Would you like to adjust your budget or search for a different brand?"
    )


def format_scrape_error(platform: str = "amazon") -> str:
    label = PLATFORM_LABELS.get(platform, platform.title())
    return (
        f"😔 Product data couldn't be retrieved from {label} right now. "
        "Please try again in a moment!"
    )


def format_llm_error() -> str:
    return (
        "⚠️ My AI brain is taking a short break. "
        "Make sure Ollama is running and try again!"
    )


SIGNATURE = "Ai automation created My Agilesh T"


def format_welcome() -> str:
    return (
        "👋 Hey! I'm *Trevor*, your personal shopping & styling assistant!\n\n"
        "I can help you:\n"
        "🛒 Find products on *Amazon* or *Flipkart*\n"
        "👗 Get outfit and styling advice\n\n"
        "Just chat naturally — no special commands needed! 😊\n\n"
        "Try saying:\n"
        "• Puma shoes under 5000\n"
        "• Red XL shirt for men\n"
        "• What to wear for a casual date?\n\n"
        f"{SIGNATURE}"
    )


def format_help() -> str:
    return (
        "🤔 Here's what I can do:\n\n"
        "🛒 Shopping — just describe what you want:\n"
        "   'Nike running shoes under ₹4000'\n"
        "   'Red XL shirt'\n"
        "   'Best gaming mouse under 1500'\n\n"
        "👗 Styling — ask for outfit advice:\n"
        "   'What to wear to a wedding?'\n"
        "   'How to style white sneakers?'\n\n"
        "Then pick Amazon or Flipkart to search!\n\n"
        "💬 Just talk to me naturally — I'll figure out what you need!\n\n"
        f"{SIGNATURE}"
    )


def format_shopping_response(result: dict, state: dict = None) -> str:
    """
    Unified Primary Shopping Response Formatter for Trevor AI Shopping Assistant.
    Accepts search result dictionary and shopping state dictionary.
    Handles status: 'ok', 'no_results', 'no_brand_results', 'scrape_failed', etc.
    Includes robust fallback formatting if primary format encounters an exception.
    """
    t0 = time.time()
    if not isinstance(result, dict):
        return "😔 Unable to format shopping result."

    status = result.get("status", "ok")
    products = result.get("products", [])
    query = result.get("query", "")
    platform = result.get("platform", "amazon")

    state = state or {}
    is_image = state.get("is_image_search", False)
    identified = state.get("identified_product", "")
    is_exact = state.get("exact_match", True)

    if status == "no_results" or not products:
        return format_no_results(query, platform)

    if status == "no_brand_results":
        req_brand = result.get("requested_brand") or state.get("brand") or "requested brand"
        return format_no_brand_results(req_brand, query, platform)

    if status == "scrape_failed":
        return format_scrape_error(platform)

    try:
        formatted = format_products(
            products=products,
            user_query=query,
            platform=platform,
            is_image_search=is_image,
            identified_product=identified,
            is_exact_match=is_exact
        )
        elapsed = time.time() - t0
        logger.info(f"[Formatter] Formatting completed in {elapsed:.2f} sec")
        return formatted
    except Exception as e:
        logger.error(f"[Formatter] Error inside format_products: {e}", exc_info=True)
        # Fallback Formatter: Ensure search results are NEVER lost if primary formatter fails!
        logger.info("[Formatter] Fallback formatter used")
        fallback_lines = []
        if is_image and identified:
            fallback_lines.append(f"👀 I found a match!\n\n📱 <b>Product Identified</b>: {html.escape(identified)}\n")
            fallback_lines.append("Here are the closest matches I found on Amazon:\n")
        else:
            fallback_lines.append("🛍️ Here are the top matching products I found for you:\n")

        for i, p in enumerate(products[:5], 1):
            name = html.escape(p.get("name") or p.get("title") or "Product")
            price = format_price(p.get("price"))
            rating = format_rating(p.get("rating"), p.get("review_count", 0))
            url = p.get("url") or p.get("purchase_url") or ""

            fallback_lines.append("━━━━━━━━━━━━━━━━━━")
            fallback_lines.append(f"{i}️⃣ <b>{name}</b>")
            fallback_lines.append(f"💰 {price}")
            fallback_lines.append(f"⭐ {rating}")
            if url:
                fallback_lines.append(f'<a href="{url}">View Product</a>')
            fallback_lines.append("")

        fallback_lines.append("━━━━━━━━━━━━━━━━━━")
        return "\n".join(fallback_lines)
