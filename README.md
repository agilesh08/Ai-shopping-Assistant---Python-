# AI Shopping & Styling Assistant 

AI Shopping & Styling Assistant (Trevor AI) is an advanced, production-grade conversational AI Shopping & Styling Assistant built for Telegram. It combines local LLMs (**Llama 3.2 3B** via Ollama) with multimodal vision (**Google Gemini 2.5 Flash**), real-time Amazon India retrieval, weighted semantic ranking, product intelligence scoring, and AI buying recommendations.

---

## Key Features

- **Multimodal Image Shopping**: Upload any product image to get visual identification and real-time Amazon India product matching.
- **Broad Category Expansion**: Automatically expands broad queries (e.g. `Gardening Equipment`, `Computer Accessories`, `Kitchen Appliances`) into subcategory search candidates for maximum product diversity.
- **Category Transition Manager**: Detects category switches across turns (e.g. `Laptop -> Water Heater`) and resets context safely while preserving user preferences.
- **Conversation Memory Engine**: Tracks shopping session context across turns with ordinal reference resolution (`"first product"`, `"compare 1st and 3rd"`).
- **Category-Aware Weighted Ranking Engine**: Custom weighting models tailored per category (Laptops, Phones, Headphones, Water Heaters, Clothing, Shoes).
- **Product Intelligence Layer**: Extracts category-tailored specifications and calculates the **Shopping Value Score (0–100)**.
- **AI Decision Engine**: Assigns non-overlapping recommendation badges with factual Pros & Cons.
- **Personalized Styling Advisor**: Generates fashion and outfit advice powered by Llama 3.2.

**Built By Agilesh T** 
