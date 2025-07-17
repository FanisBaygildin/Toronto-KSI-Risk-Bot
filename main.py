# main.py (коротко и надёжно)

# Заглушаем httpx и httpcore, чтобы не печатали запросы с токеном
import logging
logging.basicConfig(level=logging.INFO)  # или WARNING — как хочешь
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

import os
import logging
from telegram.error import TelegramError
from telegram_bot0 import build_application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN env var not set!")

    app = build_application(token)
    try:
        app.run_polling(drop_pending_updates=True)
    except TelegramError:
        logger.exception("Telegram API error")
        raise

if __name__ == "__main__":
    main()
