# -*- coding: utf-8 -*-
"""
Telegram bot (PTB 20.6): KSI risk on a route
"""

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from google_maps_route import get_routes        # ваша утилита
from weather_api import build_weather_row       # ваша утилита
from route_risk import predict_risk             # ваша модель

# ── Conversation states
ASK_START_PC, ASK_END_PC, ASK_PERIOD = range(3)


# ── Handlers -----------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/start — greet user and ask for the start postal code"""
    await update.message.reply_text("⏳ Please wait… bot is waking up 💤")
    await update.message.reply_text("📍 Send the *start* postal code")
    return ASK_START_PC


async def receive_start_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["start_pc"] = update.message.text.strip()
    await update.message.reply_text("📍 Send the *destination* postal code")
    return ASK_END_PC


async def receive_end_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["end_pc"] = update.message.text.strip()

    keyboard = [["Следующие 3 ч", "Следующие 24 ч"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("⏰ На какой период рассчитать риск?", reply_markup=reply_markup)
    return ASK_PERIOD


async def receive_period(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    period_label = update.message.text.strip()
    start_pc = context.user_data["start_pc"]
    end_pc = context.user_data["end_pc"]

    # 1) Google Maps route — если это блокирующая функция, заверните в to_thread
    route = await context.application.run_in_executor(None, get_routes, start_pc, end_pc)

    # 2) Погода
    weather_row = build_weather_row()           # если блокирует → run_in_executor

    # 3) ML-модель
    risk, city_avg = predict_risk(route, weather_row, period_label)

    diff = int(round((risk - city_avg) / city_avg * 100)) if city_avg else 0
    if diff > 0:
        comparison = f"higher than city average by {diff}%"
    elif diff < 0:
        comparison = f"lower than city average by {abs(diff)}%"
    else:
        comparison = "equal to the city average"

    await update.message.reply_text(f"🚧 KSI Risk: {risk:.2f}‰ ({comparison})")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 Operation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END


# ── Entry point --------------------------------------------------------
def start_bot() -> None:
    import os

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable not set")

    application = ApplicationBuilder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            ASK_START_PC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_start_pc)],
            ASK_END_PC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_end_pc)],
            ASK_PERIOD:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_period)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv)
    print("Bot is running…")
    application.run_polling()


if __name__ == "__main__":
    start_bot()
