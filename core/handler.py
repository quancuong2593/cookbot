import logging

import config, notifier, brain


async def handle_message(chat_id: str, text: str) -> str | None:
    """Gate whitelist + hoi Claude. Tra ve None neu chat_id bi chan (im lang)."""
    if chat_id not in config.ALLOWED:
        logging.warning(f"Chan nguoi la: {chat_id}")
        await notifier.send_log(f"⛔ Người lạ nhắn — chat_id: {chat_id}")
        return None

    logging.info(f"Tin tu {chat_id}: {text[:40]}")
    return await brain.ask(text)
