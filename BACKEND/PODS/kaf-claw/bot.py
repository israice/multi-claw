import asyncio
import os
import sys

sys.path.insert(0, "/app")

from config import POD_NAME, AI_MODEL, API_KEY_ENV, TELEGRAM_TOKEN_ENV
from BACKEND.ai_providers.xai_provider import XAIProvider
from BACKEND.base_bot import BaseBot


async def main():
    token = os.environ[TELEGRAM_TOKEN_ENV]
    api_key = os.environ[API_KEY_ENV]
    ai = XAIProvider(model=AI_MODEL, api_key=api_key)
    bot = BaseBot(token=token, pod_name=POD_NAME, ai=ai)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
