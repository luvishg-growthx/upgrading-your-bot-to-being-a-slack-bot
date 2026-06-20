#!/usr/bin/env python3
"""slack_actions.py — let your agent SEND, EDIT, DELETE, and LIST Slack messages.

The Slack bot (slack_bot.py) *replies* to people. This CLI gives your twin the
other half: acting on Slack on its own. Your agent calls it via Bash, e.g. when
you say "post 'standup in 5' to #general" or "delete that last message".

Uses the same SLACK_BOT_TOKEN from your .env. Note: Slack only lets a bot
edit/delete messages IT posted.

Usage:
  python slack_actions.py send   <channel> <text...>      -> posts, prints the ts
  python slack_actions.py edit   <channel> <ts> <text...> -> updates that message
  python slack_actions.py delete <channel> <ts>           -> deletes that message
  python slack_actions.py list   <channel> [limit]        -> recent msgs (ts | user | text)

<channel> is a channel ID (e.g. C0123ABC) or a user ID (e.g. U0123ABC) for a DM.
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

TOKEN = os.environ.get("SLACK_BOT_TOKEN")
if not TOKEN:
    print("Missing SLACK_BOT_TOKEN (set it in .env).", file=sys.stderr)
    sys.exit(1)


def slack(method: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {TOKEN}",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    if not data.get("ok"):
        raise RuntimeError(f"{method} failed: {data.get('error')}")
    return data


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2:
        print("usage: python slack_actions.py <send|edit|delete|list> <channel> [...]", file=sys.stderr)
        sys.exit(1)

    action, channel, rest = args[0], args[1], args[2:]

    if action == "send":
        text = " ".join(rest)
        if not text:
            raise RuntimeError("send needs message text")
        r = slack("chat.postMessage", {"channel": channel, "text": text})
        print(f"sent ts={r['ts']}")  # capture this ts to edit/delete later

    elif action == "edit":
        if len(rest) < 2:
            raise RuntimeError("edit needs <ts> <text>")
        ts, text = rest[0], " ".join(rest[1:])
        slack("chat.update", {"channel": channel, "ts": ts, "text": text})
        print(f"edited ts={ts}")

    elif action == "delete":
        if not rest:
            raise RuntimeError("delete needs <ts>")
        ts = rest[0]
        slack("chat.delete", {"channel": channel, "ts": ts})
        print(f"deleted ts={ts}")

    elif action == "list":
        limit = int(rest[0]) if rest else 10
        r = slack("conversations.history", {"channel": channel, "limit": limit})
        for m in r.get("messages", []):
            text = re.sub(r"\s+", " ", m.get("text", ""))[:100]
            print(f"{m.get('ts')} | {m.get('user') or m.get('bot_id') or '?'} | {text}")

    else:
        print(f"unknown action: {action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
