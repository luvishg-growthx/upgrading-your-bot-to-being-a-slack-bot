# Guide: upgrade your twin into a Slack bot (Node.js)

**You are Claude Code, reading this file inside the user's twin project.** The
user already has a terminal twin — a Node file (usually `twin.js`) that chats by
dispatching `claude -p`. Your job is to **upgrade that file in place into a
Slack bot**: same brain, new face. Do **not** create a second bot file sitting
awkwardly next to `twin.js`. You are transforming `twin.js` itself into
`slack-bot.js`.

> **Python twin?** Use the Python guide instead:
> `guide for implementing slack (python).md`.

---

## The prompt the user pastes (for reference)

> Read `guide for implementing slack.md` from
> `https://raw.githubusercontent.com/luvishg-growthx/upgrading-your-bot-to-being-a-slack-bot/main/guide%20for%20implementing%20slack.md`
> and set up the Slack feature for my twin.

---

## What "upgrade in place" means

- **Keep the brain** — the `claude -p` dispatch the user already has: the flags
  they pass, the project folder it runs in (so it loads their `CLAUDE.md` +
  handbook/persona), and the session-continuity logic that gives it memory.
- **Replace the face** — delete the terminal `readline` chat loop and put a
  Slack **Socket Mode** app in its place.
- **One change to the memory model** — instead of ONE global session for the
  terminal, keep **one Claude session per Slack thread**, so each Slack thread
  has its own memory.
- **End state: one file.** The old `twin.js` is gone; `slack-bot.js` is the
  twin now. No duplicate dispatch logic anywhere.

The result: no API key (uses the logged-in Claude Code session), no public URL
(Socket Mode), replies posted back into the Slack thread in the twin's voice.

---

## Step 0 — Read the existing twin

1. Find the user's terminal twin file. It's usually `twin.js`; if it's named
   something else (`main.js`, `index.js`, …), use that.
2. Read it and note **how it calls `claude -p`** — specifically:
   - the working directory it runs in (so the persona/handbook loads),
   - any extra flags it passes (`--allowedTools`, `--model`, etc.),
   - how it does session continuity (`--session-id` / `--resume`).
   You will carry these into the upgraded file so the Slack twin replies exactly
   like the terminal twin did.
3. If you can't find any terminal twin, tell the user — this guide upgrades an
   existing twin; it assumes one exists.

---

## Step 1 — Write `slack-bot.js`

Create `slack-bot.js` in the **project root** (next to `CLAUDE.md`) with the
content below. This is the canonical shape. **Merge in** any custom flags you
found in Step 0 (e.g. add the user's `--allowedTools` / `--model` to the `args`
array) so behavior matches their twin.

