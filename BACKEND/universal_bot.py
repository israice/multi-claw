import asyncio
import os
import sys

sys.path.insert(0, "/app")

from SETTINGS import PODS_CONFIG
from BACKEND.provider_factory import create_provider
from BACKEND.base_bot import BaseBot


def _token_env_name(pod_name: str) -> str:
    """mini-claw → TELEGRAM_TOKEN_MINI_CLAW"""
    return "TELEGRAM_TOKEN_" + pod_name.upper().replace("-", "_")


async def main():
    pod_name = os.environ["POD_NAME"]

    cfg = PODS_CONFIG.get(pod_name)
    if cfg is None:
        raise SystemExit(f"Pod {pod_name!r} not found in PODS_CONFIG")

    token = os.environ[_token_env_name(pod_name)]
    api_key = os.environ[cfg["api_key_env"]]

    ai = create_provider(
        provider_name=cfg["provider"],
        model=cfg["model"],
        api_key=api_key,
    )

    bot = BaseBot(token=token, pod_name=pod_name, ai=ai)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
