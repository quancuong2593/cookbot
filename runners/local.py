import logging
from telegram import Update
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          ContextTypes, filters)

import config, notifier
from core.handler import handle_message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    await update.message.reply_text(f"Chào cả nhà 🍲 chat_id của bạn là: {cid}")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    text = update.message.text
    if not text:
        return

    answer = await handle_message(cid, text)
    if answer is None:
        return

    await update.message.reply_text(answer)

    if config.MIRROR_ALL or cid != config.ADMIN_CHAT_ID:
        who = update.effective_user.first_name
        await notifier.send_log(
            f"👀 {who} hỏi:\n{text}\n\n🤖 Bot đáp:\n{answer}")

def main():
    notifier.setup_logging()
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    logging.info("Bot dang polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
