import asyncio
import hashlib
import importlib.util
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from SETTINGS import APP_TITLE, HOST, PORT, RELOAD, LIVE_RELOAD, LIVE_RELOAD_INTERVAL, PODS_REGISTRY, PODS_CONFIG

app = FastAPI(title=APP_TITLE)

FRONTEND_DIR = Path(__file__).parent / "FRONTEND"

# pip package name → import name (only where they differ)
_IMPORT_MAP = {
    "python-telegram-bot": "telegram",
    "google-api-python-client": "googleapiclient",
    "google-auth": "google.auth",
    "google-genai": "google.genai",
}


def _import_name(pip_pkg: str) -> str:
    """Convert pip package name to its top-level import name."""
    base = pip_pkg.split(">=")[0].split("<=")[0].split(">")[0].split("<")[0].split("==")[0].strip()
    return _IMPORT_MAP.get(base, base.replace("-", "_"))


def ensure_dependencies(requirements_file: str):
    """Check all packages from requirements file; install missing ones in one go."""
    req_path = Path(__file__).parent / requirements_file
    if not req_path.exists():
        return

    missing = []
    for line in req_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        mod = _import_name(line)
        try:
            if importlib.util.find_spec(mod) is None:
                missing.append(line)
        except ModuleNotFoundError:
            missing.append(line)

    if not missing:
        return

    print(f"Installing missing packages: {', '.join(missing)}")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--quiet", "--no-warn-script-location", *missing],
    )
    importlib.invalidate_caches()


def get_enabled_pods() -> list[str]:
    """Return list of pod names that are 'on' in SETTINGS."""
    return [name for name, state in PODS_REGISTRY.items() if state == "on"]


def docker_available() -> bool:
    """Check if Docker daemon is running and responsive."""
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _sync_compose_profiles():
    """Write COMPOSE_PROFILES to .env so bare 'docker compose up' works."""
    env_path = Path(__file__).parent / ".env"
    profiles_value = ",".join(get_enabled_pods())

    if env_path.exists():
        text = env_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        found = False
        for i, line in enumerate(lines):
            if line.startswith("COMPOSE_PROFILES=") or line.startswith("# COMPOSE_PROFILES="):
                lines[i] = f"COMPOSE_PROFILES={profiles_value}"
                found = True
                break
        if not found:
            lines.append(f"\n# Auto-generated from SETTINGS.py (python run.py sync)")
            lines.append(f"COMPOSE_PROFILES={profiles_value}")
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        env_path.write_text(f"COMPOSE_PROFILES={profiles_value}\n", encoding="utf-8")

    print(f"Synced COMPOSE_PROFILES={profiles_value} → .env")


def compose_up():
    """Launch docker compose with only enabled pod profiles."""
    _sync_compose_profiles()

    enabled = get_enabled_pods()
    if not enabled:
        print("No pods enabled in SETTINGS.py — starting only orchestrator.")

    cmd = ["docker", "compose", "up", "-d", "--build"]

    print(f"Enabled pods: {enabled}")
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)


SETTINGS_PATH = Path(__file__).parent / "SETTINGS.py"
def _settings_snapshot() -> str:
    """Hash pod-related config: PROVIDERS dict + *_PROVIDER + *_ENABLED constants."""
    text = SETTINGS_PATH.read_text(encoding="utf-8")
    # Extract PROVIDERS dict block
    start = text.find("PROVIDERS = {")
    end = text.find("}", start) + 1 if start != -1 else 0
    providers_block = text[start:end]
    # Extract individual pod constants
    pod_lines = re.findall(r'^(\w+_(?:PROVIDER|ENABLED|TOPIC_ID)\s*=\s*.+)$', text, re.MULTILINE)
    watched = providers_block + "\n".join(pod_lines)
    return hashlib.md5(watched.encode()).hexdigest()


async def _watch_settings():
    """Restart only when PROVIDERS/PROVIDER/ENABLED constants change."""
    snapshot = _settings_snapshot()
    while True:
        await asyncio.sleep(2)
        current = _settings_snapshot()
        if current != snapshot:
            print("\nSETTINGS.py pod config changed — restarting...")
            os.execv(sys.executable, [sys.executable] + sys.argv)


