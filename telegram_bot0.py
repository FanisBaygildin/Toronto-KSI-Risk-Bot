from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters
from telegram_bot0 import start, receive_start_pc, START_PC
import os

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={START_PC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_start_pc)]},
    fallbacks=[],
)

app.add_handler(conv_handler)
app.run_polling()
