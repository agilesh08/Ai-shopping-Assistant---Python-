"""
bot.py — Main Telegram bot entry point for Maya.

Run with: python bot.py
"""

import asyncio
# Python 3.10+ fix: ensure an event loop exists before telegram-bot calls get_event_loop()
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import logging
import random
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import config
from config import TELEGRAM_TOKEN
import session as sess
import llm
import vision
import retry_utils
import time
from shopping import search_products
from formatter import (
    format_products,
    format_shopping_response,
    format_platform_prompt,
    format_no_results,
    format_no_brand_results,
    format_scrape_error,
    format_llm_error,
    format_welcome,
    format_help,
    get_random_image_ack_message,
)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("trevor")

SIGNATURE = "Ai automation created My Agilesh T"


def _append_signature(text: str) -> str:
    if not text:
        return text
    clean_text = text.strip()
    if SIGNATURE in clean_text:
        return clean_text
    return f"{clean_text}\n\n{SIGNATURE}"


async def send_typing(update: Update) -> None:
    await update.effective_chat.send_action("typing")


# ── Command Handlers ───────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sess.reset_session(chat_id)
    await update.message.reply_text(_append_signature(format_welcome()), parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(_append_signature(format_help()))


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sess.reset_session(chat_id)
    await update.message.reply_text(_append_signature("🔄 Fresh start! What can I help you with?"))



async def _execute_shopping_search(update: Update, session: dict, chat_id: int) -> None:
    state = session.get("shopping_state")
    if not state:
        return
        
    platform = "amazon"
    state["marketplace"] = "amazon"
        
    if "search_query" in state and state["search_query"]:
        clean_query = state["search_query"].strip()
    else:
        product = state.get("product") or ""
        budget = state.get("budget") or ""
        filters = state.get("filters") or ""
        
        parts = [product]
        if budget:
            b_str = str(budget).strip()
            if b_str.isdigit():
                parts.append(f"under {b_str}")
            else:
                parts.append(b_str)
        if filters:
            parts.append(str(filters).strip())
            
        clean_query = " ".join(p for p in parts if p).strip()
    
    platform_labels = {"amazon": "Amazon 🔵", "flipkart": "Flipkart 🟡"}
    label = platform_labels.get(platform, "Amazon 🔵")
    
    SEARCH_MESSAGES = [
        "🔍 Nice choice! Let me find the best deals...",
        "⚡ Comparing ratings and live prices on Amazon...",
        "🛒 Looking for the highest-rated products...",
        "💸 Checking today's discounts and bank offers...",
        "⭐ Finding products worth your money...",
        "🎯 Matching products to your exact requirements...",
        "🛍 Great choice! Let me find some highly rated options for you...",
    ]
    
    last_msg = session.get("last_search_msg")
    available_msgs = [m for m in SEARCH_MESSAGES if m != last_msg]
    chosen_msg = random.choice(available_msgs)
    session["last_search_msg"] = chosen_msg
    
    formatted_msg = chosen_msg.format(label=f"*{label}*")
    
    processing_msg = await update.message.reply_text(
        formatted_msg,
        parse_mode="Markdown",
    )
    
    try:
        result = await search_products(clean_query, state, platform=platform)
        reply = _handle_shopping_result(result, state)
    except Exception as e:
        logger.error(f"Error searching {platform}: {e}", exc_info=True)
        reply = f"❌ Sorry, an error occurred while searching {platform}. Please try again later."
        
    reply = _append_signature(reply)
    sess.add_message(chat_id, "assistant", reply)
    
    await processing_msg.delete()
    await update.message.reply_text(reply, parse_mode="HTML")

# ── Helpers ────────────────────────────────────────────────────────────────────

def _handle_shopping_result(result: dict, state: dict = None) -> str:
    status = result.get("status")
    products = result.get("products", [])
    query = result.get("query", "")
    platform = result.get("platform", "amazon")

    is_image = bool(state and state.get("is_image_search"))
    id_product = (state.get("identified_product") or "") if state else ""
    cat = (state.get("category") or "") if state else ""

    top_title = products[0].get("name") if products and isinstance(products[0], dict) else "None"

    print("\n===== BEFORE FORMATTER =====")
    print(f"Category: {cat or 'Unknown'}")
    print(f"Products Count: {len(products)}")
    print(f"Top Product Title: {top_title}")
    print("============================\n")

    if status == "ok" and products:
        rendered = format_products(products, query, platform, is_image_search=is_image, identified_product=id_product, category=cat, state=state)
        first_line = rendered.split("\n")[0] if rendered else ""
        print("===== TELEGRAM OUTPUT =====")
        print(f"Category: {cat or 'Unknown'}")
        print(f"Rendered Header: {first_line}")
        print(f"Rendered Top Product: {top_title}")
        print("===========================\n")
        return rendered
    elif status == "no_results":
        return format_no_results(query)
    elif status == "no_brand_results":
        return format_no_brand_results(query)
    elif status == "scrape_error":
        return format_scrape_error()
    else:
        return "❌ Sorry, an error occurred while searching. Please try again later."

# ── Main Message Handler ───────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Core handler — routes every message through Trevor's brain with full error isolation."""
    if not update.effective_chat or not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_message = update.message.text.strip()
    if not user_message:
        return

    try:
        session = sess.get_session(chat_id)
        sess.add_message(chat_id, "user", user_message)
        await send_typing(update)
        
        msg_lower = user_message.lower()
        if "flipkart" in msg_lower:
            reply = _append_signature("Currently I support Amazon India only. Flipkart support is under development and will be available in a future update.")
            sess.add_message(chat_id, "assistant", reply)
            await update.message.reply_text(reply)
            return

        has_shopping_state = bool(session.get("shopping_state"))

        # ── Handle pending Amazon confirmation after styling ─────────────────────
        if session.get("awaiting_amazon"):
            intent = llm.classify_intent(user_message, session["history"])
            is_yes = intent == "amazon_yes" or any(
                w in user_message.lower()
                for w in ["yes", "yeah", "sure", "find", "show", "ok", "okay", "haan", "ha", "yep"]
            )
            is_no = any(
                w in user_message.lower()
                for w in ["no", "nah", "nope", "don't", "dont", "nahin", "nahi"]
            )

            if is_yes:
                session["awaiting_amazon"] = False
                styling_topic = session.get("last_styling_topic", user_message)
                session["shopping_state"] = {
                    "product": styling_topic,
                    "budget": None,
                    "filters": None,
                    "marketplace": "amazon"
                }
                await _execute_shopping_search(update, session, chat_id)
                return

            elif is_no:
                session["awaiting_amazon"] = False
                reply = _append_signature("No problem! Feel free to ask me anything else 😊")
                sess.add_message(chat_id, "assistant", reply)
                await update.message.reply_text(reply)
                return

        # ── Handle pending Amazon confirmation after Shopping Advisor advice ───
        if session.get("awaiting_amazon_advisor"):
            intent = llm.classify_intent(user_message, session["history"])
            is_yes = intent == "amazon_yes" or any(
                w in user_message.lower()
                for w in ["yes", "yeah", "sure", "find", "show", "ok", "okay", "haan", "ha", "yep", "search", "get", "same", "these"]
            ) or llm.is_shopping_query(user_message)
            
            is_no = any(
                w in user_message.lower()
                for w in ["no", "nah", "nope", "don't", "dont", "nahin", "nahi"]
            )

            if is_yes:
                session["awaiting_amazon_advisor"] = False
                rec_models = session.get("advisor_recommended_models") or session.get("recommended_models") or []
                is_same_request = any(w in user_message.lower() for w in ["same", "them", "these", "above", "recommended", "those"])

                if is_same_request and rec_models:
                    model_q = " ".join(rec_models[:3])
                    new_state = {
                        "search_query": model_q,
                        "product": model_q,
                        "marketplace": "amazon"
                    }
                else:
                    topic = session.get("last_advisor_topic", user_message)
                    combined = f"{topic} {user_message}"
                    new_state = llm.update_shopping_state(combined, None, session["history"])

                session["shopping_state"] = new_state
                await _execute_shopping_search(update, session, chat_id)
                return

            elif is_no:
                session["awaiting_amazon_advisor"] = False
                reply = _append_signature("No problem! Feel free to ask me anything else 😊")
                sess.add_message(chat_id, "assistant", reply)
                await update.message.reply_text(reply)
                return

        # ── Classify intent ──────────────────────────────────────────────────────
        intent = llm.classify_intent(user_message, session["history"])
        
        # Hard safety guardrail: force shopping_advisor or shopping intent
        if intent != "reminder" and llm.is_advisor_query(user_message):
            intent = "shopping_advisor"
        elif intent != "reminder" and llm.is_shopping_query(user_message):
            intent = "shopping"
            
        pure_greetings = {"hi", "hello", "hey", "hola", "sup", "good morning", "good evening", "bye"}
        if msg_lower in pure_greetings:
            session["shopping_state"] = None

        if has_shopping_state and intent not in {"styling", "shopping_advisor", "reminder"} and msg_lower not in pure_greetings:
            intent = "shopping"

        logger.info(f"[{chat_id}] Intent: {intent} | Msg: {user_message[:60]}")

        # ── Route ────────────────────────────────────────────────────────────────
        if intent == "shopping":
            session["mode"] = "shopping"
            current_state = session.get("shopping_state")
            new_state = llm.update_shopping_state(user_message, current_state, session["history"])
            
            if "error" in new_state:
                reply = _append_signature(format_llm_error())
                sess.add_message(chat_id, "assistant", reply)
                await update.message.reply_text(reply)
                return
                
            session["shopping_state"] = new_state
            
            if new_state.get("needs_clarification") and new_state.get("clarification_question"):
                reply = _append_signature(new_state["clarification_question"])
                sess.add_message(chat_id, "assistant", reply)
                await update.message.reply_text(reply)
                return

            await _execute_shopping_search(update, session, chat_id)

        elif intent == "shopping_advisor":
            session["mode"] = "advisor"
            advisor_result = llm.get_shopping_advisor_advice(user_message, session["history"])
            reply = _append_signature(advisor_result["advice"])

            session["awaiting_amazon_advisor"] = True
            session["last_advisor_topic"] = user_message
            session["advisor_recommended_models"] = advisor_result.get("recommended_models", [])

            sess.add_message(chat_id, "assistant", reply)
            await update.message.reply_text(reply)

        elif intent == "styling":
            session["mode"] = "styling"
            styling_result = llm.get_styling_advice(user_message, session["history"])
            reply = _append_signature(styling_result["advice"])

            if styling_result["ready"]:
                session["awaiting_amazon"] = True
                session["last_styling_topic"] = user_message
                sess.add_message(chat_id, "assistant", reply)
                await update.message.reply_text(reply)
            else:
                sess.add_message(chat_id, "assistant", reply)
                await update.message.reply_text(reply)

        elif intent == "amazon_yes":
            if has_shopping_state:
                session["mode"] = "shopping"
                new_state = llm.update_shopping_state(user_message, session["shopping_state"], session["history"])
                if "error" not in new_state:
                    session["shopping_state"] = new_state
                    
                    if new_state.get("needs_clarification") and new_state.get("clarification_question"):
                        reply = _append_signature(new_state["clarification_question"])
                        sess.add_message(chat_id, "assistant", reply)
                        await update.message.reply_text(reply)
                        return
                        
                await _execute_shopping_search(update, session, chat_id)
            else:
                reply = _append_signature("Sure! What are you looking for? Tell me the product and I'll search right away! 🛍")
                sess.add_message(chat_id, "assistant", reply)
                await update.message.reply_text(reply)

        elif intent == "reminder":
            import uuid
            from datetime import datetime
            
            reminder_data = llm.create_reminder(user_message, session["history"])
            if "error" in reminder_data:
                reply = _append_signature(format_llm_error())
            else:
                reminder_data["reminder_id"] = str(uuid.uuid4())[:8]
                category = reminder_data.get("category") or "General"
                budget = reminder_data.get("budget") or "Any"
                marketplace = (reminder_data.get("marketplace") or "Amazon").capitalize()
                rem_date = reminder_data.get("reminder_date") or "When available"
                rem_time = reminder_data.get("reminder_time") or "ASAP"
                
                reply = _append_signature(
                    "✅ Reminder Created\n\n"
                    "Category\n"
                    f"{category}\n\n"
                    "Budget\n"
                    f"{budget}\n\n"
                    "Marketplace\n"
                    f"{marketplace}\n\n"
                    "Reminder Time\n"
                    f"{rem_date}\n"
                    f"{rem_time}\n\n"
                    f"I'll remind you on {rem_date} at {rem_time} and can also check for good deals matching your requirements."
                )
                
                reminder_data["created_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if not reminder_data.get("status"):
                    reminder_data["status"] = "Active"
                
                import json
                try:
                    with open("reminders.json", "a") as f:
                        f.write(json.dumps(reminder_data) + "\n")
                except:
                    pass

            sess.add_message(chat_id, "assistant", reply)
            await update.message.reply_text(reply)

        else:
            reply = llm.general_chat(user_message, session["history"])
            if reply.startswith("__OLLAMA"):
                reply = _ollama_error_message(reply)
            reply = _append_signature(reply)
            sess.add_message(chat_id, "assistant", reply)
            await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Unhandled error handling message for chat {chat_id}: {e}", exc_info=True)
        safe_reply = _append_signature("Sorry, I couldn't retrieve products right now. Please try again.")
        try:
            await update.message.reply_text(safe_reply)
        except Exception:
            pass
# ── Helpers ────────────────────────────────────────────────────────────────────

def _handle_shopping_result(result: dict, state: dict | None = None) -> str:
    status = result.get("status")
    products = result.get("products", [])
    query = result.get("query", "")
    platform = result.get("platform", "amazon")

    is_image = bool(state and state.get("is_image_search"))
    id_product = (state.get("identified_product") or "") if state else ""

    if status == "ok" and products:
        return format_products(products, query, platform, is_image_search=is_image, identified_product=id_product)
    elif status == "no_brand_results":
        req_brand = result.get("requested_brand", "requested brand")
        return format_no_brand_results(req_brand, query, platform)
    elif status == "no_results":
        return format_no_results(query, platform)
    elif status == "scrape_failed":
        return format_scrape_error(platform)
    elif status == "llm_error":
        return format_llm_error()
    else:
        return format_no_results(query, platform)


def _ollama_error_message(error: str) -> str:
    if "OFFLINE" in error:
        return (
            "⚠️ I can't reach my AI brain right now. "
            "Please make sure Ollama is running (`ollama serve`) and try again!"
        )
    if "TIMEOUT" in error:
        return "⏳ That took too long. Please try again!"
    return "⚠️ Something went wrong. Please try again in a moment."


# ── Main ───────────────────────────────────────────────────────────────────────

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all error handler for Telegram Application loop."""
    logger.error(f"Global Telegram Exception: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                _append_signature("Sorry, I couldn't retrieve products right now. Please try again.")
            )
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")


async def _update_progress(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, stop_event: asyncio.Event):
    """Background progress ticker that updates user message at 5s, 10s, 15s, 20s."""
    updates = [
        (5, "👀 I'm identifying the product..."),
        (10, "🛍️ Looking for the closest matching products on Amazon..."),
        (15, "💳 Checking today's discounts and bank offers..."),
        (20, "⏳ Almost done! Large images can take a little longer.")
    ]
    start_time = time.time()
    for delay, text in updates:
        elapsed = time.time() - start_time
        remaining = delay - elapsed
        if remaining > 0:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=remaining)
                return
            except asyncio.TimeoutError:
                pass

        if stop_event.is_set():
            return

        try:
            msg_text = _append_signature(f"😊 I've received your image!\n\n{text}")
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg_text)
        except Exception:
            pass


async def _process_image_background(update: Update, context: ContextTypes.DEFAULT_TYPE, photo, chat_id: int, status_msg):
    """
    Fault-Tolerant Background Worker:
    Processes uploaded images asynchronously without blocking the Telegram handler.
    Retries network timeouts, updates progress, and preserves partial recognition results.
    """
    import os
    import html
    os.makedirs("temp_images", exist_ok=True)
    temp_path = os.path.join("temp_images", f"photo_{chat_id}_{update.message.message_id}.jpg")

    stop_progress = asyncio.Event()
    progress_task = asyncio.create_task(_update_progress(context, chat_id, status_msg.message_id, stop_progress))
    pipeline_start = time.time()

    try:
        # Step 1: Download Image via Retry System
        t0 = time.time()
        try:
            tg_file = await retry_utils.async_retry(
                context.bot.get_file, photo.file_id,
                retries=4, initial_delay=1.0, stage_name="Telegram get_file"
            )
            await retry_utils.async_retry(
                tg_file.download_to_drive, temp_path,
                retries=4, initial_delay=1.0, stage_name="Telegram download"
            )
        except Exception as e:
            stop_progress.set()
            logger.error(f"[{chat_id}] Telegram file download failed after retries: {e}")
            reply = _append_signature("📡 Telegram is taking longer than usual to send the image. I tried multiple times. Could you please try resending the image?")
            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=reply)
            return

        t_down = time.time() - t0
        logger.info(f"[{chat_id}] [Image] Downloaded in {t_down:.2f} sec")

        # Step 2: Pass image to Gemini Vision API via Retry System
        t1 = time.time()
        try:
            analysis = await retry_utils.async_retry(
                vision.analyze_product_image, temp_path,
                retries=3, initial_delay=1.0, stage_name="Gemini Vision"
            )
        except Exception as e:
            stop_progress.set()
            logger.error(f"[{chat_id}] Gemini vision API failed after retries: {e}")
            reply = _append_signature("🧠 The vision service is responding slowly right now. Please try uploading the image again in a moment.")
            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=reply)
            return

        t_vis = time.time() - t1
        logger.info(f"[{chat_id}] [Vision] Gemini completed in {t_vis:.2f} sec")

        status = analysis.get("status")
        conf = float(analysis.get("confidence", 1.0))
        if status in {"blurry", "no_product", "error", "vision_error", "low_confidence"} or conf < 0.5:
            stop_progress.set()
            reply_text = analysis.get("message", "😅 I couldn't confidently identify the product in this image. Could you please upload a clearer or closer image?")
            reply = _append_signature(reply_text)
            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=reply)
            return

        search_q = analysis.get("search_query") or query_builder.build_amazon_search_query(analysis)
        identified_name = analysis.get("identified_product") or query_builder.build_identified_product_name(analysis)

        session = sess.get_session(chat_id)
        new_state = llm.update_shopping_state(search_q, None, session["history"])
        new_state["is_image_search"] = True
        new_state["identified_product"] = identified_name
        new_state["product_type"] = analysis.get("product_type", "")
        new_state["vision_metadata"] = analysis  # Requirement 4: Save structured vision JSON in session state
        session["shopping_state"] = new_state

        # Step 3: Amazon Search via Retry System
        t2 = time.time()
        search_res = None
        try:
            search_res = await retry_utils.async_retry(
                search_products, search_q, new_state, "amazon",
                retries=3, initial_delay=1.0, stage_name="Amazon Search"
            )
        except Exception as e:
            logger.error(f"[{chat_id}] Amazon search failed after retries: {e}")

        t_srch = time.time() - t2
        logger.info(f"[{chat_id}] [Search] Amazon completed in {t_srch:.2f} sec")

        stop_progress.set()

        # Step 4: Formatter & Recovery Strategy
        t3 = time.time()
        if search_res and search_res.get("products"):
            formatted_text = format_shopping_response(search_res, new_state)
            reply = _append_signature(formatted_text)
            t_fmt = time.time() - t3
            t_total = time.time() - pipeline_start
            logger.info(f"[{chat_id}] [Formatter] Formatted in {t_fmt:.2f} sec | Total elapsed: {t_total:.2f} sec")
            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=reply, parse_mode="HTML", disable_web_page_preview=True)
        else:
            # Recovery Strategy: Preserve recognized product info even if search fails!
            recovery_text = f"📸 I identified your product: <b>{html.escape(identified_name)}</b>!\n\n🛍️ Amazon product search is temporarily taking longer than expected. You can try searching for '{html.escape(identified_name)}' in a moment."
            reply = _append_signature(recovery_text)
            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=reply, parse_mode="HTML")

    except Exception as e:
        stop_progress.set()
        logger.error(f"[{chat_id}] Unexpected background image error: {e}", exc_info=True)
        reply = _append_signature("😅 Something went wrong while processing your image. Please try uploading it again!")
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=reply)
        except Exception:
            pass
    finally:
        stop_progress.set()
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Non-blocking Telegram photo handler. Immediately acknowledges receipt and queues background worker."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id

    if update.message.photo:
        photo = update.message.photo[-1]
    elif update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith("image/"):
        photo = update.message.document
    else:
        return

    # Immediately acknowledge image receipt
    ack_text = _append_signature("😊 I've received your image!\n\n🔍 Analyzing it...")
    status_msg = await update.message.reply_text(ack_text)

    # Queue background task non-blockingly
    asyncio.create_task(_process_image_background(update, context, photo, chat_id, status_msg))


def main() -> None:
    logger.info("🚀 Starting Trevor — AI Shopping & Styling Assistant")
    logger.info(f"Using Ollama model: {config.OLLAMA_MODEL}")

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .read_timeout(60.0)
        .write_timeout(60.0)
        .connect_timeout(60.0)
        .get_updates_read_timeout(60.0)
        .build()
    )

    app.add_error_handler(global_error_handler)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("✅ Trevor is live! Polling for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
