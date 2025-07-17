"""
main.py
-------
Entry point для Render (и локального запуска).
Запускает long polling.
"""

import asyncio          # нам не надо напрямую, но полезно иметь под рукой для отладки
import os               # чтобы прочитать токен из переменных окружения
import logging          # простой лог — увидишь в логах Render

from telegram.error import TelegramError

from telegram_bot0 import build_application  # импорт фабрики Application

# Включаем базовый логгер (INFO достаточно; DEBUG очень шумно на Render)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_bot_token() -> str:
    """Берём токен из переменной окружения BOT_TOKEN.
    Ругаемся, если не найден.
    """
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN env var not set! Add it in Render -> Environment.")
    return token


async def run() -> None:
    """Асинхронный запуск бота."""
    token = get_bot_token()
    app = build_application(token)

    # Стартуем polling и ждём завершения (Ctrl+C / SIGTERM / рестарт Render)
    # .run_polling() *сама* создаёт и управляет asyncio loop'ом, НО
    # удобнее вызывать app.initialize()/app.start()/app.updater.start_polling() вручную?
    # Проще: используем встроенный shortcut app.run_polling()
    await app.initialize()
    await app.start()
    logger.info("Bot started. Waiting for updates...")
    await app.updater.start_polling()

    # Гарантируем, что приложение живёт пока не будет отменено
    await asyncio.Event().wait()


def main() -> None:
    """Синхронная оболочка: запускает run() в event loop."""
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by signal.")
    except TelegramError as e:
        logger.exception("Telegram API error: %s", e)
    except Exception:  # pylint: disable=broad-except
        logger.exception("Unhandled error in bot")
        raise


if __name__ == "__main__":
    main()
