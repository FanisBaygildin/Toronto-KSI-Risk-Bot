# main.py
import os    # to get the bot token
import logging    # to output logs

from telegram.error import TelegramError    # for Telegram errors
from telegram_bot import build_application    # my telegram_bot.py code

'''
Logs output format:
asctime - event time
levelname - level (INFO, ERROR, ...)
name - logger name
message - the message itself
'''
logging.basicConfig(
    level=logging.INFO,    # outputs everything from INFO and higher (INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"    
)

# remove
# logging.getLogger("httpx").setLevel(logging.WARNING)
# logging.getLogger("httpcore").setLevel(logging.WARNING)
# logger = logging.getLogger(__name__)


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("404: the Bot Token Not Found!")

    # transmitting the token to build_application func from telegram_bot.py
    app = build_application(token)
    try:
        app.run_polling(drop_pending_updates=True)    # polling the bot about new messages ignoring the old messages on Start
    except TelegramError as e:
        print("Telegram API error:", e)    # for errors in Telegram API
        # remove
    # except TelegramError:
    #     logger.exception("Telegram API error")
        raise

if __name__ == "__main__":
    main()