async def _run_bot_local(pod_name: str, cfg: dict, health_port: int):
    """Start a single bot in the current process."""
    from BACKEND.provider_factory import create_provider
    from BACKEND.base_bot import BaseBot

    token_env = "TELEGRAM_TOKEN_" + pod_name.upper().replace("-", "_")
    token = os.environ.get(token_env)
    api_key = os.environ.get(cfg["api_key_env"])

    if not token:
        print(f"  [!] {pod_name}: {token_env} not set — skipped")
        return
    if not api_key:
        print(f"  [!] {pod_name}: {cfg['api_key_env']} not set — skipped")
        return

    ai = create_provider(
        provider_name=cfg["provider"],
        model=cfg["model"],
        api_key=api_key,
    )
    bot = BaseBot(token=token, pod_name=pod_name, ai=ai, health_port=health_port, topic_id=cfg.get("topic_id"))
    await bot.run()


def local_up():
    """Run dashboard + enabled bots locally without Docker."""
    ensure_dependencies("BACKEND/requirements-pod.txt")

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    enabled = get_enabled_pods()
    print(f"Local mode (no Docker) — enabled pods: {enabled}")

    # Build port map and store it so health.py can use it
    port_map = {}
    for i, name in enumerate(enabled):
        port_map[name] = 8081 + i
    os.environ["MULTI_CLAW_LOCAL"] = "1"
    os.environ["LOCAL_POD_PORTS"] = json.dumps(port_map)

    # Suppress telegram's noisy CancelledError traceback on Ctrl+C shutdown
    # CRITICAL=50, so we set above it to silence the non-error shutdown log
    logging.getLogger("telegram.ext.Application").setLevel(logging.CRITICAL + 1)

    async def _run_all():
        tasks = [asyncio.create_task(_watch_settings())]
        for name in enabled:
            cfg = PODS_CONFIG[name]
            tasks.append(asyncio.create_task(
                _run_bot_local(name, cfg, port_map[name])
            ))

        # Uvicorn alongside bots (reload disabled in local mode)
        config = uvicorn.Config("run:app", host=HOST, port=PORT, reload=False)
        server = uvicorn.Server(config)
        tasks.append(asyncio.create_task(server.serve()))

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            # Suppress noisy shutdown tracebacks from telegram and asyncio
            for name in ("telegram.ext.Updater", "telegram.ext.Application",
                         "httpx", "httpcore", "asyncio"):
                logging.getLogger(name).setLevel(logging.CRITICAL + 1)

            server.should_exit = True
            for t in tasks:
                if not t.done():
                    t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    try:
        asyncio.run(_run_all())
    except KeyboardInterrupt:
        print("\nShutdown complete.")


# ═══════════════════════════════════════════════════════════════
# FastAPI routes
# ═══════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("{{APP_TITLE}}", APP_TITLE)
    if LIVE_RELOAD:
        script = f'<script>(async()=>{{let h=null;while(true){{try{{const r=await fetch("/api/hash");const{{hash}}=await r.json();if(h&&hash!==h)location.reload();h=hash}}catch{{}}await new Promise(r=>setTimeout(r,{LIVE_RELOAD_INTERVAL * 1000}))}}}})();</script>'
        html = html.replace("</body>", script + "</body>")
    return html


if LIVE_RELOAD:
    def _hash_frontend():
        h = hashlib.md5()
        for f in sorted(FRONTEND_DIR.rglob("*")):
            if f.is_file():
                h.update(f.read_bytes())
        return h.hexdigest()

    @app.get("/api/hash")
    async def frontend_hash():
        return {"hash": _hash_frontend()}


@app.get("/api/pods")
async def api_pods():
    try:
        from BACKEND.health import check_all_pods
        results = await check_all_pods()
        return JSONResponse(content=results)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/enabled")
async def api_enabled():
    return JSONResponse(content=get_enabled_pods())


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools():
    return JSONResponse(content={})


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(FRONTEND_DIR / "favicon.svg", media_type="image/svg+xml")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "compose":
        compose_up()
    elif len(sys.argv) > 1 and sys.argv[1] == "local":
        local_up()
    else:
        # Auto-detect: Docker available → compose, otherwise → local
        if docker_available():
            print("Docker detected — launching via docker compose...")
            compose_up()
        else:
            print("Docker not available — falling back to local mode...")
            local_up()
