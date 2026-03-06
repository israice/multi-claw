"""
Create a Telegram supergroup with forum topics for each pod.

Usage:
    1. Fill TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE in .env
    2. pip install pyrogram
    3. python BACKEND/create_telegram_group_with_topics.py
    4. On first run, enter the confirmation code from Telegram
    5. Copy the printed topic IDs into SETTINGS.py
"""

import asyncio
import os
import sys

# Python 3.12+ removed auto-creation of event loop in get_event_loop().
# Pyrogram's sync wrapper needs one to exist before import.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.errors import FloodWait
from pyrogram.raw.functions.channels import ToggleForum
from pyrogram.raw.types import InputChannel

# --- load project root so we can import SETTINGS ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from SETTINGS import _PODS_RAW, TELEGRAM_GROUP_NICKNAME  # noqa: E402

# --- config ---
API_ID = os.environ.get("TELEGRAM_API_ID")
API_HASH = os.environ.get("TELEGRAM_API_HASH")
PHONE = os.environ.get("TELEGRAM_PHONE")

if not API_ID or not API_HASH:
    print("ERROR: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")
    print("Get them from https://my.telegram.org")
    sys.exit(1)

# Pause between every Telegram API call (seconds).
# Telegram rate-limits bursts harshly — 2s per call keeps us safe.
API_CALL_DELAY = 2

# --- collect bot user IDs from tokens in .env ---
TOKEN_ENV_MAP = {
    "mini-claw":  "TELEGRAM_TOKEN_MINI_CLAW",
    "pico-claw":  "TELEGRAM_TOKEN_PICO_CLAW",
    "nano-claw":  "TELEGRAM_TOKEN_NANO_CLAW",
    "tiny-claw":  "TELEGRAM_TOKEN_TINY_CLAW",
    "open-claw":  "TELEGRAM_TOKEN_OPEN_CLAW",
    "zero-claw":  "TELEGRAM_TOKEN_ZERO_CLAW",
    "titan-claw": "TELEGRAM_TOKEN_TITAN_CLAW",
    "kaf-claw":   "TELEGRAM_TOKEN_KAF_CLAW",
    "safe-claw":  "TELEGRAM_TOKEN_SAFE_CLAW",
    "null-claw":  "TELEGRAM_TOKEN_NULL_CLAW",
    "tinyagi":    "TELEGRAM_TOKEN_TINYAGI",
    "nanobot":    "TELEGRAM_TOKEN_NANOBOT",
}


def get_bot_user_ids():
    """Extract bot user IDs from tokens (format: <user_id>:<hash>)."""
    bot_ids = {}
    for pod_name, env_var in TOKEN_ENV_MAP.items():
        token = os.environ.get(env_var, "")
        if token and ":" in token:
            bot_ids[pod_name] = int(token.split(":")[0])
    return bot_ids


async def safe_call(coro_func, *args, **kwargs):
    """Call an async Telegram method with FloodWait auto-retry and delay."""
    while True:
        try:
            result = await coro_func(*args, **kwargs)
            await asyncio.sleep(API_CALL_DELAY)
            return result
        except FloodWait as e:
            wait = e.value + 1
            print(f"      [FloodWait] Telegram asks to wait {e.value}s — sleeping {wait}s...")
            await asyncio.sleep(wait)


async def main():
    group_name = f"multi-claw-{TELEGRAM_GROUP_NICKNAME}"
    session_path = os.path.join(PROJECT_ROOT, "multi_claw_user")

    # Check if session file exists (avoids auth.SendCode flood)
    session_file = session_path + ".session"
    if not os.path.exists(session_file):
        print("No session file found — first-time authorization required.")
        print("Telegram will send a confirmation code to your app.")
        if not PHONE:
            print("ERROR: TELEGRAM_PHONE must be set in .env for first-time auth.")
            sys.exit(1)
        print(f"Phone: {PHONE}")
        print("IMPORTANT: If auth fails, do NOT re-run immediately!")
        print("           Wait at least 5 minutes before retrying.\n")
    else:
        print(f"Session file found: {session_file}")
        print("Skipping auth — using saved session.\n")

    # sleep_threshold=120: Pyrogram auto-sleeps on FloodWait up to 120s
    # instead of raising the exception. Extra safety on top of safe_call.
    app = Client(
        session_path,
        api_id=int(API_ID),
        api_hash=API_HASH,
        phone_number=PHONE,
        sleep_threshold=120,
    )

    try:
        async with app:
            # 1. Create supergroup
            print(f"[1/5] Creating supergroup '{group_name}'...")
            chat = await safe_call(app.create_supergroup, group_name, "Multi-Claw bot group with forum topics")
            chat_id = chat.id
            print(f"      Created: {chat.title} (id={chat_id})")

            # 2. Enable forum mode via raw API
            print("[2/5] Enabling forum mode...")
            peer = await safe_call(app.resolve_peer, chat_id)
            await safe_call(
                app.invoke,
                ToggleForum(
                    channel=InputChannel(
                        channel_id=peer.channel_id,
                        access_hash=peer.access_hash,
                    ),
                    enabled=True,
                ),
            )
            print("      Forum enabled.")

            # 3. Create topics for each pod
            print("[3/5] Creating forum topics...")
            pod_names = list(_PODS_RAW.keys())
            topics = {}
            for pod_name in pod_names:
                topic = await safe_call(app.create_forum_topic, chat_id, pod_name)
                topics[pod_name] = topic.id
                print(f"      {pod_name} -> topic_id={topic.id}")

            # 4. Add bots and promote them
            print("[4/5] Adding bots to group...")
            bot_ids = get_bot_user_ids()
            for pod_name, bot_user_id in bot_ids.items():
                try:
                    await safe_call(app.add_chat_members, chat_id, bot_user_id)
                    await safe_call(app.promote_chat_member, chat_id, bot_user_id)
                    print(f"      Added & promoted: {pod_name} (uid={bot_user_id})")
                except Exception as e:
                    print(f"      WARNING: {pod_name} (uid={bot_user_id}): {e}")

            # 5. Print results table
            print("\n[5/5] Results — copy these into SETTINGS.py:\n")
            print(f"{'Pod':<15} {'topic_id':<12} {'SETTINGS.py variable'}")
            print("-" * 55)

            for pod_name in pod_names:
                tid = topics.get(pod_name, "N/A")
                var_name = pod_name.upper().replace("-", "_") + "_TOPIC_ID"
                setting_line = f"{var_name:<24} = {tid}"
                print(f"{pod_name:<15} {str(tid):<12} {setting_line}")

            print(f"\nGroup chat_id: {chat_id}")
            print("Done!")

    except FloodWait as e:
        minutes = e.value // 60
        hours = minutes // 60
        mins = minutes % 60
        print(f"\nFLOOD_WAIT: Telegram requires a wait of {e.value}s (~{hours}h {mins}m)")
        print("This happens during auth when too many SendCode calls are made.")
        print("DO NOT re-run the script — wait the full time, then try once.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
