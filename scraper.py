"""
scraper.py — ScraperAPI wrapper (supports optional JS rendering for Myntra etc.)
"""

import requests
from config import SCRAPER_API_KEY

SCRAPER_URL = "https://api.scraperapi.com/"


def fetch_html(url: str, render_js: bool = False) -> str | None:
    """
    Fetch a page's HTML via ScraperAPI.

    Args:
        url: The target URL to scrape
        render_js: If True, ScraperAPI will execute JavaScript before returning HTML
                   (needed for React/Angular SPAs like Myntra)

    Returns:
        Raw HTML string, or None on failure
    """
    params = {
        "api_key": SCRAPER_API_KEY,
        "url": url,
        "country_code": "in",
        "render": "true" if render_js else "false",
    }

    try:
        timeout = 25
        response = requests.get(SCRAPER_URL, params=params, timeout=timeout)

        if response.status_code == 200:
            return response.text
        elif response.status_code == 403:
            print(f"[Scraper] 403 Forbidden — check your API key")
        elif response.status_code == 429:
            print(f"[Scraper] 429 Rate limited")
        elif response.status_code == 500:
            print(f"[Scraper] 500 ScraperAPI internal error for URL: {url}")
        else:
            print(f"[Scraper] HTTP {response.status_code} for URL: {url}")
        return None

    except requests.exceptions.Timeout:
        print(f"[Scraper] Timeout fetching: {url}")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"[Scraper] Connection error: {e}")
        return None
    except Exception as e:
        print(f"[Scraper] Unexpected error: {e}")
        return None


# Keep old name for backward compat
def fetch_amazon_html(search_url: str) -> str | None:
    return fetch_html(search_url, render_js=False)
