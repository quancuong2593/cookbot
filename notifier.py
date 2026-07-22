import logging
import os
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
    """StreamHandler luon co (Lambda tu gom stdout vao CloudWatch). FileHandler
    chi them khi KHONG chay tren Lambda — filesystem cua Lambda chi-doc tru
    /tmp (ma /tmp cung khong persistent nen ghi vao do cung vo nghia)."""
    handlers = [logging.StreamHandler()]
    if "AWS_LAMBDA_FUNCTION_NAME" not in os.environ:
        handlers.append(logging.FileHandler("cookbot.log", encoding="utf-8"))

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        level=logging.INFO,
        handlers=handlers,
        # Lambda runtime da tu cau hinh logging san; basicConfig() se bi
        # bo qua lang le neu thieu force=True (chi ap dung khi chua co handler).
        force=True)
