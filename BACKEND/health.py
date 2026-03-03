import asyncio
import aiohttp

from SETTINGS import PODS_REGISTRY

PODS = [
    {"name": "mini-claw", "host": "mini-claw", "port": 8080, "model": "gpt-4o", "provider": "OpenAI", "category": "Lightweight"},
    {"name": "pico-claw", "host": "pico-claw", "port": 8080, "model": "claude-sonnet-4-6", "provider": "Anthropic", "category": "Lightweight"},
    {"name": "nano-claw", "host": "nano-claw", "port": 8080, "model": "gemini-2.0-flash", "provider": "Google", "category": "Lightweight"},
    {"name": "tiny-claw", "host": "tiny-claw", "port": 8080, "model": "mistral-large", "provider": "Mistral", "category": "Lightweight"},
    {"name": "open-claw", "host": "open-claw", "port": 8080, "model": "gpt-4o-mini", "provider": "OpenAI", "category": "Full Runtime"},
    {"name": "zero-claw", "host": "zero-claw", "port": 8080, "model": "claude-haiku-4-5", "provider": "Anthropic", "category": "Full Runtime"},
    {"name": "titan-claw", "host": "titan-claw", "port": 8080, "model": "gemini-flash-lite", "provider": "Google", "category": "Full Runtime"},
    {"name": "kaf-claw", "host": "kaf-claw", "port": 8080, "model": "grok-2", "provider": "xAI", "category": "Full Runtime"},
    {"name": "safe-claw", "host": "safe-claw", "port": 8080, "model": "claude-opus-4-6", "provider": "Anthropic", "category": "Security"},
    {"name": "null-claw", "host": "null-claw", "port": 8080, "model": "deepseek-chat", "provider": "DeepSeek", "category": "Security"},
    {"name": "tinyagi", "host": "tinyagi", "port": 8080, "model": "llama-3.1-70b", "provider": "Groq", "category": "Experimental"},
    {"name": "nanobot", "host": "nanobot", "port": 8080, "model": "mixtral-8x22b", "provider": "Together", "category": "Experimental"},
]


def is_pod_enabled(name: str) -> bool:
    return PODS_REGISTRY.get(name, "off") == "on"


async def check_pod(pod: dict) -> dict:
    """Check health of a single pod."""
    if not is_pod_enabled(pod["name"]):
        return {**pod, "status": "disabled", "uptime": 0}

    url = f"http://{pod['host']}:{pod['port']}/health"
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
