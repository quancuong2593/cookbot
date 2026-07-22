import asyncio
import logging

import core.daily as daily

# daily.main() co goi notifier.setup_logging() ben trong — an toan tren Lambda
# vi setup_logging() da kiem tra AWS_LAMBDA_FUNCTION_NAME va khong tao FileHandler.
logging.getLogger().setLevel(logging.INFO)


def lambda_handler(event, context):
    slot = (event or {}).get("slot", "morning")
    asyncio.run(daily.main(slot))
    return {"statusCode": 200, "body": "ok"}
