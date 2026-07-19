import os
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
LOG_BOT_TOKEN  = os.environ["LOG_BOT_TOKEN"]
ANTHROPIC_KEY  = os.environ["ANTHROPIC_API_KEY"]
CHEF_NAME = os.getenv("CHEF_NAME", "chị Như")

ALLOWED       = {x.strip() for x in os.environ["ALLOWED_CHAT_IDS"].split(",")}
ADMIN_CHAT_ID = os.environ["ADMIN_CHAT_ID"].strip()
MIRROR_ALL    = os.getenv("MIRROR_ALL") == "1"

# Người nhận tin nhắn 9h sáng (mặc định = cả whitelist)
DAILY_CHAT_IDS = {x.strip() for x in
                  os.getenv("DAILY_CHAT_IDS", ",".join(ALLOWED)).split(",")}

MODEL = os.getenv("MODEL", "claude-haiku-4-5")

# Toạ độ Hà Nội
LAT = float(os.getenv("LAT", "21.03"))
LON = float(os.getenv("LON", "105.85"))
