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

    # Отвечаем на /start: просим прислать текст
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👋 Hi! Send me your start point Postal Code")     # update.message: объект Message, пришедший от пользователя (в чате с ботом), reply_text(...) отправляет ответ в тот же чат

# --- Handler: Сохраняет ответ юзера в user_data и отправляет эхо
async def echo_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text_in = (update.message.text or "").strip()        # Забираем текст, or "" на случай, если пользователь прислал, к примеру, фото или стикер
    context.user_data["last_message"] = text_in    # Сохраняем в user_data (словарь, поддерживаемый PTB; живёт в памяти процесса)
    await update.message.reply_text(f"{text_in}")    # Отправляем эхо

# --- Фабрика для Application --- Создаёт и настраивает Application; возвращает готовый объект. Не запускает polling — это делает main.py
def build_application(token: str) -> Application:
    app = (
        ApplicationBuilder()
        .token(token)            # токен бота от @BotFather (подаём из переменной окружения)
        .build()
    )

    # Регистрируем handlers
    app.add_handler(CommandHandler("start", cmd_start))            # реагируем на /start
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_text))  # любой текст, кроме команд

    return app
