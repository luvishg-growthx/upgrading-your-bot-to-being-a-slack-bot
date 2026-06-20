"""slack_bot.py — your twin, upgraded from a terminal chat into a Slack app.

This file IS your twin. It keeps the same brain your terminal twin had
(dispatch to `claude -p`, with memory) and swaps the terminal chat for a Slack
front-end:
  - Listens to Slack (Socket Mode — no public URL needed).
  - When someone @mentions the bot, DMs it, or replies in a thread the bot is
    already in, it sends that message to your twin via `claude -p`.
  - `claude -p` runs inside this project folder, so it automatically loads your
    CLAUDE.md + handbook/persona files — the reply sounds like your agent, not a
    generic assistant.
  - It keeps ONE Claude session per Slack thread, so each thread has memory.
  - The reply is posted back into the same Slack thread.

No API key. It uses your logged-in Claude Code session, just like before.

Run:  python slack_bot.py   (after `pip install -r requirements.txt` and .env)
"""

import os
import re
import subprocess
import uuid
from pathlib import Path

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

# Where YOUR twin lives. `claude -p` runs here so it loads your CLAUDE.md,
# PERSONA.md / handbook, and any skills. Defaults to this file's own folder
# (this bot lives in your project root, next to CLAUDE.md). Override with
# TWIN_DIR in .env.
TWIN_DIR = Path(os.environ.get("TWIN_DIR", Path(__file__).resolve().parent)).resolve()

# How long to let one Claude turn run before giving up (seconds).
CLAUDE_TIMEOUT_S = int(os.environ.get("CLAUDE_TIMEOUT_MS", "300000")) // 1000

# Slack messages cap around 4000 chars; split below that to be safe.
SLACK_CHUNK = 3500

# ── One Claude session per Slack thread = per-thread memory ───────────────────
#
# `claude --session-id` needs a UUID. Slack thread ids aren't UUIDs, so we map
# each thread to a UUID the first time we see it. First message in a thread
# creates the session (--session-id); later messages resume it (--resume), so
# the twin remembers the conversation. (In-memory: a bot restart starts fresh.)
_thread_sessions: dict[str, dict] = {}  # slack_thread_id -> {"id", "started"}


def _session_for(thread_id: str) -> dict:
    s = _thread_sessions.get(thread_id)
    if s is None:
        s = {"id": str(uuid.uuid4()), "started": False}
        _thread_sessions[thread_id] = s
    return s


# ── Dispatch one message to the twin via `claude -p` ──────────────────────────

def ask_twin(thread_id: str, message: str) -> str:
    session = _session_for(thread_id)
    session_flag = (
        ["--resume", session["id"]] if session["started"] else ["--session-id", session["id"]]
    )
    session["started"] = True

    args = [
        "claude",
        "-p",
        message,
        *session_flag,
        # The bot runs unattended, so it can't answer permission prompts.
        # bypassPermissions lets the twin use its tools (read files, etc.) freely.
        "--permission-mode",
        "bypassPermissions",
    ]

    try:
        result = subprocess.run(
            args,
            cwd=str(TWIN_DIR),  # <-- loads your CLAUDE.md + handbook/persona
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return "(the twin took too long and was stopped)"
    except FileNotFoundError:
        return "(couldn't start `claude` — is Claude Code installed and logged in?)"

    if result.returncode != 0:
        print("[claude] exit", result.returncode, result.stderr)
        return "(the twin hit an error — check the bot's logs)"

    return result.stdout.strip() or "(the twin had nothing to say)"


def chunk(text: str) -> list[str]:
    """Split a long reply into Slack-sized chunks (prefer breaking on newlines)."""
    if len(text) <= SLACK_CHUNK:
        return [text]
    parts, buf = [], ""
    for line in text.split("\n"):
        if buf and len(buf) + 1 + len(line) > SLACK_CHUNK:
            parts.append(buf)
            buf = ""
        buf = line if not buf else buf + "\n" + line
    if buf:
        parts.append(buf)
    return parts


# ── Slack wiring ──────────────────────────────────────────────────────────────

app = App(token=os.environ["SLACK_BOT_TOKEN"])

# The bot's own user id, so we can strip @mentions and ignore our own posts.
SELF_USER_ID = app.client.auth_test()["user_id"]

_MENTION_RE = re.compile(r"<@[A-Z0-9]+>")


def _handle(text: str, channel: str, thread_id: str, say, client) -> None:
    clean = _MENTION_RE.sub("", text or "").strip()
    if not clean:
        return

    print(f"[slack] thread={thread_id} msg=\"{clean[:80]}\"")

    # Best-effort "I'm on it" signal.
    try:
        client.reactions_add(channel=channel, name="eyes", timestamp=thread_id)
    except Exception:
        pass

    reply = ask_twin(thread_id, clean)
    for part in chunk(reply):
        say(text=part, thread_ts=thread_id)


# 1) @mentions in a channel.
@app.event("app_mention")
def on_mention(event, say, client):
    thread_id = event.get("thread_ts") or event["ts"]
    _handle(event.get("text", ""), event["channel"], thread_id, say, client)


# 2) DMs, and 3) thread replies in threads the bot is already part of.
@app.event("message")
def on_message(event, say, client):
    # Ignore bots (including ourselves) and edits/joins/etc.
    if event.get("bot_id") or event.get("subtype"):
        return
    if event.get("user") == SELF_USER_ID:
        return

    is_dm = event.get("channel_type") == "im"
    thread_ts = event.get("thread_ts")
    thread_id = thread_ts or event["ts"]
    is_follow_up = bool(thread_ts and thread_ts in _thread_sessions)

    # In channels we only start on an @mention (handled above). Here we only
    # handle DMs and follow-ups inside threads the bot already owns.
    if not is_dm and not is_follow_up:
        return

    _handle(event.get("text", ""), event["channel"], thread_id, say, client)


if __name__ == "__main__":
    # If the cronjobs module is also installed, auto-start its scheduler in this
    # same process so scheduled messages fire even when only the Slack bot runs.
    # Best-effort: no-op if scheduler.py isn't present.
    try:
        from scheduler import start_scheduler
        start_scheduler()
    except Exception:
        pass
    print(f"⚡️ Twin Slack bot starting (twin dir: {TWIN_DIR})")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
