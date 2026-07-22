import logging
from typing import Awaitable, Callable

import config, brain, weather
import core.mealtime as mealtime

NotifyAdmin = Callable[[str], Awaitable[None]]


async def handle_message(chat_id: str, text: str, notify_admin: NotifyAdmin) -> str | None:
    """Gate whitelist + hoi Claude. Tra ve None neu chat_id bi chan (im lang)."""
    if chat_id not in config.ALLOWED:
        logging.warning(f"Chan nguoi la: {chat_id}")
        await notify_admin(f"⛔ Người lạ nhắn — chat_id: {chat_id}")
        return None

    logging.info(f"Tin tu {chat_id}: {text[:40]}")

    meals = mealtime.current_meals_now()
    try:
        today_weather = await weather.get_today()
    except Exception as e:
        # Khong de loi thoi tiet lam im lang bot — tra loi tiep, chi thieu ngu canh.
        logging.error(f"Loi lay thoi tiet cho chat: {e}")
        today_weather = None

    return await brain.ask(text, today_weather, meals)
