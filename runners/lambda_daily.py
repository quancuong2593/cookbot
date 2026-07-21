import asyncio
import logging

import core.daily as daily

# Xem ghi chu trong lambda_bot.py: khong dung notifier.setup_logging() o day.
logging.getLogger().setLevel(logging.INFO)


def lambda_handler(event, context):
    asyncio.run(daily.main())
    return {"statusCode": 200, "body": "ok"}
