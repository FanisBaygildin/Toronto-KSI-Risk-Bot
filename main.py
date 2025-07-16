# -*- coding: utf-8 -*-

# main.py
from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler
from telegram_bot0 import start, START_PC  # импортируешь свою функцию и состояние

app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={START_PC: []},  # пока можно оставить пустым
    fallbacks=[],
)

app.add_handler(conv_handler)

app.run_polling()
