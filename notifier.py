import logging
from telegram import Bot
from telegram.constants import ParseMode
import config

main_bot = Bot(config.TELEGRAM_TOKEN)
log_bot  = Bot(config.LOG_BOT_TOKEN)

async def send(chat_id: str, text: str) -> None:
    """Gửi tin cho người dùng."""
    await main_bot.send_message(chat_id, text)

async def send_log(text: str) -> None:
    """Gửi log cho admin. Không bao giờ được làm chết chương trình chính."""
    try:
        await log_bot.send_message(config.ADMIN_CHAT_ID, text)
    except Exception as e:
        logging.error(f"Loi gui log: {e}")

def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        level=logging.INFO,
        handlers=[logging.FileHandler("cookbot.log", encoding="utf-8"),
                  logging.StreamHandler()])
