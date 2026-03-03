import asyncio
import time
from aiohttp import web


class HealthServer:
    """Simple HTTP server for Docker healthcheck on /health."""

    def __init__(self, port: int = 8080):
        self.port = port
        self.start_time = time.time()
        self.healthy = True

    async def handle_health(self, request: web.Request) -> web.Response:
        if self.healthy:
            uptime = int(time.time() - self.start_time)
            return web.json_response({"status": "ok", "uptime": uptime})
        return web.json_response({"status": "unhealthy"}, status=503)

    async def start(self):
        app = web.Application()
        app.router.add_get("/health", self.handle_health)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()
