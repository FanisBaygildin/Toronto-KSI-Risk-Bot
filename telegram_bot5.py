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
from weather_api import build_weather_row          # ← новый импорт
import asyncio                                     # для to_thread

# --- Состояния ---------------------------------------------------------
START_PC, END_PC = range(2)

# --- /start ------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("👋 Hi! Send me your start point Postal Code")
    return START_PC

# --- получаем start PC -------------------------------------------------
async def receive_start_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    start_pc = (update.message.text or "").strip().upper()
    context.user_data["start_pc"] = start_pc
    await update.message.reply_text("✅ Saved! Now send me your destination point Postal Code")
    return END_PC

# --- получаем destination PC ------------------------------------------
async def receive_end_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dest_pc = (update.message.text or "").strip().upper()
    context.user_data["dest_pc"] = dest_pc
    await update.message.reply_text("⏳ Calculating routes, please wait…")

    # --- маршруты ---
    try:
        routes = await get_routes(context.user_data["start_pc"], dest_pc)
    except Exception as e:
        await update.message.reply_text(f"❌ Google Maps error: {e}")
        return ConversationHandler.END

    # --- погода ---
    try:
        weather = await asyncio.to_thread(build_weather_row)
    except Exception as e:
        await update.message.reply_text(f"❌ Weather API error: {e}")
        weather = None                # чтобы дальше не падать

    if not routes:
        await update.message.reply_text("❗ No route found")
        return ConversationHandler.END

    if weather is not None:
        weather_str = (
            f"Temperature {weather['temp_c']} °C, "
            f"Humidity {weather['humidity']} %, "
            f"Wind {weather['wind_kph']} kph, "
            f"Dewpoint_c {weather['dewpoint_c']} °C, "
            f"Visibility {weather['vis_km']} km, "
            f"Pressure {weather['pressure_mb']} mBar"
        )
        caption_lines = [f"Current Weather: {weather_str}"]
    else:
        caption_lines = ["Current Weather: unavailable"]
    
    caption_lines += [
        f"Route {i+1}: {r['distance_km']} km, {r['duration_text']}"
        for i, r in enumerate(routes)
    ]
    caption = "\n".join(caption_lines)

    # пытаемся получить статическую карту
    try:
        img_bytes = await static_map(
            context.user_data["start_pc"],
            dest_pc,
            [r["poly"] for r in routes],
        )
        await update.message.reply_photo(photo=img_bytes, caption=caption)
    except Exception as e:
        # если не вышло — хотя бы текст
        await update.message.reply_text(caption + f"\n(карту показать не удалось: {e})")

    return ConversationHandler.END

# --- эхо вне диалога ---------------------------------------------------
async def echo_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text((update.message.text or "").strip())

# --- фабрика приложения ------------------------------------------------
def build_application(token: str) -> Application:
    app = ApplicationBuilder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            START_PC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_start_pc)],
            END_PC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_end_pc)],
        },
        fallbacks=[],
    )
    app.add_handler(conv)
    return app
