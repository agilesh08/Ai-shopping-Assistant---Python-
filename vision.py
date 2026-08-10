"""
vision.py — Unified Vision Module for Trevor AI Shopping Assistant.
Routes product photo/screenshot requests to Google Gemini Vision API (vision_gemini.py).
"""

import vision_gemini

def analyze_product_image(image_path: str) -> dict:
    """Analyze product photo/screenshot using Gemini Vision API."""
    return vision_gemini.analyze_product_image(image_path)
