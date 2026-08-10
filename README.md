# AI Shopping & Styling Assistant 🛍️✨

AI Shopping & Styling Assistant (Trevor AI) is an advanced, production-grade conversational AI Shopping & Styling Assistant built for Telegram. It combines local LLMs (**Llama 3.2 3B** via Ollama) with multimodal vision (**Google Gemini 2.5 Flash**), real-time Amazon India retrieval, weighted semantic ranking, product intelligence scoring, and AI buying recommendations.

---

## 🚀 Key Features

- 📸 **Multimodal Image Shopping**: Upload any product image to get visual identification and real-time Amazon India product matching.
- 🌐 **Broad Category Expansion**: Automatically expands broad queries (e.g. `Gardening Equipment`, `Computer Accessories`, `Kitchen Appliances`) into subcategory search candidates for maximum product diversity.
- 🔄 **Category Transition Manager**: Detects category switches across turns (e.g. `Laptop -> Water Heater`) and resets context safely while preserving user preferences.
- 🧠 **Conversation Memory Engine**: Tracks shopping session context across turns with ordinal reference resolution (`"first product"`, `"compare 1st and 3rd"`).
- ⚖️ **Category-Aware Weighted Ranking Engine**: Custom weighting models tailored per category (Laptops, Phones, Headphones, Water Heaters, Clothing, Shoes).
- 📊 **Product Intelligence Layer**: Extracts category-tailored specifications and calculates the **Shopping Value Score (0–100)**.
- 🏆 **AI Decision Engine**: Assigns non-overlapping recommendation badges (`🏆 Best Overall`, `💰 Best Value for Money`, `🏷️ Best Budget`) with factual Pros & Cons.
- 👗 **Personalized Styling Advisor**: Generates fashion and outfit advice powered by Llama 3.2.

---

## 🛠️ Technology Stack

- **Language**: Python 3.11+
- **Bot Framework**: `python-telegram-bot` (v21.9)
- **Local LLM**: Llama 3.2 3B *(via Ollama)*
- **Vision Model**: Google Gemini 2.5 Flash API
- **Web Scraping**: ScraperAPI Proxy, `BeautifulSoup4`, `lxml`
- **Networking**: `requests`, `httpx`, `asyncio`

---

## 📐 Pipeline Architecture

```
User Input (Image / Text)
        │
        ▼
Intent Detection & Category Classifier (llm.py)
        │
        ▼
Broad Category & Subcategory Expansion Engine (broad_category.py)
        │
        ▼
Category Transition Manager (category_manager.py)
        │
        ▼
Conversation Memory Engine (memory_engine.py)
        │
        ▼
Multi-Stage Retrieval Engine (retrieval.py / shopping.py)
        │
        ▼
Category-Aware Weighted Semantic Ranking Engine (ranker.py)
        │
        ▼
Product Intelligence Layer (product_intelligence.py)
        │
        ▼
AI Decision Engine (decision_engine.py)
        │
        ▼
Telegram Card Formatter (formatter.py)
```

---

## 📦 Prerequisites

- **Python 3.11+**
- **[Ollama](https://ollama.com)** with `llama3.2:3b` model
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
- **Google Gemini API Key**
- **ScraperAPI Key**

---

## ⚙️ Setup & Installation

### 1. Install Ollama and pull model
```bash
ollama pull llama3.2:3b
ollama serve
```

### 2. Clone repository & install dependencies
```bash
git clone https://github.com/agilesh08/Ai-shopping-Assistant---Python-.git
cd "Ai-shopping-Assistant---Python-"
pip install -r requirements.txt
```

### 3. Configure `.env` file
Copy `.env.example` to `.env` and fill in your keys:
```env
TELEGRAM_TOKEN=your_telegram_bot_token
SCRAPER_API_KEY=your_scraperapi_key
GEMINI_API_KEY=your_gemini_api_key
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

### 4. Start Trevor AI Bot
```bash
python bot.py
```

---

