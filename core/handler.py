import logging
from typing import Awaitable, Callable

import config, brain

NotifyAdmin = Callable[[str], Awaitable[None]]


async def handle_message(chat_id: str, text: str, notify_admin: NotifyAdmin) -> str | None:
    """Gate whitelist + hoi Claude. Tra ve None neu chat_id bi chan (im lang)."""
    if chat_id not in config.ALLOWED:
        logging.warning(f"Chan nguoi la: {chat_id}")
        await notify_admin(f"⛔ Người lạ nhắn — chat_id: {chat_id}")
        return None

    logging.info(f"Tin tu {chat_id}: {text[:40]}")
    return await brain.ask(text)
