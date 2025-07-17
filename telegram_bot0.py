"""
telegram_bot0.py
----------------
Минимальный эхо-бот на python-telegram-bot v20.6.
Вызывается из main.py через build_application().
"""

from __future__ import annotations  # для аннотаций строками в Py<3.11 (безопасно)

# === Импорты из PTB ===
from telegram import Update  # объект, содержащий входящее событие (сообщение, команду и т.п.)
from telegram.ext import (
    Application,                # главный объект бота (event loop + диспетчер)
    ApplicationBuilder,         # строитель Application: задаём токен и опции
    ContextTypes,               # типы контекстов; context содержит user_data/chat_data и др.
    CommandHandler,             # обработчик /command
    MessageHandler,             # обработчик произвольных сообщений (текст и пр.)
    filters,                    # предопределённые фильтры для MessageHandler
)

# --- Handler: /start ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отвечаем на /start: просим прислать текст."""
    # update.message: объект Message, пришедший от пользователя (в чате с ботом)
    # reply_text(...) отправляет ответ в тот же чат
    await update.message.reply_text("👋 Hi! Send me your start point Postal Code")

# --- Handler: текстовые сообщения ---
async def echo_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сохраняем текст в user_data и отправляем эхо."""
    # Забираем текст
    text_in = (update.message.text or "").strip()

    # Сохраняем в user_data (словарь, поддерживаемый PTB; живёт в памяти процесса)
    context.user_data["last_message"] = text_in

    # Отправляем подтверждение + эхо
    await update.message.reply_text(f"{text_in}")

# --- Фабрика для Application ---
def build_application(token: str) -> Application:
    """Создаёт и настраивает Application; возвращает готовый объект.

    Не запускает polling — это делает main.py.
    """
    app = (
        ApplicationBuilder()
        .token(token)            # токен бота от @BotFather (подаём из переменной окружения)
        .build()
    )

    # Регистрируем handlers
    app.add_handler(CommandHandler("start", cmd_start))            # реагируем на /start
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_text))  # любой текст, кроме команд

    return app
