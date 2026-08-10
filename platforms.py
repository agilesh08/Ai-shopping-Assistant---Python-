"""
platforms.py — URL builders and HTML parsers for Amazon, Flipkart, and Myntra.
"""

import re
from bs4 import BeautifulSoup


# ── URL Builders ───────────────────────────────────────────────────────────────

def build_amazon_url(query: str) -> str:
    encoded = query.strip().replace(" ", "+")
    return f"https://www.amazon.in/s?k={encoded}"


def build_flipkart_url(query: str) -> str:
    encoded = query.strip().replace(" ", "+")
    return f"https://www.flipkart.com/search?q={encoded}"


# ── Amazon Parser ──────────────────────────────────────────────────────────────

def parse_amazon(html: str) -> list[dict]:
    """Parse Amazon India search results HTML → list of product dicts."""
    soup = BeautifulSoup(html, "lxml")
    products = []

    items = soup.select("div[data-component-type='s-search-result']")

    for item in items:
        try:
            # Check for Sponsored / Ad badges or /sspa/click URLs
            link_el = item.select_one("h2 a") or item.select_one("a.a-link-normal")
            raw_href = link_el.get("href", "") if link_el else ""
            is_sponsored = "/sspa/click" in raw_href

            if not is_sponsored:
                for sp_sel in [".puis-sponsored-label-text", ".s-sponsored-label-text", ".s-sponsored-label-info-icon", "span.a-color-secondary"]:
                    sp_el = item.select_one(sp_sel)
                    if sp_el and "sponsored" in sp_el.get_text(strip=True).lower():
                        is_sponsored = True
                        break

            if is_sponsored:
                continue

            # Name — find complete title element
            name = None
            for sel in ["h2 a span", "a.a-link-normal span.a-text-normal", "h2 a", "h2"]:
                el = item.select_one(sel)
                if el:
                    t = el.get_text(strip=True)
                    if len(t) > len(name or ""):
                        name = t
            if not name or len(name) < 5:
                continue

            # Price
            price_whole = item.select_one(".a-price-whole")
            price = None
            if price_whole:
                try:
                    price = int(price_whole.get_text(strip=True).replace(",", "").replace(".", ""))
                except ValueError:
                    pass

            # Rating
            rating = None
            for sel in ["span[aria-label*='out of 5']", ".a-icon-alt"]:
                el = item.select_one(sel)
                if el:
                    text = el.get("aria-label") or el.get_text(strip=True)
                    m = re.search(r"(\d+\.?\d*)\s*out of", text)
                    if m:
                        rating = float(m.group(1))
                        break

            # Review count
            review_count = 0
            for sel in ["span[aria-label*='reviews']", "span.a-size-base.s-underline-text"]:
                el = item.select_one(sel)
                if el:
                    text = (el.get("aria-label") or el.get_text(strip=True)).replace(",", "")
                    m = re.search(r"(\d+)", text)
                    if m:
                        review_count = int(m.group(1))
                        break

            # URL — preserve full path, just strip ref= tracking
            url = None
            link_el = item.select_one("h2 a") or item.select_one("a.a-link-normal")
            if link_el:
                href = link_el.get("href", "")
                if href.startswith("/"):
                    url = f"https://www.amazon.in{href}"
                elif href.startswith("http"):
                    url = href
                if url:
                    # Amazon Sponsored products use /sspa/click? - we must keep query params for these
                    if "/sspa/click" not in url:
                        # Strip ref= tracking params, keep clean URL for normal products
                        url = re.sub(r"/ref=.*", "", url)
                        url = url.split("?")[0]

            # Discount
            discount = None
            for sel in [".a-size-base.a-color-price", ".s-coupon-unclipped"]:
                el = item.select_one(sel)
                if el:
                    m = re.search(r"(\d+)%", el.get_text(strip=True))
                    if m:
                        discount = int(m.group(1))
                        break

            # Features, Offers & EMI
            features = []
            for el in item.select(".a-list-item"):
                feat = el.get_text(strip=True)
                if 5 < len(feat) < 100 and feat not in features:
                    features.append(feat)
                    
            offers = []
            for sel in [".s-coupon-unclipped", ".a-size-base.a-color-secondary", "span.a-truncate-full"]:
                for el in item.select(sel):
                    t = el.get_text(strip=True)
                    if any(w in t.lower() for w in ["off", "discount", "cashback", "emi", "bank", "card", "exchange"]):
                        if 5 < len(t) < 100 and t not in offers:
                            offers.append(t)

            emi = None
            for f in features + offers:
                if "emi" in f.lower():
                    emi = f
                    break

            if name and url:
                products.append({
                    "name": name,
                    "price": price,
                    "rating": rating,
                    "review_count": review_count,
                    "url": url,
                    "discount": discount,
                    "features": features[:10],
                    "offers": offers[:5],
                    "emi": emi,
                    "platform": "amazon",
                })

        except Exception as e:
            print(f"[Amazon Parser] Error: {e}")
            continue

    return products


