# Guide: upgrade your twin into a Slack bot (Python)

**You are Claude Code, reading this file inside the user's twin project.** The
user already has a terminal twin — a Python file (usually `twin.py`) that chats
by dispatching `claude -p`. Your job is to **upgrade that file in place into a
Slack bot**: same brain, new face. Do **not** create a second bot file sitting
awkwardly next to `twin.py`. You are transforming `twin.py` itself into
`slack_bot.py`.

> ## ⚠️ First: confirm the stack
> Check whether the user's agent is **Node.js** (`package.json` / `*.js`) or
> **Python** (`requirements.txt` / `*.py`) — ask if unclear. **This is the
> Python guide.** If their agent is **Node.js**, stop and follow
> `guide for implementing slack.md` instead, so you install the files for the
> right language.

---

## The prompt the user pastes (for reference)

> Read `guide for implementing slack.md` from
> `https://raw.githubusercontent.com/luvishg-growthx/upgrading-your-bot-to-being-a-slack-bot/main/guide%20for%20implementing%20slack.md`
> and set up the Slack feature for my twin.

(For a Python twin, point the same prompt at
`https://raw.githubusercontent.com/luvishg-growthx/upgrading-your-bot-to-being-a-slack-bot/main/guide%20for%20implementing%20slack%20(python).md`
instead.)

---

## What "upgrade in place" means

- **Keep the brain** — the `claude -p` dispatch the user already has: the flags
  they pass, the project folder it runs in (so it loads their `CLAUDE.md` +
  handbook/persona), and the session-continuity logic that gives it memory.
- **Replace the face** — delete the terminal input loop and put a Slack
  **Socket Mode** app in its place.
- **One change to the memory model** — instead of ONE global session for the
  terminal, keep **one Claude session per Slack thread**, so each Slack thread
  has its own memory.
- **End state: one file.** The old `twin.py` is gone; `slack_bot.py` is the twin
  now. No duplicate dispatch logic anywhere.

The result: no API key (uses the logged-in Claude Code session), no public URL
(Socket Mode), replies posted back into the Slack thread in the twin's voice.

---

## Step 0 — Read the existing twin

1. Find the user's terminal twin file. It's usually `twin.py`; if it's named
   something else (`main.py`, `bot.py`, …), use that.
2. Read it and note **how it calls `claude -p`** — specifically:
   - the working directory it runs in (so the persona/handbook loads),
   - any extra flags it passes (`--allowedTools`, `--model`, etc.),
   - how it does session continuity (`--session-id` / `--resume`).
   Carry these into the upgraded file so the Slack twin replies exactly like the
   terminal twin did.
3. If you can't find any terminal twin, tell the user — this guide upgrades an
   existing twin; it assumes one exists.

---

## Step 1 — Write `slack_bot.py`

