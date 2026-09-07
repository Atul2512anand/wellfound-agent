#!/usr/bin/env python3
"""Helper to find your Telegram chat ID after messaging your bot."""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Allow running without pip install -e .
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wellfound_agent.config import TELEGRAM_BOT_TOKEN


def main():
    token = TELEGRAM_BOT_TOKEN or input("Paste your TELEGRAM_BOT_TOKEN: ").strip()
    if not token:
        print("No token provided.")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"Error: {exc.read().decode()}")
        sys.exit(1)

    if not data.get("ok"):
        print(f"API error: {data}")
        sys.exit(1)

    updates = data.get("result", [])
    if not updates:
        print("No messages found.")
        print("1. Open your bot in Telegram")
        print("2. Send /start")
        print("3. Run this script again")
        sys.exit(1)

    seen = set()
    print("\nYour chat ID(s):\n")
    for update in updates:
        msg = update.get("message") or update.get("edited_message") or {}
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        if not chat_id or chat_id in seen:
            continue
        seen.add(chat_id)
        name = chat.get("first_name", "") + " " + chat.get("last_name", "")
        username = chat.get("username", "")
        print(f"  TELEGRAM_CHAT_ID={chat_id}  ({name.strip()} @{username})")

    print("\nAdd this line to your .env file.")


if __name__ == "__main__":
    main()