```javascript
// slack-bot.js — your twin, upgraded from a terminal chat into a Slack app.
// Same brain (claude -p, with memory); new face (Slack). Lives in project root
// next to CLAUDE.md so `claude -p` loads your persona/handbook automatically.

const { App } = require("@slack/bolt");
const { spawn } = require("child_process");
const { randomUUID } = require("crypto");
const path = require("path");
require("dotenv").config();

// Project root (this file's folder) — `claude -p` runs here so it loads your
// CLAUDE.md + handbook. Override with TWIN_DIR in .env only if needed.
const TWIN_DIR = process.env.TWIN_DIR ? path.resolve(process.env.TWIN_DIR) : __dirname;
const CLAUDE_TIMEOUT_MS = Number(process.env.CLAUDE_TIMEOUT_MS || 300000);
const SLACK_CHUNK = 3500; // Slack caps messages near 4000 chars

// One UUID per Slack thread: first msg creates the session, later msgs resume
// it. This is the same session-continuity idea your terminal twin used, but
// keyed per thread instead of one global session.
const threadSessions = new Map();
function sessionFor(threadId) {
  let s = threadSessions.get(threadId);
  if (!s) {
    s = { id: randomUUID(), started: false };
    threadSessions.set(threadId, s);
  }
  return s;
}

// THE BRAIN — carried over from your terminal twin. Add any custom flags your
// old twin.js passed (e.g. "--allowedTools", ..., "--model", "...") here.
function askTwin(threadId, message) {
  return new Promise((resolve) => {
    const session = sessionFor(threadId);
    const sessionFlag = session.started
      ? ["--resume", session.id]
      : ["--session-id", session.id];
    session.started = true;

    const args = [
      "-p",
      message,
      ...sessionFlag,
      "--permission-mode",
      "bypassPermissions", // bot is unattended — it can't answer prompts
    ];

    const child = spawn("claude", args, { cwd: TWIN_DIR, env: process.env });
    let out = "";
    let err = "";
    child.stdout.on("data", (d) => (out += d));
    child.stderr.on("data", (d) => (err += d));

    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      resolve("(the twin took too long and was stopped)");
    }, CLAUDE_TIMEOUT_MS);

    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        console.error("[claude] exit", code, err);
        resolve("(the twin hit an error — check the bot's logs)");
        return;
      }
      resolve(out.trim() || "(the twin had nothing to say)");
    });
    child.on("error", (e) => {
      clearTimeout(timer);
      console.error("[claude] spawn failed:", e.message);
      resolve("(couldn't start `claude` — is Claude Code installed and logged in?)");
    });
  });
}

function chunk(text) {
  if (text.length <= SLACK_CHUNK) return [text];
  const parts = [];
  let buf = "";
  for (const line of text.split("\n")) {
    if ((buf + "\n" + line).length > SLACK_CHUNK && buf) {
      parts.push(buf);
      buf = "";
    }
    buf = buf ? buf + "\n" + line : line;
  }
  if (buf) parts.push(buf);
  return parts;
}

// THE FACE — Slack instead of the terminal readline loop.
const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  appToken: process.env.SLACK_APP_TOKEN,
  socketMode: true,
});
let selfUserId = null;

async function handle({ text, channel, threadId, say, client }) {
  const clean = text.replace(/<@[A-Z0-9]+>/g, "").trim();
  if (!clean) return;
  console.log(`[slack] thread=${threadId} msg="${clean.slice(0, 80)}"`);
  try {
    await client.reactions.add({ channel, name: "eyes", timestamp: threadId });
  } catch (_) {}
  const reply = await askTwin(threadId, clean);
  for (const part of chunk(reply)) await say({ text: part, thread_ts: threadId });
}

app.event("app_mention", async ({ event, say, client }) => {
  const threadId = event.thread_ts || event.ts;
  await handle({ text: event.text, channel: event.channel, threadId, say, client });
});

app.event("message", async ({ event, say, client }) => {
  if (event.bot_id || event.subtype) return;
  if (event.user && event.user === selfUserId) return;
  const isDM = event.channel_type === "im";
  const threadId = event.thread_ts || event.ts;
  const isFollowUp = event.thread_ts && threadSessions.has(event.thread_ts);
  if (!isDM && !isFollowUp) return;
  await handle({ text: event.text, channel: event.channel, threadId, say, client });
});

(async () => {
  await app.start();
  const auth = await app.client.auth.test();
  selfUserId = auth.user_id;
  console.log(`⚡️ Twin Slack bot running as @${auth.user} (${selfUserId})`);
  console.log(`   twin dir: ${TWIN_DIR}`);
})();
```

---

## Step 2 — Remove the old terminal twin

The terminal `readline` chat now lives nowhere — its job moved into
`slack-bot.js`. Delete the old `twin.js` (or, if the user wants a safety copy,
rename it to `twin.js.bak`). The point is a clean single app, not two files.

If `package.json` has a `start`/`twin` script that ran `node twin.js`, update it
to `"start": "node slack-bot.js"`.

---

## Step 3 — Dependencies

Add the two libraries the Slack face needs:

```
npm install @slack/bolt dotenv
```

(If there's no `package.json`, create one first with `npm init -y`.)

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
2. Start the bot from the project root: `node slack-bot.js` (or `npm start`).
3. Expect: `⚡️ Twin Slack bot running as @… — twin dir: …`.
4. In Slack, `@mention` the bot in the invited channel (`@YourBot say hi`).
   Within seconds it should react 👀 and reply in a thread, in the twin's voice.
   Follow-ups inside that thread don't need another mention.

---

## Step 6 — Outbound actions: send / edit / delete messages

The bot above *replies* to people. To also let the twin **send, edit, delete,
and list** Slack messages on its own (e.g. "post 'standup in 5' to #general",
"delete that last message"), install the actions CLI + a skill.

**6a. Create `slack-actions.js`** in the project root:

```javascript
#!/usr/bin/env node
// slack-actions.js — send / edit / delete / list Slack messages from your agent.
// Uses SLACK_BOT_TOKEN from .env. Slack only lets a bot edit/delete its OWN msgs.
const path = require("path");
require("dotenv").config({ path: path.join(__dirname, ".env") });

const TOKEN = process.env.SLACK_BOT_TOKEN;
if (!TOKEN) { console.error("Missing SLACK_BOT_TOKEN (set it in .env)."); process.exit(1); }

async function slack(method, payload) {
  const res = await fetch(`https://slack.com/api/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8", Authorization: `Bearer ${TOKEN}` },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!data.ok) throw new Error(`${method} failed: ${data.error}`);
  return data;
}

