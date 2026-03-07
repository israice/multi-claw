import asyncio
import json
import os

import aiohttp

from SETTINGS import PODS_CONFIG, PODS_REGISTRY

# Provider display names
_PROVIDER_DISPLAY = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "mistral": "Mistral",
    "deepseek": "DeepSeek",
    "groq": "Groq",
    "together": "Together",
    "xai": "xAI",
}

PODS = [
    {
        "name": name,
        "host": name,
        "port": 5000,
        "model": cfg["model"],
        "provider": _PROVIDER_DISPLAY.get(cfg["provider"], cfg["provider"]),
        "category": cfg["category"],
    }
    for name, cfg in PODS_CONFIG.items()
]


def _is_local() -> bool:
    return os.environ.get("MULTI_CLAW_LOCAL") == "1"


def _local_pod_ports() -> dict[str, int]:
    raw = os.environ.get("LOCAL_POD_PORTS", "{}")
    return json.loads(raw)


def is_pod_enabled(name: str) -> bool:
    return PODS_REGISTRY.get(name, "off") == "on"


async def check_pod(pod: dict) -> dict:
    """Check health of a single pod."""
    if not is_pod_enabled(pod["name"]):
        return {**pod, "status": "disabled", "uptime": 0}

    # In local mode, bots run on localhost with unique ports
    if _is_local():
        port_map = _local_pod_ports()
        port = port_map.get(pod["name"])
        if port is None:
            return {**pod, "status": "offline", "uptime": 0}
        host = "127.0.0.1"
    else:
        host = pod["host"]
        port = pod["port"]

    url = f"http://{host}:{port}/health"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {**pod, "status": "healthy", "uptime": data.get("uptime", 0)}
                return {**pod, "status": "unhealthy", "uptime": 0}
    except Exception:
        return {**pod, "status": "offline", "uptime": 0}


async def check_all_pods() -> list[dict]:
    """Check health of all pods concurrently."""
    tasks = [check_pod(pod) for pod in PODS]
    return await asyncio.gather(*tasks)
