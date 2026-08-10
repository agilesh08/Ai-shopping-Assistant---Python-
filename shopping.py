"""
shopping.py — Multi-platform shopping pipeline (Amazon, Flipkart).
"""

import asyncio
from scraper import fetch_html
from platforms import (
    build_amazon_url, build_flipkart_url,
    parse_amazon, parse_flipkart,
)
import llm
import retrieval

PLATFORM_CONFIG = {
    "amazon": {
        "label": "Amazon",
        "emoji": "🛒",
        "build_url": build_amazon_url,
        "parse": parse_amazon,
        "render_js": False,
    },
    "flipkart": {
        "label": "Flipkart",
        "emoji": "🔵",
        "build_url": build_flipkart_url,
        "parse": parse_flipkart,
        "render_js": False,
    },
}


def pre_filter_products(products: list[dict], state: dict) -> list[dict]:
    import re
    product_req = (state.get("product") or "").lower()
    filters_req = (state.get("filters") or "").lower()
    search_query = (state.get("search_query") or "").lower()
    budget_req = state.get("budget")
    full_req = f"{product_req} {filters_req} {search_query}"
    
    known_brands = [
        "poco", "iqoo", "oneplus", "samsung", "apple", "realme", "redmi", "xiaomi",
        "vivo", "oppo", "motorola", "moto", "nokia", "nothing", "infinix", "lava",
        "tecno", "honor", "acer", "hp", "dell", "lenovo", "asus", "msi", "sony",
        "lg", "whirlpool", "haier", "godrej", "bose", "jbl", "boat", "noise",
        "fire-boltt", "zebronics", "logitech", "razer", "hyperx", "nike", "puma", "adidas"
    ]
    
    req_brand = None
    state_b = state.get("brand")
    if state_b and str(state_b).strip().lower() not in {"null", "none", ""}:
        req_brand = str(state_b).strip().lower()
    else:
        for b in known_brands:
            if re.search(r'\b' + re.escape(b) + r'\b', full_req):
                req_brand = b
                break

    # Store resolved req_brand in state for result reporting
    state["_resolved_req_brand"] = req_brand.title() if req_brand else None
            
    numeric_budget = None
    if isinstance(budget_req, (int, float)):
        numeric_budget = float(budget_req)
    elif isinstance(budget_req, str):
        m = re.search(r"(\d+)", budget_req.replace(",", "").replace("k", "000"))
        if m:
            numeric_budget = float(m.group(1))

    # GPU strict matching (e.g. rtx 4050)
    gpu_match = re.search(r"(rtx\s*\d{4}|gtx\s*\d{4})", full_req)
    req_gpu = gpu_match.group(1).replace(" ", "") if gpu_match else None

    # RAM strict matching (e.g. 16gb)
    ram_match = re.search(r"(\d+\s*gb)\s*ram", full_req)
    req_ram = ram_match.group(1).replace(" ", "") if ram_match else None

    filtered = []
    aliases = {
        "apple": ["apple", "iphone", "ipad", "macbook", "airpods"],
        "poco": ["poco"],
        "iqoo": ["iqoo"],
        "oneplus": ["oneplus", "1+"],
        "motorola": ["motorola", "moto"],
        "xiaomi": ["xiaomi", "redmi", "mi"],
    }

    for p in products:
        name_lower = (p.get("name") or "").lower()
        feats_text = " ".join(p.get("features", [])).lower()
        text_content = f"{name_lower} {feats_text}"
        price = p.get("price")
        
        if req_brand:
            match_terms = aliases.get(req_brand, [req_brand])
            if not any(re.search(r'\b' + re.escape(term) + r'\b', name_lower) for term in match_terms):
                continue
            
        if numeric_budget and price and price > numeric_budget * 1.05:
            continue
            
        if req_gpu and req_gpu not in text_content.replace(" ", ""):
            continue

        if req_ram and req_ram not in text_content.replace(" ", ""):
            continue
            
        filtered.append(p)
        
    return filtered


import normalizer
import ranker
import query_builder
import broad_category


