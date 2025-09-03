# main.py
import os
import logging

from telegram.error import TelegramError
from telegram_bot import build_application

# --- Логирование (настраиваем один раз) -------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)     # скрываем запросы с токеном
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
# ----------------------------------------------------------------------

def main() -> None:
    token = os.getenv("BOT_TOKEN")
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
