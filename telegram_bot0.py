# -*- coding: utf-8 -*-

# telegram_bot0.py

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

START_PC = 0  # состояние ожидания postal code

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📍 Send postal code of the start point")
    return START_PC

async def receive_start_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pc = update.message.text.strip().upper()
    print("Start PC:", pc)  # лог в консоль
    await update.message.reply_text(f"✅ Got it: {pc}")
    return ConversationHandler.END
