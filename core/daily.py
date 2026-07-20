import asyncio, logging
from datetime import datetime
from zoneinfo import ZoneInfo

import config, notifier, weather, brain

TZ = ZoneInfo("Asia/Bangkok")

WEEKDAY_VI = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm",
              "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]

def meals_for(day_index: int) -> list[str]:
    """0=Thứ Hai ... 5=Thứ Bảy, 6=Chủ Nhật."""
    if day_index >= 5:                       # cuối tuần
        return ["bữa trưa", "bữa tối"]
    return ["bữa tối"]

async def main() -> None:
    notifier.setup_logging()
    now = datetime.now(TZ)
    day_index = now.weekday()
    meals = meals_for(day_index)

    logging.info(f"Chay daily cho {WEEKDAY_VI[day_index]}, bua: {meals}")

    try:
        w = await weather.get_today()
    except Exception as e:
        logging.error(f"Loi lay thoi tiet: {e}")
        await notifier.send_log(f"⚠️ Daily lỗi lấy thời tiết: {e}")
        return

    try:
        menu = await brain.daily_menu(w, meals)
    except Exception as e:
        logging.error(f"Loi goi Claude: {e}")
        await notifier.send_log(f"⚠️ Daily lỗi gọi Claude: {e}")
        return

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
