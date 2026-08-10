"""
normalizer.py — Product Normalization Layer & Category Intelligence System for Trevor v2.0.
Converts all scraped and identified products into a unified, standard product schema.
"""

import html
import re

STANDARD_PRODUCT_SCHEMA = {
    "title": "",
    "brand": "",
    "model": "",
    "price": 0,
    "rating": 0.0,
    "reviews": 0,
    "description": "",
    "specifications": {},
    "offers": {
        "emi": [],
        "bank": [],
        "cashback": [],
        "exchange": [],
        "coupon": [],
        "partner": []
    },
    "purchase_url": ""
}


def extract_category_specifications(title: str, features: list[str] = None, category: str = "") -> dict:
    """
    Category Intelligence System:
    Extracts category-tailored specifications for Phones, Laptops, TVs, ACs, Refrigerators, Shoes, Clothing, etc.
    """
    features = features or []
    full_text = f"{title} {' '.join(features)}"
    specs = {}

    cat_lower = (category or "").lower()
    text_lower = full_text.lower()

    # 1. Shoes
    if any(k in cat_lower for k in ["shoe", "shoes", "sneaker", "footwear", "boot"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["shoe", "shoes", "sneaker", "sneakers", "running shoes", "sports shoes"]):
        mat_m = re.search(r"(Leather|Mesh|Canvas|Synthetic|Suede|Knit|Rubber)", full_text, re.I)
        if mat_m: specs["Material"] = mat_m.group(1).title()

        purp_m = re.search(r"(Running|Walking|Basketball|Gym|Training|Casual|Formal)", full_text, re.I)
        if purp_m: specs["Purpose"] = purp_m.group(1).title()

        sole_m = re.search(r"(Rubber Sole|EVA Sole|Air Cushion|Phylon)", full_text, re.I)
        if sole_m: specs["Sole"] = sole_m.group(1).title()

        if re.search(r"Waterproof|Water Resistant", full_text, re.I):
            specs["Waterproof"] = "Yes"

        wt_m = re.search(r"(\d+\s*g|\d+\.?\d*\s*kg)", full_text, re.I)
        if wt_m: specs["Weight"] = wt_m.group(1).strip()

    # 2. Clothing / Fashion
    elif any(k in cat_lower for k in ["shirt", "t-shirt", "jeans", "jacket", "dress", "clothing", "apparel"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["shirt", "t-shirt", "tshirt", "jeans", "jacket", "hoodie", "dress"]):
        fab_m = re.search(r"(100%\s*Cotton|Cotton Blend|Polyester|Denim|Linen|Silk|Fleece|Wool|Cotton)", full_text, re.I)
        if fab_m: specs["Material"] = fab_m.group(1).title()

        fit_m = re.search(r"(Regular Fit|Slim Fit|Relaxed Fit|Oversized Fit)", full_text, re.I)
        if fit_m: specs["Fit"] = fit_m.group(1).title()

        sleeve_m = re.search(r"(Half Sleeve|Full Sleeve|Sleeveless)", full_text, re.I)
        if sleeve_m: specs["Sleeve"] = sleeve_m.group(1).title()

        col_m = re.search(r"\b(Black|White|Blue|Navy|Red|Green|Grey|Gray|Yellow|Pink|Beige|Olive)\b", full_text, re.I)
        if col_m: specs["Color"] = col_m.group(1).title()

        occ_m = re.search(r"(Casual|Formal|Party|Sports|Work Wear)", full_text, re.I)
        if occ_m: specs["Occasion"] = occ_m.group(1).title()

    # 3. Laptops
    elif any(k in cat_lower for k in ["laptop", "notebook", "macbook", "chromebook"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["laptop", "notebook", "macbook", "chromebook", "vivobook", "legion", "nitro", "tuf"]):
        proc_m = re.search(r"(Intel\s*(?:Core\s*)?(?:i\d|Ultra\s*\d)[\w\d-]*|Ryzen\s*\d\s*[\w\d-]*|Apple\s*M\d\s*(?:Pro|Max)?)", full_text, re.I)
        if proc_m: specs["CPU"] = proc_m.group(1).strip()

        gpu_m = re.search(r"(NVIDIA\s*(?:GeForce\s*)?(?:RTX|GTX)\s*\d{4}[\w\d]*|AMD\s*Radeon[\w\d\s]*|Intel\s*(?:Iris\s*Xe|Arc)[\w\d]*)", full_text, re.I)
        if gpu_m: specs["GPU"] = gpu_m.group(1).strip()

        ram_m = re.search(r"(\d+\s*GB)\s*(?:DDR\d|RAM|Memory)", full_text, re.I)
        if ram_m: specs["RAM"] = ram_m.group(1).strip()

        ssd_m = re.search(r"(\d+\s*(?:GB|TB))\s*(?:SSD|NVMe|HDD)", full_text, re.I)
        if ssd_m: specs["SSD"] = ssd_m.group(1).strip()

        disp_m = re.search(r"(\d+\.?\d*\s*(?:inch|\"))", full_text, re.I)
        if disp_m: specs["Display"] = disp_m.group(1).strip()

        hz_m = re.search(r"(\d+\s*Hz)", full_text, re.I)
        if hz_m: specs["Refresh Rate"] = hz_m.group(1).strip()

        wt_m = re.search(r"(\d+\.?\d*\s*kg)", full_text, re.I)
        if wt_m: specs["Weight"] = wt_m.group(1).strip()

        bat_m = re.search(r"(\d+\s*(?:Hours?|Hrs)\s*(?:Battery|Backup)?)", full_text, re.I)
        if bat_m: specs["Battery"] = bat_m.group(1).strip()

        laptop_keys = ["CPU", "GPU", "RAM", "SSD", "Display", "Refresh Rate", "Battery", "Weight"]
        for k in laptop_keys:
            if k not in specs: specs[k] = "Not available"

    # 4. Phones / Smartphones
    elif any(k in cat_lower for k in ["phone", "mobile", "smartphone"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["phone", "mobile", "smartphone", "iphone", "galaxy", "poco", "iqoo", "redmi", "realme", "oneplus"]):
        proc_m = re.search(r"(Snapdragon\s*[\w\d\+]+|Dimensity\s*[\w\d\+]+|Helio\s*[\w\d\+]+|Bionic\s*A\d+|Tensor\s*G\d+|Exynos\s*[\w\d]+)", full_text, re.I)
        if proc_m: specs["Processor"] = proc_m.group(1).strip()

        ram_m = re.search(r"(\d+\s*GB)\s*(?:RAM|Memory)", full_text, re.I) or re.search(r"(\d+GB)\s*(?:\+|RAM|/)", full_text, re.I)
        if ram_m: specs["RAM"] = ram_m.group(1).strip()

        rom_m = re.search(r"(\d+\s*(?:GB|TB))\s*(?:ROM|Storage|Internal)", full_text, re.I)
        if rom_m: specs["Storage"] = rom_m.group(1).strip()

        disp_m = re.search(r"(\d+\.?\d*\s*(?:inch|\"|cm)?\s*(?:AMOLED|Super AMOLED|OLED|FHD\+|HD\+|LCD|IPS)[\w\s]*)", full_text, re.I)
        if disp_m: specs["Display"] = disp_m.group(1).strip()

        hz_m = re.search(r"(\d+\s*Hz)", full_text, re.I)
        if hz_m: specs["Refresh Rate"] = hz_m.group(1).strip()

        bat_m = re.search(r"(\d{4}\s*mAh)", full_text, re.I)
        if bat_m: specs["Battery"] = bat_m.group(1).strip()

        chg_m = re.search(r"(\d+W\s*(?:Fast\s*)?Charg\w*)", full_text, re.I)
        if chg_m: specs["Charging"] = chg_m.group(1).strip()

        cam_m = re.search(r"(\d+\s*MP[\w\s\+\-]*Camera|\d+\s*MP\s*OIS|\d+\s*MP\s*(?:Rear|Dual|Triple|Quad))", full_text, re.I)
        if cam_m: specs["Camera"] = cam_m.group(1).strip()

        if re.search(r"\b5G\b", full_text, re.I):
            specs["5G"] = "Yes"

        # Ensure Phone Spec Defaults
        phone_keys = ["Processor", "RAM", "Storage", "Display", "Refresh Rate", "Battery", "Camera", "5G"]
        for k in phone_keys:
            if k not in specs: specs[k] = "Not available"

    # 5. TVs / Monitors
    elif any(k in cat_lower for k in ["tv", "television", "monitor"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["tv", "television", "monitor"]):
        sz_m = re.search(r"(\d{2,3}\s*(?:inch|\")|\d{2,3}\s*cm)", full_text, re.I)
        if sz_m: specs["Screen Size"] = sz_m.group(1).strip()

        res_m = re.search(r"(4K Ultra HD|Full HD|HD Ready|8K)", full_text, re.I)
        if res_m: specs["Resolution"] = res_m.group(1).strip()

        panel_m = re.search(r"(QLED|OLED|LED|IPS|VA Panel)", full_text, re.I)
        if panel_m: specs["Panel Type"] = panel_m.group(1).strip()

        hz_m = re.search(r"(\d+\s*Hz)", full_text, re.I)
        if hz_m: specs["Refresh Rate"] = hz_m.group(1).strip()

        hdr_m = re.search(r"(Dolby Vision|HDR10\+|HDR10)", full_text, re.I)
        if hdr_m: specs["HDR"] = hdr_m.group(1).strip()

        os_m = re.search(r"(Google TV|Android TV|WebOS|Tizen|Fire TV)", full_text, re.I)
        if os_m: specs["Smart TV"] = os_m.group(1).strip()

        tv_keys = ["Screen Size", "Resolution", "Panel Type", "Refresh Rate", "Smart TV"]
        for k in tv_keys:
            if k not in specs: specs[k] = "Not available"

    # 6. Air Conditioners
    elif any(k in cat_lower for k in ["ac", "air conditioner"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["ac", "air conditioner", "split ac"]):
        cap_m = re.search(r"(\d+\.?\d*\s*Ton)", full_text, re.I)
        if cap_m: specs["Capacity"] = cap_m.group(1).strip()

        star_m = re.search(r"(\d\s*Star)", full_text, re.I)
        if star_m: specs["Star Rating"] = star_m.group(1).strip()

        inv_m = re.search(r"(Dual Inverter|Inverter|Smart Inverter)", full_text, re.I)
        if inv_m: specs["Inverter"] = inv_m.group(1).strip()

        war_m = re.search(r"(\d+\s*Years?\s*(?:Compressor)?\s*Warranty)", full_text, re.I)
        if war_m: specs["Warranty"] = war_m.group(1).strip()

    # 7. Refrigerators
    elif any(k in cat_lower for k in ["refrigerator", "fridge"]) or any(re.search(r'\b' + k + r'\b', text_lower) for k in ["refrigerator", "fridge"]):
        cap_m = re.search(r"(\d+\s*(?:L|Litre|Litres))", full_text, re.I)
        if cap_m: specs["Capacity"] = cap_m.group(1).strip()

        star_m = re.search(r"(\d\s*Star)", full_text, re.I)
        if star_m: specs["Star Rating"] = star_m.group(1).strip()

        comp_m = re.search(r"(Smart Inverter|Digital Inverter|Inverter Compressor)", full_text, re.I)
        if comp_m: specs["Compressor Type"] = comp_m.group(1).strip()

    return specs


def normalize_product(raw: dict, category: str = "") -> dict:
    """
    Normalizes any raw product dictionary into Trevor's standard product schema.
    """
    if not isinstance(raw, dict):
        return dict(STANDARD_PRODUCT_SCHEMA)

    title = str(raw.get("title") or raw.get("name") or "").strip()
    brand = str(raw.get("brand") or "").strip()
    model = str(raw.get("model") or "").strip()
    price = raw.get("price")
    try:
        price_val = int(price) if price is not None and str(price).isdigit() else (int(float(price)) if price is not None else 0)
    except:
        price_val = 0

    rating = raw.get("rating")
    try:
        rating_val = float(rating) if rating is not None else 0.0
    except:
        rating_val = 0.0

    reviews = raw.get("review_count") or raw.get("reviews") or 0
    try:
        reviews_val = int(reviews)
    except:
        reviews_val = 0

    description = str(raw.get("description") or raw.get("ai_advisor") or "").strip()
    url = str(raw.get("url") or raw.get("purchase_url") or "").strip()

    # Specifications normalization
    raw_specs = raw.get("specifications") or {}
    auto_specs = extract_category_specifications(title, raw.get("features", []), category)
    
    if isinstance(raw_specs, dict):
        merged_specs = {**auto_specs, **raw_specs}
    else:
        merged_specs = auto_specs

    # Offers normalization
    offers = {
        "emi": raw.get("emi_offers") or ([raw.get("emi")] if raw.get("emi") else []),
        "bank": raw.get("credit_offers") or raw.get("debit_offers") or raw.get("offers") or [],
        "cashback": raw.get("cashback_offers") or [],
        "exchange": raw.get("exchange_offers") or [],
        "coupon": raw.get("coupon_offers") or [],
        "partner": raw.get("partner_offers") or [],
    }

    return {
        "title": title,
        "brand": brand,
        "model": model,
        "price": price_val,
        "rating": rating_val,
        "reviews": reviews_val,
        "description": description,
        "specifications": merged_specs,
        "offers": offers,
        "purchase_url": url,
        # Preserve original fields for legacy compat
        "name": title,
        "url": url,
    }