Create `slack_bot.py` in the **project root** (next to `CLAUDE.md`) with the
content below. This is the canonical shape. **Merge in** any custom flags you
found in Step 0 (add the user's `--allowedTools` / `--model` to the `args` list)
so behavior matches their twin.

```python
"""slack_bot.py — your twin, upgraded from a terminal chat into a Slack app.
Same brain (claude -p, with memory); new face (Slack). Lives in project root
next to CLAUDE.md so `claude -p` loads your persona/handbook automatically.
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

# Project root (this file's folder) — `claude -p` runs here so it loads your
# CLAUDE.md + handbook. Override with TWIN_DIR in .env only if needed.
TWIN_DIR = Path(os.environ.get("TWIN_DIR", Path(__file__).resolve().parent)).resolve()
CLAUDE_TIMEOUT_S = int(os.environ.get("CLAUDE_TIMEOUT_MS", "300000")) // 1000
SLACK_CHUNK = 3500  # Slack caps messages near 4000 chars

# One UUID per Slack thread: first msg creates the session, later msgs resume
# it. Same session-continuity idea your terminal twin used, but keyed per thread.
_thread_sessions: dict[str, dict] = {}


def _session_for(thread_id: str) -> dict:
    s = _thread_sessions.get(thread_id)
    if s is None:
        s = {"id": str(uuid.uuid4()), "started": False}
        _thread_sessions[thread_id] = s
    return s


# THE BRAIN — carried over from your terminal twin. Add any custom flags your
# old twin.py passed (e.g. "--allowedTools", ..., "--model", "...") here.
def ask_twin(thread_id: str, message: str) -> str:
    session = _session_for(thread_id)
    session_flag = (
        ["--resume", session["id"]] if session["started"] else ["--session-id", session["id"]]
    )
    session["started"] = True
    args = [
        "claude", "-p", message, *session_flag,
        "--permission-mode", "bypassPermissions",  # unattended bot
    ]
    try:
        result = subprocess.run(
            args, cwd=str(TWIN_DIR), capture_output=True, text=True, timeout=CLAUDE_TIMEOUT_S
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


# THE FACE — Slack instead of the terminal input loop.
app = App(token=os.environ["SLACK_BOT_TOKEN"])
SELF_USER_ID = app.client.auth_test()["user_id"]
_MENTION_RE = re.compile(r"<@[A-Z0-9]+>")


def _handle(text, channel, thread_id, say, client):
    clean = _MENTION_RE.sub("", text or "").strip()
    if not clean:
        return
    print(f'[slack] thread={thread_id} msg="{clean[:80]}"')
    try:
        client.reactions_add(channel=channel, name="eyes", timestamp=thread_id)
    except Exception:
        pass
    reply = ask_twin(thread_id, clean)
    for part in chunk(reply):
        say(text=part, thread_ts=thread_id)


@app.event("app_mention")
def on_mention(event, say, client):
    thread_id = event.get("thread_ts") or event["ts"]
    _handle(event.get("text", ""), event["channel"], thread_id, say, client)


@app.event("message")
def on_message(event, say, client):
    if event.get("bot_id") or event.get("subtype"):
        return
    if event.get("user") == SELF_USER_ID:
        return
    is_dm = event.get("channel_type") == "im"
    thread_ts = event.get("thread_ts")
    thread_id = thread_ts or event["ts"]
    is_follow_up = bool(thread_ts and thread_ts in _thread_sessions)
    if not is_dm and not is_follow_up:
        return
    _handle(event.get("text", ""), event["channel"], thread_id, say, client)


if __name__ == "__main__":
    print(f"⚡️ Twin Slack bot starting (twin dir: {TWIN_DIR})")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
```

---

## Step 2 — Remove the old terminal twin

The terminal input loop now lives nowhere — its job moved into `slack_bot.py`.
Delete the old `twin.py` (or, if the user wants a safety copy, rename it to
`twin.py.bak`). The point is a clean single app, not two files.

---

## Step 3 — Dependencies

```
pip install slack_bolt python-dotenv
```

Add them to `requirements.txt` (create it if missing):

```
slack_bolt>=1.18.0
python-dotenv>=1.0.0
```

---

## Step 4 — Slack app + tokens (have the USER do this)

You (Claude) **cannot** create the Slack app — it needs a human in a browser.
Print these steps and wait for the user to paste back the two tokens. Socket
Mode means no public URL is needed.

1. <https://api.slack.com/apps> → **Create New App** → **From scratch**; name
   it, pick the workspace.
2. **Socket Mode** → enable. Generate an **App-Level Token** with scope
   `connections:write`. Copy it → `SLACK_APP_TOKEN` (starts `xapp-`).
3. **OAuth & Permissions** → **Bot Token Scopes**, add: `app_mentions:read`,
   `chat:write`, `im:history`, `channels:history`, `groups:history`,
   `reactions:write`.
4. **Event Subscriptions** → enable → **Subscribe to bot events**:
   `app_mention`, `message.im`, `message.channels`, `message.groups`.
5. **Install App** → **Install to Workspace** → **Allow**. Copy the **Bot User
   OAuth Token** → `SLACK_BOT_TOKEN` (starts `xoxb-`).
6. In Slack: `/invite @YourBotName` into a channel (DMs need no invite).

Then create `.env` in the project root (and make sure `.env` is git-ignored):

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
# Optional: TWIN_DIR=/abs/path/to/twin   (default = this project root)
# Optional: CLAUDE_TIMEOUT_MS=300000
```

---

## Step 5 — Run & verify

1. Confirm Claude Code is installed/logged in: `claude --version`. If it fails,
   tell the user to install/login first.
2. Start the bot from the project root: `python slack_bot.py`.
3. Expect: `⚡️ Twin Slack bot starting (twin dir: …)`.
4. In Slack, `@mention` the bot in the invited channel (`@YourBot say hi`).
   Within seconds it should react 👀 and reply in a thread, in the twin's voice.
   Follow-ups inside that thread don't need another mention.

---

## Step 6 — Outbound actions: send / edit / delete messages

The bot above *replies* to people. To also let the twin **send, edit, delete,
and list** Slack messages on its own (e.g. "post 'standup in 5' to #general",
"delete that last message"), install the actions CLI + a skill.

**6a. Create `slack_actions.py`** in the project root:

```python
#!/usr/bin/env python3
"""slack_actions.py — send / edit / delete / list Slack messages from your agent.
Uses SLACK_BOT_TOKEN from .env. Slack only lets a bot edit/delete its OWN msgs."""
import json, os, re, sys, urllib.request
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
        headers={"Content-Type": "application/json; charset=utf-8", "Authorization": f"Bearer {TOKEN}"},
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
        print(f"sent ts={r['ts']}")
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
```

**6b. Create `.claude/skills/slack-message/SKILL.md`** so the twin knows it has
these powers and calls the CLI via Bash:

````markdown
---
name: slack-message
description: Send, edit, delete, or list Slack messages on the user's behalf. Trigger whenever the user asks to post/send a Slack message, edit/update a message already sent, delete/remove a message, or look up recent messages in a channel.
---

# Act on Slack (send / edit / delete / list)

Use the project's CLI via Bash (Python: `slack_actions.py`). Slack only lets the
bot **edit/delete messages it posted itself.**

```
python slack_actions.py send   <channel> <text...>      # prints the ts — save it
python slack_actions.py edit   <channel> <ts> <text...>
python slack_actions.py delete <channel> <ts>
python slack_actions.py list   <channel> [limit]        # "ts | user | text"
```

`<channel>` = channel ID (`C…`) or user ID (`U…`) for a DM.

- "Send X to <channel>" → `send`, then report the ts.
- "Edit/delete that message" → reuse the ts from a recent `send`, or `list` the
  channel to find the bot's message first. Confirm before deleting if ambiguous.
- Keep wording in the agent's voice unless the user gave exact text.
````

**6c.** The Slack scopes from Step 4 already cover this (`chat:write` for
send/edit/delete of the bot's own messages, `*:history` for `list`), so no scope
change is needed. The twin runs with `bypassPermissions`, so it can call the CLI
via Bash.

---

## Guardrails (do these, quietly)

- **Upgrade in place — don't duplicate.** End with one app file (`slack_bot.py`)
  and no leftover terminal twin running its own `claude -p`.
- **Preserve the brain.** Carry over the user's existing `claude -p` flags and
  working directory so the Slack twin answers exactly like the terminal one.
- **Don't touch** `CLAUDE.md`, the persona/handbook, or other source — the
  personality stays 100% the user's. This bot adds no voice of its own.
- **Never print or commit token values.** Ensure `.env` is git-ignored.
- If `claude -p` isn't found at runtime, it's almost always Claude Code not being
  installed / on PATH for the shell that launched the bot.

When finished, give the user a 3-line summary: that `twin.py` was upgraded into
`slack_bot.py`, that you added send/edit/delete via `slack_actions.py` + the
`slack-message` skill, and the exact command to start the bot.
