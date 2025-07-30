# telegram_bot0.py
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    Application,
)

from google_maps_route import get_routes, static_map
from weather_api import build_weather_row, weather_df_for_route
import joblib, numpy as np
from pathlib import Path
import asyncio                                     # для to_thread

import os
from telegram.ext import PicklePersistence

import logging

# --- Состояния ---------------------------------------------------------
AUTH, START_PC, END_PC = range(3)  # +AUTH
MAX_AUTH_TRIES = 3

# --- /start ------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Уже авторизован? Сразу к стартовому индексу/PC.
    if context.user_data.get("auth"):
        await update.message.reply_text("📍 Send start postal code")
        return START_PC

    # Первый вход — спросим пароль
    context.user_data.setdefault("auth_tries", 0)
    await update.message.reply_text("🔒 Enter access password")
    return AUTH


async def authorize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pwd = update.message.text.strip()
    real = os.getenv("BOT_PASS", "")

    if pwd == real and real:
        context.user_data["auth"] = True
        context.user_data.pop("auth_tries", None)
        await update.message.reply_text("✅ Access granted.\n📍 Please send your start point Postal Code (for example M6S 5A2)")
        return START_PC

    tries = context.user_data.get("auth_tries", 0) + 1
    context.user_data["auth_tries"] = tries

    if tries >= MAX_AUTH_TRIES:
        await update.message.reply_text("⛔ Wrong password. Try again later with /start")
        return ConversationHandler.END

    await update.message.reply_text(f"❌ Wrong password ({tries}/{MAX_AUTH_TRIES}). Try again:")
    return AUTH


# --- получаем start PC -------------------------------------------------
async def receive_start_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    start_pc = (update.message.text or "").strip().upper()
    context.user_data["start_pc"] = start_pc
    await update.message.reply_text("✅ Saved! Now please send your destination point Postal Code (for example M4R 1R3)")
    return END_PC

# --- получаем destination PC ------------------------------------------
# --- получаем destination PC ------------------------------------------
async def receive_end_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dest_pc = (update.message.text or "").strip().upper()
    context.user_data["dest_pc"] = dest_pc
    await update.message.reply_text("⏳ Calculating routes, please wait…")

    # --- маршруты ---
    try:
        routes = await get_routes(context.user_data["start_pc"], dest_pc)
    except Exception as e:
        await update.message.reply_text(f"❌ Google Maps error: {e}")
        return ConversationHandler.END

    if not routes:
        await update.message.reply_text("❗ No route found")
        return ConversationHandler.END

    # --- погода (агрегированный «сейчас») + DataFrame-ы для каждого маршрута ---
    weather = None
    try:
        # агрегированная погода для хедера (если твоя build_weather_row это умеет)
        weather = await asyncio.to_thread(build_weather_row)
    except Exception as e:
        logging.warning("build_weather_row failed: %s", e)

    # Для каждого маршрута пытаемся собрать фичи (DataFrame).
    # Даже если одна из сборок упадёт — остальные маршруты не теряем.
    dfs = []
    for idx, r in enumerate(routes, start=1):
        try:
            df = await asyncio.to_thread(weather_df_for_route, r["geohash5"])
            dfs.append(df)
        except Exception as e:
            logging.warning("weather_df_for_route failed for route %d: %s", idx, e)
            dfs.append(None)  # маркер «не получилось собрать фичи» для этого маршрута

    # ------ KSI-модель ----------------------------------------------
    try:
        model_path = Path(__file__).resolve().parent / "model" / "model.pkl"
        model = joblib.load(model_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Model load error: {e}")
        return ConversationHandler.END

    # Считаем риск по каждому маршруту отдельно. Если для маршрута df=None/пустой — ставим score=None.
    pairs = []  # список (route_dict, score_or_None)
    for idx, (r, df) in enumerate(zip(routes, dfs), start=1):
        score = None
        try:
            if df is not None and getattr(df, "empty", False) is False:
                score = float(model.predict_sum(df))
            else:
                logging.warning("Route %d: empty/None DF -> score=None", idx)
        except Exception as e:
            logging.warning("predict_sum failed for route %d: %s", idx, e)
        pairs.append((r, score))

    logging.info("routes=%d; dfs=%d; scored=%d",
                 len(routes), len(dfs), sum(1 for _, s in pairs if s is not None))

    # ------ Формируем ответ -----------------------------------------
    if weather is not None:
        weather_str = (
            f"Temperature {weather.get('temp_c','?')} °C, "
            f"Humidity {weather.get('humidity','?')} %, "
            f"Wind {weather.get('wind_kph','?')} kph, "
            f"Dewpoint_c {weather.get('dewpoint_c','?')} °C, "
            f"Visibility {weather.get('vis_km','?')} km, "
            f"Pressure {weather.get('pressure_mb','?')} mBar"
        )
        caption_lines = [f"Current Weather: {weather_str}"]
    else:
        caption_lines = ["Current Weather: unavailable"]

    # Безопасно выводим до N маршрутов (все, что есть). Без индексации по i.
    for idx, (r, score) in enumerate(pairs, start=1):
        prob_line = f"KSI probability {score*100:.3f} %" if isinstance(score, (int, float)) else "KSI probability n/a"
        caption_lines += [
            f"Route {idx}: {r.get('distance_km','?')} km, {r.get('duration_text','?')}, {prob_line}"
        ]

    caption = "\n".join(caption_lines)

    # Пытаемся получить статическую карту (даже если для части маршрутов score=None)
    try:
        img_bytes = await static_map(
            context.user_data["start_pc"],
            dest_pc,
            [r["poly"] for r, _ in pairs if "poly" in r],
        )
        await update.message.reply_photo(photo=img_bytes, caption=caption)
    except Exception as e:
        await update.message.reply_text(caption + f"\n(карту показать не удалось: {e})")

    return ConversationHandler.END


# --- эхо вне диалога ---------------------------------------------------
async def echo_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text((update.message.text or "").strip())

# --- фабрика приложения ------------------------------------------------
def build_application(token: str) -> Application:
    app = ApplicationBuilder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states = {
            AUTH:     [MessageHandler(filters.TEXT & ~filters.COMMAND, authorize)],  # +AUTH
            START_PC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_start_pc)],
            END_PC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_end_pc)],
        }
,
        fallbacks=[],
    )
    app.add_handler(conv)
    return app
