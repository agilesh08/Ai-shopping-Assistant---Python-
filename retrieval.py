"""
retrieval.py — Multi-Stage Retrieval Engine for Trevor AI Shopping Assistant.
Executes progressive search candidate queries, merges candidate product pools, and deduplicates by ASIN/Title similarity.
"""

import asyncio
import html
import logging
import re
import ranker
import normalizer
import llm
import query_builder
import product_intelligence
import decision_engine

logger = logging.getLogger("trevor.retrieval")


def deduplicate_products(products: list[dict]) -> tuple[list[dict], int]:
    """
    Deduplicates raw parsed product dictionaries.
    Filters out items with identical ASIN/URL or normalized title similarity (>90%).
    Returns (unique_products, count_removed).
    """
    if not products:
        return [], 0

    unique_items = []
    seen_keys = set()
    count_removed = 0

    def get_norm_title(title_str: str) -> str:
        s = title_str.lower()
        s = re.sub(r'[^\w\d]', '', s)
        return s[:60]  # First 60 alphanumeric chars

    for p in products:
        url = p.get("url") or p.get("purchase_url") or ""
        name = p.get("name") or p.get("title") or ""

        # ASIN or URL key
        asin_match = re.search(r"/dp/([A-Z0-9]{10})", url)
        if asin_match:
            item_key = f"asin_{asin_match.group(1)}"
        elif url:
            item_key = f"url_{url.split('?')[0]}"
        else:
            item_key = f"title_{get_norm_title(name)}"

        norm_title = get_norm_title(name)

        if item_key in seen_keys or (norm_title and norm_title in seen_keys):
            count_removed += 1
        else:
            seen_keys.add(item_key)
            if norm_title:
                seen_keys.add(norm_title)
            unique_items.append(p)

    return unique_items, count_removed


async def execute_multi_stage_retrieval(
    state: dict,
    platform_config: dict,
    fetch_html_func,
    max_candidates_to_execute: int = 4,
    override_candidates: list[str] = None
) -> tuple[dict, bool]:
    """
    Multi-Stage Retrieval Pipeline:
    1. Generates category-specific or subcategory-expansion candidate queries.
    2. Executes candidate queries to retrieve candidate products from Amazon.
    3. Merges all retrieved products into one unified pool.
    4. Removes duplicate products by ASIN/URL and normalized title similarity.
    5. Returns (result_dict, exact_match_flag).
    """
    if override_candidates:
        candidates = [(c, False) for c in override_candidates]
    else:
        vision_meta = state.get("vision_metadata") or state
        candidates = query_builder.generate_category_queries(vision_meta)

    merged_raw_products = []
    executed_queries = []
    exact_match = False

    print(f"\n[Retrieval] Beginning Multi-Stage Search Execution for '{state.get('identified_product', 'Product')}'...")

    for idx, (cand_query, is_exact_attempt) in enumerate(candidates[:max_candidates_to_execute], 1):
        search_url = platform_config["build_url"](cand_query)
        logger.info(f"[Retrieval] Candidate {idx} [{cand_query}] -> Scraping...")

        html_content = await asyncio.to_thread(fetch_html_func, search_url, platform_config.get("render_js", False))
        if not html_content:
            print(f"[Retrieval] Candidate {idx} '{cand_query}' | Scrape Failed (0 products)")
            continue

        raw_parsed = platform_config["parse"](html_content)
        raw_count = len(raw_parsed)

        print(f"[Retrieval] Candidate {idx} '{cand_query}' | Products Found: {raw_count}")

        if raw_count > 0:
            merged_raw_products.extend(raw_parsed)
            executed_queries.append(cand_query)
            if is_exact_attempt and not exact_match:
                exact_match = True

    total_merged = len(merged_raw_products)
    print(f"[Retrieval] Total Raw Merged Products: {total_merged}")

    if not merged_raw_products:
        return {"status": "no_results", "products": [], "query": state.get("search_query", ""), "search_url": ""}, False

    # Stage 3: Deduplicate Merged Product Pool
    unique_products, removed_count = deduplicate_products(merged_raw_products)
    final_candidates_count = len(unique_products)

    print(f"[Retrieval] Duplicates Removed: {removed_count}")
    print(f"[Retrieval] Final Candidates: {final_candidates_count}")

    # Stage 4: Run Specification-Aware Weighted Ranking Engine once over the merged list
    ranked_products = ranker.rank_products(unique_products, state)

    if not ranked_products:
        ranked_products = unique_products[:5]

    cat = state.get("category", "Unknown")
    top_title_1 = ranked_products[0].get("name", "Product") if ranked_products else "None"
    print("\n===== AFTER RANKER =====")
    print(f"Category: {cat}")
    print(f"Top Product: {top_title_1}")
    print(f"Products Count: {len(ranked_products)}")
    print("========================\n")

    # Stage 5: Select TOP 5 for LLM summary & normalizer (With Subcategory Diversity for Broad Categories)
    if state.get("is_broad_category"):
        top_candidates = []
        seen_subcats = set()
        for p in ranked_products:
            p_name_lower = (p.get("name") or p.get("title") or "").lower()
            sub_key = p_name_lower.split()[0] if p_name_lower else "item"
            for kw in ["hose", "tools", "shears", "sprayer", "gloves", "trimmer", "rake", "pots", "keyboard", "mouse", "webcam", "ssd", "air fryer", "kettle", "microwave", "mixer", "blender", "trowel"]:
                if kw in p_name_lower:
                    sub_key = kw
                    break
            if sub_key not in seen_subcats or len(top_candidates) >= 4:
                seen_subcats.add(sub_key)
                top_candidates.append(p)
            if len(top_candidates) >= 5:
                break
        if len(top_candidates) < 5:
            top_candidates = ranked_products[:5]
    else:
        top_candidates = ranked_products[:5]

    described = await asyncio.to_thread(llm.filter_and_describe_products, top_candidates, state)
    if not described:
        described = top_candidates

    normalized_products = [normalizer.normalize_product(p, cat) for p in described]

    # Stage 6: Product Intelligence Layer (Enrichment)
    enriched_products = [product_intelligence.enrich_product(p, cat) for p in normalized_products]
    top_title_2 = enriched_products[0].get("name", "Product") if enriched_products else "None"
    print("===== AFTER PRODUCT INTELLIGENCE =====")
    print(f"Category: {cat}")
    print(f"Top Product: {top_title_2}")
    print(f"Products Count: {len(enriched_products)}")
    print("======================================\n")

    # Stage 7: AI Decision Engine (Buying Recommendations & Badges)
    final_decision_products = decision_engine.analyze_decisions(enriched_products, state)
    top_title_3 = final_decision_products[0].get("name", "Product") if final_decision_products else "None"
    print("===== AFTER DECISION ENGINE =====")
    print(f"Category: {cat}")
    print(f"Top Product: {top_title_3}")
    print(f"Products Count: {len(final_decision_products)}")
    print("=================================\n")

    res = {
        "status": "ok",
        "products": [dict(p) for p in final_decision_products],
        "query": executed_queries[0] if executed_queries else state.get("search_query", ""),
        "search_url": platform_config["build_url"](executed_queries[0]) if executed_queries else "",
        "platform": "amazon",
        "platform_label": platform_config.get("label", "Amazon"),
    }
    return res, exact_match
