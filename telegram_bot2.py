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

# --- Состояния ---------------------------------------------------------
START_PC, END_PC = 0, 1        # 0 и 1: удобнее читать, чем magic‑числа

# --- 1. /start: просим отправить стартовый индекс ----------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("👋 Hi! Send me your start point Postal Code")
    return START_PC                # переключаемся в состояние START_PC

# --- 2. Пришёл start PC -----------------------------------------------
async def receive_start_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    start_pc = (update.message.text or "").strip().upper()
    context.user_data["start_pc"] = start_pc
    await update.message.reply_text("✅ Saved! Now send me your destination point Postal Code")
    return END_PC                  # ждём второй код

# --- 3. Пришёл destination PC -----------------------------------------
async def receive_end_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dest_pc = (update.message.text or "").strip().upper()
    context.user_data["dest_pc"] = dest_pc
    await update.message.reply_text(
        f"✅ Saved!\n🗺️ Route: {context.user_data['start_pc']} → {dest_pc}"
    )
    return ConversationHandler.END  # диалог завершён

# --- (необязательно) 4. Эхо для любых других текстов ------------------
async def echo_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text_in = (update.message.text or "").strip()
    await update.message.reply_text(text_in)

# --- 5. Фабрика приложения -------------------------------------------
def build_application(token: str) -> Application:
    app = ApplicationBuilder().token(token).build()

    # ConversationHandler для двух шагов
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            START_PC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_start_pc)],
            END_PC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_end_pc)],
        },
        fallbacks=[],               # можно добавить /cancel при желании
    )
    app.add_handler(conv)

    # эхо — после conv, чтобы не перехватывать его сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_text))

    return app
