import hashlib
import subprocess
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from SETTINGS import APP_TITLE, HOST, PORT, RELOAD, LIVE_RELOAD, LIVE_RELOAD_INTERVAL, PODS_REGISTRY

app = FastAPI(title=APP_TITLE)

FRONTEND_DIR = Path(__file__).parent / "FRONTEND"


def get_enabled_pods() -> list[str]:
    """Return list of pod names that are 'on' in SETTINGS."""
    return [name for name, state in PODS_REGISTRY.items() if state == "on"]


def compose_up():
    """Launch docker compose with only enabled pod profiles."""
    enabled = get_enabled_pods()
    if not enabled:
        print("No pods enabled in SETTINGS.py — starting only orchestrator.")

    cmd = ["docker", "compose"]
    for pod in enabled:
        cmd += ["--profile", pod]
    cmd += ["up", "-d", "--build"]

    print(f"Enabled pods: {enabled}")
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)


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


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(FRONTEND_DIR / "favicon.svg", media_type="image/svg+xml")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "compose":
        compose_up()
    else:
        uvicorn.run("run:app", host=HOST, port=PORT, reload=RELOAD)
