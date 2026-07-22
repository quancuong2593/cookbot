import asyncio
import logging

import core.daily as daily

# daily.main() co goi notifier.setup_logging() ben trong — an toan tren Lambda
# vi setup_logging() da kiem tra AWS_LAMBDA_FUNCTION_NAME va khong tao FileHandler.
logging.getLogger().setLevel(logging.INFO)


def lambda_handler(event, context):
    asyncio.run(daily.main())
    return {"statusCode": 200, "body": "ok"}
