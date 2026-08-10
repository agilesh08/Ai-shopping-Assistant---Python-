import json
import logging
import os
import re
from PIL import Image
from config import GEMINI_API_KEY
import query_builder

logger = logging.getLogger("trevor.vision_gemini")

# Import official Google Gemini SDK (google.genai or fallback google.generativeai)
USE_GENAI_SDK = False
try:
    from google import genai
    from google.genai import types
    USE_GENAI_SDK = True
except ImportError:
    import google.generativeai as legacy_genai
    if GEMINI_API_KEY:
        legacy_genai.configure(api_key=GEMINI_API_KEY)


def analyze_product_image(image_path: str) -> dict:
    """
    Analyzes a product photo/screenshot using Google Gemini Vision API (Free Tier).
    Returns structured JSON product understanding. Python backend builds the search query.
    """
    logger.info("[Vision] Uploading image...")
    if not GEMINI_API_KEY:
        logger.error("[Vision] GEMINI_API_KEY is not set in .env file.")
        return {
            "status": "vision_error",
            "message": "⚠️ I couldn't analyze your image right now because the vision service is temporarily unavailable. Please try again in a few moments."
        }

    try:
        img = Image.open(image_path)
    except Exception as e:
        logger.error(f"[Vision] Failed to open image file {image_path}: {e}")
        return {
            "status": "vision_error",
            "message": "⚠️ I couldn't analyze your image right now because the vision service is temporarily unavailable. Please try again in a few moments."
        }

    prompt = """You are an expert AI shopping vision assistant for Amazon India. Analyze the provided image or screenshot.

Perform OCR to extract all visible text from labels, boxes, logos, stickers, and UI elements.

Return ONLY a raw JSON object containing structured product understanding with 19 fields:
1. "category": (Specific category e.g. "shirt", "t-shirt", "smartphone", "laptop", "shoes", "smartwatch", "tv", "refrigerator", "ac", "jeans", "jacket", "headphones", "bag")
2. "sub_category": (Subcategory e.g. "casual shirt", "flagship phone", "gaming laptop", "running shoes")
3. "product_type": (Mandatory Enum: "PHONE", "LAPTOP", "CLOTHING", "SHOES", "HEADPHONES", "TV", "APPLIANCE", "WATCH", "BAG", "BEAUTY", "FURNITURE", "OTHER")
4. "gender": (Gender target if applicable: "men", "women", "unisex", "kids", or null)
5. "brand": (Visible brand name e.g. "Nike", "Apple", "ASUS", "Samsung", "Sony", "Puma", or null)
6. "model": (Exact model series e.g. "iPhone 16 Pro", "TUF Gaming A15", "Galaxy M35", or null)
7. "variant": (Style/capacity variant e.g. "256GB", "16GB RAM", or null)
8. "pattern": (Clothing pattern e.g. "Plaid Check", "Solid", "Printed", "Striped", or null)
9. "primary_color": (Main color e.g. "Blue", "White", "Black", "Silver", or null)
10. "secondary_color": (Accent color e.g. "Peach", "Red", "Grey", or null)
11. "material": (Material e.g. "Cotton", "Denim", "Leather", "Mesh", or null)
12. "fit": (Fit style e.g. "Relaxed", "Slim", "Regular", "Oversized", or null)
13. "sleeve": (Sleeve type e.g. "Full Sleeve", "Half Sleeve", "Sleeveless", or null)
14. "collar": (Collar/neck type e.g. "Round Neck", "Polo Collar", "V-Neck", or null)
15. "style": (Style theme e.g. "Casual", "Formal", "Sports", "Gaming", or null)
16. "occasion": (Occasion e.g. "Party", "Work", "Daily", or null)
17. "size": (Visible size e.g. "M", "L", "XL", "Size 9", or null)
18. "specifications": (JSON object of key specs for electronics, e.g. {"storage":"256GB", "camera":"Triple Camera"})
19. "confidence": (Confidence float from 0.0 to 1.0)

CRITICAL RULES:
- Output MUST be valid RAW JSON only. Do NOT surround with markdown code blocks.
- UNKNOWN fields MUST be null (JSON literal null), NEVER string "None" or "Unknown".

EXAMPLE JSON OUTPUT:
{
  "category": "shirt",
  "sub_category": "casual shirt",
  "product_type": "CLOTHING",
  "gender": "men",
  "brand": null,
  "model": null,
  "variant": null,
  "pattern": "Plaid Check",
  "primary_color": "Blue",
  "secondary_color": "Peach",
  "material": "Cotton",
  "fit": "Relaxed",
  "sleeve": "Full Sleeve",
  "collar": null,
  "style": "Casual",
  "occasion": null,
  "size": null,
  "specifications": {},
  "confidence": 0.96
}
"""

    try:
        if USE_GENAI_SDK:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[img, prompt]
            )
            raw_text = response.text.strip()
        else:
            model = legacy_genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(
                [prompt, img],
                generation_config={"temperature": 0.1}
            )
            raw_text = response.text.strip()

        logger.info("[Vision] Gemini analysis completed")

        # Clean JSON fences if present
        if "```" in raw_text:
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

        result = json.loads(raw_text, strict=False)
        result["raw_text"] = raw_text

        # Sanitize any string "None" or "Unknown" to Python None
        for k, v in result.items():
            if isinstance(v, str) and v.strip().lower() in {"none", "null", "unknown", "n/a"}:
                result[k] = None

        brand = result.get("brand")
        prod_model = result.get("model")
        conf = float(result.get("confidence", 0.0))

        logger.info(f"[Vision] Brand: {brand}")
        logger.info(f"[Vision] Model: {prod_model}")
        logger.info(f"[Vision] Confidence: {conf}")

        if conf < 0.50:
            return {
                "status": "low_confidence",
                "confidence": conf,
                "message": "😅 I couldn't confidently identify this product. Could you upload a clearer image or a closer photo?"
            }
        elif conf <= 0.79:
            result["status"] = "success"
            result["confidence_warning"] = "I identified this product with medium confidence; some minor details might vary."
        else:
            result["status"] = "success"

        # Build clean Amazon search query using Python Search Query Builder
        search_q = query_builder.build_amazon_search_query(result)
        identified_title = query_builder.build_identified_product_name(result)

        result["search_query"] = search_q
        result["identified_product"] = identified_title

        logger.info(f"[Shopping] Python Built Query: '{search_q}'")
        logger.info(f"[Shopping] Identified Title: '{identified_title}'")

        return result

    except Exception as e:
        logger.error(f"[Vision] Gemini vision API error: {e}", exc_info=True)
        return {
            "status": "vision_error",
            "message": "⚠️ I couldn't analyze your image right now because the vision service is temporarily unavailable. Please try again in a few moments."
        }
        raw_text = response.text.strip()

        # Clean JSON fences if present
        if "```" in raw_text:
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

        result = json.loads(raw_text, strict=False)
        result["raw_text"] = raw_text

        brand = result.get("brand", "")
        prod_model = result.get("model", "")
        conf = float(result.get("confidence", 0.0))

        logger.info(f"[Vision] Brand: {brand}")
        logger.info(f"[Vision] Model: {prod_model}")
        logger.info(f"[Vision] Confidence: {conf}")

        # Confidence Rules:
        # >= 0.80 -> Automatically search Amazon
        # 0.50 - 0.79 -> Search Amazon with warning
        # < 0.50 -> Ask for clearer image without searching Amazon
        if conf < 0.50:
            return {
                "status": "low_confidence",
                "confidence": conf,
                "message": "😅 I couldn't confidently identify this product. Could you upload a clearer image or a closer photo?"
            }
        elif conf <= 0.79:
            result["status"] = "success"
            result["confidence_warning"] = "I identified this product with medium confidence; some minor details might vary."
        else:
            result["status"] = "success"

        search_q = result.get("search_query") or f"{brand} {prod_model} {result.get('category', '')}".strip()
        result["search_query"] = search_q
        logger.info(f"[Shopping] Query: {search_q}")

        return result

    except Exception as e:
        logger.error(f"[Vision] Gemini vision API error: {e}", exc_info=True)
        return {
            "status": "vision_error",
            "message": "⚠️ I couldn't analyze your image right now because the vision service is temporarily unavailable. Please try again in a few moments."
        }
