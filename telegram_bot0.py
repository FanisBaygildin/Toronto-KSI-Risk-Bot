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
from google_maps_route import get_routes

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

    try:
        routes = await get_routes(context.user_data["start_pc"], dest_pc)
    except Exception as e:
        await update.message.reply_text(f"❌ Google Maps error: {e}")
        return ConversationHandler.END

    if not routes:
        await update.message.reply_text("❗ No route found")
        return ConversationHandler.END

    lines = [
        f"Route {i+1}: {r['distance_km']} km, {r['duration_text']}"
        for i, r in enumerate(routes)
    ]
    await update.message.reply_text("\n".join(lines))
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
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_text))
    return app
