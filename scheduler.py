# DEPRECATED: dùng runners/scheduler.py
import asyncio
from runners.scheduler import loop

if __name__ == "__main__":
    asyncio.run(loop())
