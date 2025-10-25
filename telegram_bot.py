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
import asyncio
from telegram.ext import PicklePersistence
import logging
# import os



# --- states ---------------------------------------------------------
AUTH, START_PC, END_PC = range(3)    # current dialog state
MAX_AUTH_TRIES = 5



# --- /start ---------------------------------------------------------
'''
Asynchronous handler function 'start', which Telegram will call when the user sends /start
It takes two parameters:
    update: contains information about the incoming message (who sent it, text, etc.)
    context: stores per-user data and helper methods (like context.user_data, context.bot, etc.)
Returns an integer representing the next conversation state (used by ConversationHandler).
'''
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # If already authorized
    if context.user_data.get("auth"):    # if the key "auth" exists for the user and is True
        await update.message.reply_text("📍 Please send the start point postal code (E.g. M6S5A2)")
        return START_PC    # this tells the ConversationHandler to move to the 'start postal code' part

    # Authorization
    context.user_data.setdefault("auth_tries", 0)
    await update.message.reply_text("🔒 Enter access password")
    return AUTH


async def authorize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pwd = update.message.text.strip()
    real = os.getenv("BOT_PASS", "")

    if pwd == real and real:
        context.user_data["auth"] = True
        context.user_data.pop("auth_tries", None)
        await update.message.reply_text("📍 Please send the start point postal code (E.g. M6S5A2)")
        return START_PC

    tries = context.user_data.get("auth_tries", 0) + 1
    context.user_data["auth_tries"] = tries

    if tries >= MAX_AUTH_TRIES:
        await update.message.reply_text("⛔ Wrong password! You are locked until the next "cycle"! ;)")    # the user will be locked until Render gets restart
        return ConversationHandler.END

    await update.message.reply_text(f"❌ Wrong password ({tries}/{MAX_AUTH_TRIES}). Try again:")
    return AUTH


# --- Getting Start PC -------------------------------------------------
async def receive_start_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    start_pc = (update.message.text or "").strip().upper()
    context.user_data["start_pc"] = start_pc
    await update.message.reply_text("📍 Now send the destination point postal code (E.g. M4R1R3)")
    return END_PC

# --- Getting Destination PC ------------------------------------------
async def receive_end_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dest_pc = (update.message.text or "").strip().upper()
    context.user_data["dest_pc"] = dest_pc
    await update.message.reply_text("⏳ Calculating routes…")

    # --- routes ---
    try:
        routes = await get_routes(context.user_data["start_pc"], dest_pc)
    except Exception as e:
        await update.message.reply_text(f"❌ Google Maps error: {e}")
        return ConversationHandler.END

    if not routes:
        await update.message.reply_text("❗ No route found")
        return ConversationHandler.END

    # --- Current Weather + DataFrames for each route ---
    weather = None
    try:
        # агрегированная погода для хедера (если твоя build_weather_row это умеет) ????????
        weather = await asyncio.to_thread(build_weather_row)
    except Exception as e:
        logging.warning("build_weather_row failed: %s", e)

    # Getting features and built a DF for each route
    # Even if one of the DFs crashes, we don't lose the rest
    dfs = []
    for idx, r in enumerate(routes, start=1):
        try:
            df = await asyncio.to_thread(weather_df_for_route, r["geohash5"])
            dfs.append(df)
        except Exception as e:
            logging.warning("weather_df_for_route failed for route %d: %s", idx, e)
            dfs.append(None)    # "failed to collect features" marker for this route

    # ------ KSI-model ----------------------------------------------
    try:
        model_path = Path(__file__).resolve().parent / "model" / "model.pkl"
        model = joblib.load(model_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Model load error: {e}")
        return ConversationHandler.END

    # Calculating risk for each route. If df=None/empty for the route, set score=None.
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

    # ------ Making the return -----------------------------------------
    if weather is not None:
        weather_str = (
            f"Temperature {weather.get('temp_c','?')} °C,\n"
            f"Humidity {weather.get('humidity','?')} %,\n"
            f"Wind {weather.get('wind_kph','?')} kph,\n"
            f"Dewpoint_c {weather.get('dewpoint_c','?')} °C,\n"
            f"Visibility {weather.get('vis_km','?')} km,\n"
            f"Pressure {weather.get('pressure_mb','?')} mBar\n"
        )
        caption_lines = [f"According to the routes and the current weather conditions:\n{weather_str}"]
    else:
        caption_lines = ["Current Weather: unavailable"]

    # output up to N routes
    for idx, (r, score) in enumerate(pairs, start=1):
        prob_line = f"KSI probability {score*100:.3f} %" if isinstance(score, (int, float)) else "KSI probability n/a"
        caption_lines += [
            f"Route {idx}: {r.get('distance_km','?')} km, {r.get('duration_text','?')}, {prob_line}"
        ]

    caption = "\n".join(caption_lines)

    # Trying to get a static map (even if score=None for some routes)
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


# --- эхо вне диалога --------------------------------------------------- ?????????????????
async def echo_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text((update.message.text or "").strip())

# --- фабрика приложения ------------------------------------------------ ?????????????????
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
