import asyncio, logging
from datetime import datetime
from zoneinfo import ZoneInfo

import config, notifier, weather, brain

TZ = ZoneInfo("Asia/Bangkok")

WEEKDAY_VI = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm",
              "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]

# T6 toi (day_index=4) chuan bi sang T7; T7 toi (day_index=5) chuan bi sang CN
BREAKFAST_LABEL = {4: "bữa sáng thứ Bảy", 5: "bữa sáng Chủ nhật"}

def meals_for(day_index: int, slot: str) -> list[str]:
    """0=Thứ Hai ... 5=Thứ Bảy, 6=Chủ Nhật. slot: "morning" (9h) hoặc "evening" (21h)."""
    if slot == "evening":
        label = BREAKFAST_LABEL.get(day_index)
        return [label] if label else []
    if day_index >= 5:                       # cuối tuần
        return ["bữa trưa", "bữa tối"]
    return ["bữa tối"]

async def main(slot: str = "morning") -> None:
    notifier.setup_logging()
    now = datetime.now(TZ)
    day_index = now.weekday()
    meals = meals_for(day_index, slot)

    logging.info(f"Chay daily slot={slot} cho {WEEKDAY_VI[day_index]}, bua: {meals}")

    if not meals:
        logging.info("Khong co bua nao ung voi slot nay, bo qua.")
        return

    try:
        w = await (weather.get_tomorrow() if slot == "evening" else weather.get_today())
    except Exception as e:
        logging.error(f"Loi lay thoi tiet: {e}")
        await notifier.send_log(f"⚠️ Daily lỗi lấy thời tiết: {e}")
        return

    try:
        when = "sáng mai" if slot == "evening" else "hôm nay"
        menu = await brain.daily_menu(w, meals, when)
    except Exception as e:
        logging.error(f"Loi goi Claude: {e}")
        await notifier.send_log(f"⚠️ Daily lỗi gọi Claude: {e}")
        return

    if slot == "evening":
        tomorrow_index = (day_index + 1) % 7
        header = (f"🌙 Chào buổi tối {config.CHEF_NAME}! Đây là gợi ý CHO SÁNG MAI "
                  f"({WEEKDAY_VI[tomorrow_index]}), không phải cho tối nay đâu nhé.\n"
                  f"Thời tiết ngày mai: {w}\n\n")
    else:
        header = (f"☀️ Chào buổi sáng {config.CHEF_NAME}!\n{WEEKDAY_VI[day_index]}, "
                  f"ngày {now.strftime('%d/%m')}\n"
                  f"Thời tiết: {w}\n\n")
    message = header + menu

    sent, failed = 0, 0
    for cid in config.DAILY_CHAT_IDS:
        try:
            await notifier.send(cid, message)
            sent += 1
        except Exception as e:
            failed += 1
            logging.error(f"Loi gui cho {cid}: {e}")

    logging.info(f"Xong. Gui thanh cong {sent}, that bai {failed}")
    await notifier.send_log(f"✅ Daily đã gửi {sent} người "
                            f"({failed} lỗi)\n\n{message}")

if __name__ == "__main__":
    asyncio.run(main())
