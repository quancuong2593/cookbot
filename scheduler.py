import asyncio, logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import notifier
import daily

TZ = ZoneInfo("Asia/Bangkok")
HOUR, MINUTE = 9, 0

def seconds_until_next_run() -> float:
    now = datetime.now(TZ)
    target = now.replace(hour=HOUR, minute=MINUTE, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()

async def loop() -> None:
    notifier.setup_logging()
    logging.info("Scheduler khoi dong")
    while True:
        wait = seconds_until_next_run()
        logging.info(f"Ngu {wait/3600:.1f} gio den lan chay tiep theo")
        await asyncio.sleep(wait)
        try:
            await daily.main()
        except Exception as e:
            logging.error(f"Daily that bai: {e}")
            await notifier.send_log(f"⚠️ Scheduler: daily thất bại — {e}")
        await asyncio.sleep(60)     # tránh chạy 2 lần trong cùng 1 phút

if __name__ == "__main__":
    asyncio.run(loop())