# ── Flipkart Parser ────────────────────────────────────────────────────────────

def parse_flipkart(html: str) -> list[dict]:
    """Parse Flipkart search results HTML → list of product dicts using multi-strategy fallback."""
    soup = BeautifulSoup(html, "lxml")
    products = []

    def process_item(item) -> dict | None:
        try:
            name = None
            for sel in ["div.KzDlHZ", "div._4rR01T", "a.CGtCSt", "a.w2-fe9", "a.IRpwTa", "a.s1Q9rs", "div.col-7-12 a", "div._3wU53n", "div._2WkVRV"]:
                el = item.select_one(sel)
                if el:
                    name = el.get_text(strip=True)
                    break

            link_el = item if (item.name == "a" and item.get("href") and "/p/" in item["href"]) else item.find("a", href=lambda h: h and "/p/" in h)
            if not name or len(name) < 5:
                if link_el:
                    name = link_el.get("title", "").strip() or link_el.get_text(strip=True)

            if name:
                for junk in ["Add to Compare", "Exchange Offer", "Bank Offer", "Special price", "Free delivery"]:
                    if junk in name:
                        name = name.split(junk)[0].strip()
                name = re.sub(r"^(Add to Compare|Offer|Special price)\s*", "", name, flags=re.IGNORECASE).strip()

            if not name or len(name) < 3:
                return None

            price = None
            for sel in ["div.Nx9bqj", "div._30jeq3", "div._25b18h ._30jeq3", "div._1_WHN1"]:
                el = item.select_one(sel)
                if el:
                    text = el.get_text(strip=True).replace("₹", "").replace(",", "")
                    m = re.search(r"^(\d+)", text)
                    if m:
                        price = int(m.group(1))
                        break
            
            if price is None:
                full_text = " ".join(item.stripped_strings)
                m = re.search(r"₹\s*([\d,]+)", full_text)
                if m:
                    price = int(m.group(1).replace(",", ""))

            rating = None
            for sel in ["div.XQDdHH", "div._3LWZlK", "span._1lRcqv"]:
                el = item.select_one(sel)
                if el:
                    try:
                        rating = float(el.get_text(strip=True))
                        break
                    except ValueError:
                        pass
            
            if rating is None:
                full_text = " ".join(item.stripped_strings)
                m = re.search(r"(\d\.\d)\s*★", full_text)
                if not m:
                    m = re.search(r"(\d\.\d)\s*out of", full_text, re.IGNORECASE)
                if m:
                    rating = float(m.group(1))

            review_count = 0
            for sel in ["span.Wphh3N", "span._2_R_DZ", "span._13vcmD", "span.col-12-12"]:
                el = item.select_one(sel)
                if el:
                    text = el.get_text(strip=True).replace(",", "")
                    m = re.search(r"(\d+)", text)
                    if m:
                        review_count = int(m.group(1))
                        break
                        
            if review_count == 0:
                full_text = " ".join(item.stripped_strings)
                m = re.search(r"([\d,]+)\s*(?:Ratings|Reviews)", full_text, re.IGNORECASE)
                if m:
                    review_count = int(m.group(1).replace(",", ""))

            url = None
            if link_el:
                href = link_el.get("href", "")
                if href and "/p/" in href:
                    url = f"https://www.flipkart.com{href}" if href.startswith("/") else href

            discount = None
            for sel in ["div._3Ay6Sb", "span.col-3-12._2Svcs_"]:
                el = item.select_one(sel)
                if el:
                    m = re.search(r"(\d+)%", el.get_text(strip=True))
                    if m:
                        discount = int(m.group(1))
                        break

            features = []
            for sel in ["ul.GZ7ufM li", "ul._1xgwMu li", "li.rgWa7D", "div._21A20"]:
                for el in item.select(sel):
                    feat = el.get_text(strip=True)
                    if 5 < len(feat) < 100 and feat not in features:
                        features.append(feat)

            offers = []
            for sel in ["div._3Ay6Sb", "div.UkvWh2", "div._2GcW2o", "div.yD2hv", "div._16v7t7", "span.b-offer"]:
                for el in item.select(sel):
                    t = el.get_text(strip=True)
                    if any(w in t.lower() for w in ["off", "discount", "cashback", "emi", "bank", "card", "exchange", "coupon", "bonus"]):
                        if 5 < len(t) < 100 and t not in offers:
                            offers.append(t)

            emi = None
            for f in features + offers:
                if "emi" in f.lower():
                    emi = f
                    break

            if name and (url or price):
                return {
                    "name": name,
                    "price": price,
                    "rating": rating,
                    "review_count": review_count,
                    "url": url or "https://www.flipkart.com",
                    "discount": discount,
                    "features": features[:10],
                    "offers": offers[:8],
                    "emi": emi,
                    "platform": "flipkart",
                }
        except Exception:
            return None
        return None

    # --- Strategy 1: Container Selectors ---
    items = (
        soup.select("div.cPH-V8")
        or soup.select("div.tX2u1b")
        or soup.select("div._75W9qi")
        or soup.select("div.yPfT85")
        or soup.select("div._1AtVbE div._13oc-S")
        or soup.select("div[data-id]")
        or soup.select("div._2kHMtA")
        or soup.select("div._1xHGtK._373qXS")
        or soup.select("div._1sd2w")
        or soup.select("div.slp-card")
    )
    for it in items:
        p = process_item(it)
        if p:
            products.append(p)

    if products:
        return products

    # --- Strategy 2: Product Link Parent nodes ---
    p_links = [a for a in soup.find_all("a") if a.get("href") and "/p/" in a.get("href")]
    seen = set()
    for a in p_links:
        parent = a.parent
        if parent and id(parent) not in seen:
            seen.add(id(parent))
            p = process_item(parent)
            if p:
                products.append(p)

    if products:
        return products

    # --- Strategy 3: Ancestor Card Containers ---
    seen = set()
    for a in p_links:
        curr = a.parent
        for _ in range(4):
            if not curr:
                break
            if id(curr) not in seen:
                seen.add(id(curr))
                p = process_item(curr)
                if p:
                    products.append(p)
                    break
            curr = curr.parent

    return products





# ── Ranker (shared across all platforms) ──────────────────────────────────────

def rank_products(products: list[dict], max_results: int = 5) -> list[dict]:
    """Rank products: prefer rating≥4.0, then by rating, reviews, discount."""
    def score(p: dict) -> tuple:
        rating = p.get("rating") or 0
        reviews = p.get("review_count") or 0
        discount = p.get("discount") or 0
        has_price = 1 if p.get("price") else 0
        tier = 1 if rating >= 4.0 else 0
        return (tier, rating, reviews, discount, has_price)

    ranked = sorted(products, key=score, reverse=True)
    return ranked[:max_results]