def generate_retry_queries(original_query: str, state: dict) -> list[str]:
    """Generates fallback search queries for Intelligent Search Retry System."""
    queries = []
    cat = state.get("category") or ""
    brand = state.get("brand") or ""
    budget = state.get("budget")

    # Variant 1: Brand + Category + Budget
    if brand and cat:
        v1 = f"{brand} {cat} under {budget}" if budget else f"{brand} {cat}"
        if v1.lower() != original_query.lower(): queries.append(v1)

    # Variant 2: Category + Budget
    if cat:
        v2 = f"{cat} under {budget}" if budget else str(cat)
        if v2.lower() != original_query.lower(): queries.append(v2)

    # Variant 3: Brand + Budget
    if brand:
        v3 = f"{brand} under {budget}" if budget else str(brand)
        if v3.lower() != original_query.lower(): queries.append(v3)

    return list(dict.fromkeys(queries))


async def search_products(clean_query: str, state: dict, platform: str = "amazon") -> dict:
    config = PLATFORM_CONFIG.get(platform, PLATFORM_CONFIG["amazon"])

    async def _try_single_search(query_str: str) -> tuple[dict, int]:
        """Executes a single search attempt and returns (result_dict, raw_parsed_count)."""
        search_url = config["build_url"](query_str)

        html = await asyncio.to_thread(fetch_html, search_url, config["render_js"])
        if not html:
            return {"status": "scrape_failed", "products": [], "query": query_str, "search_url": search_url}, 0

        raw_products = config["parse"](html)
        raw_count = len(raw_products)

        if not raw_products:
            return {"status": "no_results", "products": [], "query": query_str, "search_url": search_url}, 0

        # Step 1: Weighted Semantic Ranking Engine (No rigid keyword filtering!)
        ranked_products = ranker.rank_products(raw_products, state)

        if not ranked_products:
            ranked_products = raw_products[:5]

        # Step 2: Limit candidate products to TOP 5 for LLM summary & spec extraction
        top_candidates = ranked_products[:5]
        described = await asyncio.to_thread(llm.filter_and_describe_products, top_candidates, state)

        if not described:
            described = top_candidates

        # Step 3: Normalize products using Standard Product Schema & Category Intelligence
        cat = state.get("category", "")
        normalized_products = [normalizer.normalize_product(p, cat) for p in described]

        return {
            "status": "ok",
            "products": normalized_products,
            "query": query_str,
            "search_url": search_url,
            "platform": platform,
            "platform_label": config["label"],
        }, raw_count

    try:
        # Check if searching for an Image Upload (Multi-Stage Retrieval Engine)
        if state.get("is_image_search"):
            res, is_exact = await retrieval.execute_multi_stage_retrieval(
                state=state,
                platform_config=config,
                fetch_html_func=fetch_html,
                max_candidates_to_execute=3
            )
            state["exact_match"] = is_exact
            return res

        # Check if Broad Category Query (e.g. "Gardening Equipment", "Computer Accessories")
        is_broad, broad_key = broad_category.is_broad_category_query(clean_query, state.get("category", ""))
        if is_broad and broad_key:
            state["is_broad_category"] = True
            state["broad_category_key"] = broad_key
            expanded_queries = broad_category.expand_broad_category(broad_key, state.get("budget"))
            print(f"[Shopping] Broad Category Detected ('{broad_key}'). Expanding into subcategory queries: {expanded_queries}")
            res, is_exact = await retrieval.execute_multi_stage_retrieval(
                state=state,
                platform_config=config,
                fetch_html_func=fetch_html,
                max_candidates_to_execute=4,
                override_candidates=expanded_queries
            )
            return res

        # Standard Text Search Attempt
        res, raw_count = await _try_single_search(clean_query)
        if raw_count > 0:
            return res

        # Fallback Retry Queries for Text Search
        retry_queries = generate_retry_queries(clean_query, state)
        for rq in retry_queries:
            print(f"[Shopping Retry System] Retrying with fallback query: '{rq}'")
            retry_res, r_count = await _try_single_search(rq)
            if r_count > 0:
                return retry_res

        return res

    except Exception as e:
        print(f"[Shopping] Search exception: {e}")
        return {"status": "scrape_failed", "products": [], "query": clean_query, "search_url": ""}
