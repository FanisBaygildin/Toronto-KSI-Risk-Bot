from telegram import Update
def start(update, context):
    update.message.reply_text("📍 Send postal code of the start point")

def echo_pc(update, context):
    pc = update.message.text.strip().upper()
    update.message.reply_text(f"✅ You sent: {pc}")
