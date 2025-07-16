from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

BOT_TOKEN = "вставь_сюда_токен_или_используй_env"

def start(update, context):
    update.message.reply_text("📍 Send postal code of the start point")

def echo_pc(update, context):
    pc = update.message.text.strip().upper()
    update.message.reply_text(f"✅ You sent: {pc}")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo_pc))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