async function main() {
  const [action, channel, ...rest] = process.argv.slice(2);
  if (!action || !channel) {
    console.error("usage: node slack-actions.js <send|edit|delete|list> <channel> [...]");
    process.exit(1);
  }
  switch (action) {
    case "send": {
      const text = rest.join(" ");
      if (!text) throw new Error("send needs message text");
      const r = await slack("chat.postMessage", { channel, text });
      console.log(`sent ts=${r.ts}`);
      break;
    }
    case "edit": {
      const [ts, ...textParts] = rest;
      const text = textParts.join(" ");
      if (!ts || !text) throw new Error("edit needs <ts> <text>");
      await slack("chat.update", { channel, ts, text });
      console.log(`edited ts=${ts}`);
      break;
    }
    case "delete": {
      const [ts] = rest;
      if (!ts) throw new Error("delete needs <ts>");
      await slack("chat.delete", { channel, ts });
      console.log(`deleted ts=${ts}`);
      break;
    }
    case "list": {
      const limit = Number(rest[0] || 10);
      const r = await slack("conversations.history", { channel, limit });
      for (const m of r.messages || []) {
        const text = (m.text || "").replace(/\s+/g, " ").slice(0, 100);
        console.log(`${m.ts} | ${m.user || m.bot_id || "?"} | ${text}`);
      }
      break;
    }
    default:
      console.error(`unknown action: ${action}`);
      process.exit(1);
  }
}
main().catch((e) => { console.error(e.message); process.exit(1); });
```

**6b. Create `.claude/skills/slack-message/SKILL.md`** so the twin knows it has
these powers and calls the CLI via Bash:

````markdown
---
name: slack-message
description: Send, edit, delete, or list Slack messages on the user's behalf. Trigger whenever the user asks to post/send a Slack message, edit/update a message already sent, delete/remove a message, or look up recent messages in a channel.
---

# Act on Slack (send / edit / delete / list)

Use the project's CLI via Bash (Node: `slack-actions.js`). Slack only lets the
bot **edit/delete messages it posted itself.**

```
node slack-actions.js send   <channel> <text...>      # prints the ts — save it
node slack-actions.js edit   <channel> <ts> <text...>
node slack-actions.js delete <channel> <ts>
node slack-actions.js list   <channel> [limit]        # "ts | user | text"
```

`<channel>` = channel ID (`C…`) or user ID (`U…`) for a DM.

- "Send X to <channel>" → `send`, then report the ts.
- "Edit/delete that message" → reuse the ts from a recent `send`, or `list` the
  channel to find the bot's message first. Confirm before deleting if ambiguous.
- Keep wording in the agent's voice unless the user gave exact text.
````

**6c.** Make sure the bot's Slack scopes include `chat:write` (send/edit/delete
of its own messages) and the `*:history` scopes (for `list`) — they're already in
the Step 4 scope list, so no change is needed. The twin runs with
`bypassPermissions`, so it can already call the CLI via Bash.

---

## Guardrails (do these, quietly)

- **Upgrade in place — don't duplicate.** End with one app file (`slack-bot.js`)
  and no leftover terminal twin running its own `claude -p`.
- **Preserve the brain.** Carry over the user's existing `claude -p` flags and
  working directory so the Slack twin answers exactly like the terminal one.
- **Don't touch** `CLAUDE.md`, the persona/handbook, or other source — the
  personality stays 100% the user's. This bot adds no voice of its own.
- **Never print or commit token values.** Ensure `.env` is git-ignored.
- If `claude -p` isn't found at runtime, it's almost always Claude Code not being
  installed / on PATH for the shell that launched the bot.

When finished, give the user a 3-line summary: that `twin.js` was upgraded into
`slack-bot.js`, that you added send/edit/delete via `slack-actions.js` + the
`slack-message` skill, and the exact command to start the bot.
