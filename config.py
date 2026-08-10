import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
VISION_MODEL = os.getenv("VISION_MODEL", "llava:7b")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in .env file")
if not SCRAPER_API_KEY:
    raise ValueError("SCRAPER_API_KEY is not set in .env file")
