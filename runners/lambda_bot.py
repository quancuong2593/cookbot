import asyncio
import json
import logging

import config, notifier
from core.handler import handle_message

# Khong goi notifier.setup_logging(): FileHandler ghi "cookbot.log" se
# loi tren filesystem chi-doc cua Lambda. CloudWatch da tu bat stdout/stderr.
logging.getLogger().setLevel(logging.INFO)

SECRET_HEADER = "x-telegram-bot-api-secret-token"


def _get_header(headers: dict, name: str) -> str | None:
    name = name.lower()
    for key, value in (headers or {}).items():
        if key.lower() == name:
            return value
    return None


def _extract_text_message(update: dict) -> tuple[str, str, str] | None:
    """Tra ve (chat_id, text, who) neu la tin nhan van ban, None neu khong phai."""
    message = update.get("message")
    if not message:
        return None

    text = message.get("text")
    chat = message.get("chat")
    if not text or not chat or "id" not in chat:
        return None

    who = message.get("from", {}).get("first_name", "")
    return str(chat["id"]), text, who


async def _process(event: dict) -> dict:
    headers = event.get("headers") or {}
    if _get_header(headers, SECRET_HEADER) != config.WEBHOOK_SECRET:
        logging.warning("Webhook secret sai")
        return {"statusCode": 403, "body": "forbidden"}

    try:
        update = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        logging.error("Webhook body khong phai JSON hop le")
        return {"statusCode": 200, "body": "ignored"}

    parsed = _extract_text_message(update)
    if parsed is None:
        return {"statusCode": 200, "body": "ignored"}

    cid, text, who = parsed

    answer = await handle_message(cid, text, notify_admin=notifier.send_log)
    if answer is None:
        return {"statusCode": 200, "body": "ok"}

    await notifier.send(cid, answer)

    if config.MIRROR_ALL or cid != config.ADMIN_CHAT_ID:
        await notifier.send_log(
            f"👀 {who} hỏi:\n{text}\n\n🤖 Bot đáp:\n{answer}")

    return {"statusCode": 200, "body": "ok"}


def lambda_handler(event, context):
    return asyncio.run(_process(event))
