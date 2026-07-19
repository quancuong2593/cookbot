import os, logging
from dotenv import load_dotenv
load_dotenv()

import anthropic
from telegram import Update, Bot
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          ContextTypes, filters)

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s",
                    level=logging.INFO)

ALLOWED = {x.strip() for x in os.environ["ALLOWED_CHAT_IDS"].split(",")}
ADMIN_CHAT_ID = os.environ["ADMIN_CHAT_ID"]
MIRROR_ALL = os.getenv("MIRROR_ALL") == "1"
client = anthropic.AsyncAnthropic()
log_bot = Bot(os.environ["LOG_BOT_TOKEN"])

SYSTEM = ("Bạn là trợ lý nấu ăn của một gia đình ở Hà Nội, bạn cũng là chuyên gia Đông y. "
          "Tư vấn món healthy, đơn giản, phục hồi tì vị. Trả lời ngắn gọn, ấm áp.")

async def send_log(text: str) -> None:
    try:
        await log_bot.send_message(ADMIN_CHAT_ID, text)
    except Exception as e:
        logging.error(f"Loi gui log: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    await update.message.reply_text(f"Chào cả nhà 🍲 chat_id của bạn là: {cid}")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    if cid not in ALLOWED:                       # GATE — chặn người lạ
        logging.warning(f"Chan nguoi la: {cid}")
        await send_log(f"⛔ Người lạ nhắn — chat_id: {cid}")
        return

    logging.info(f"Tin tu {cid}: {update.message.text[:40]}")
    reply = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        system=SYSTEM,
        messages=[{"role": "user", "content": update.message.text}],
    )
    answer = reply.content[0].text
    await update.message.reply_text(answer)

    if MIRROR_ALL or cid != ADMIN_CHAT_ID:
        who = update.effective_user.first_name
        await send_log(f"👀 {who} hỏi:\n{update.message.text}\n\n🤖 Bot đáp:\n{answer}")

def main():
    app = Application.builder().token(os.environ["TELEGRAM_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    logging.info("Bot dang polling...")
    app.run_polling()

if __name__ == "__main__":
    main()