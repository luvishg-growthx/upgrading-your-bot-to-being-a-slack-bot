// slack-bot.js — your twin, upgraded from a terminal chat into a Slack app.
//
// This file IS your twin. It keeps the same brain your terminal twin had
// (dispatch to `claude -p`, with memory) and swaps the terminal chat for a
// Slack front-end:
//   - Listens to Slack (Socket Mode — no public URL needed).
//   - When someone @mentions the bot, DMs it, or replies in a thread the bot
//     is already in, it sends that message to your twin via `claude -p`.
//   - `claude -p` runs inside this project folder, so it automatically loads
//     your CLAUDE.md + handbook/persona files — the reply sounds like your
//     agent, not a generic assistant.
//   - It keeps ONE Claude session per Slack thread, so each thread has memory.
//   - The reply is posted back into the same Slack thread.
//
// No API key. It uses your logged-in Claude Code session, just like before.
//
// Run:  node slack-bot.js   (after `npm install` and filling in .env)

const { App } = require("@slack/bolt");
const { spawn } = require("child_process");
const { randomUUID } = require("crypto");
const path = require("path");
require("dotenv").config();

// ── Config ──────────────────────────────────────────────────────────────────

// Where YOUR twin lives. `claude -p` runs here so it loads your CLAUDE.md,
// PERSONA.md / handbook, and any skills. Defaults to this file's own folder
// (this bot lives in your project root, next to CLAUDE.md). Override in .env.
const TWIN_DIR = process.env.TWIN_DIR
  ? path.resolve(process.env.TWIN_DIR)
  : __dirname;

// How long to let one Claude turn run before giving up (ms).
const CLAUDE_TIMEOUT_MS = Number(process.env.CLAUDE_TIMEOUT_MS || 300000);

// Slack messages cap around 4000 chars; split below that to be safe.
const SLACK_CHUNK = 3500;

// ── One Claude session per Slack thread = per-thread memory ──────────────────
//
// claude --session-id needs a UUID. Slack thread ids aren't UUIDs, so we map
// each thread to a UUID the first time we see it. First message in a thread
// creates the session (--session-id); later messages resume it (--resume), so
// the twin remembers the conversation. (In-memory: a bot restart starts fresh.)
const threadSessions = new Map(); // slackThreadId -> { id, started }

function sessionFor(threadId) {
  let s = threadSessions.get(threadId);
  if (!s) {
    s = { id: randomUUID(), started: false };
    threadSessions.set(threadId, s);
  }
  return s;
}

// ── Dispatch one message to the twin via `claude -p` ─────────────────────────

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
      // The bot runs unattended, so it can't answer permission prompts.
      // bypassPermissions lets the twin use its tools (read files, etc.) freely.
      "--permission-mode",
      "bypassPermissions",
    ];

    const child = spawn("claude", args, {
      cwd: TWIN_DIR, // <-- loads your CLAUDE.md + handbook/persona
      env: process.env,
    });

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

// Split a long reply into Slack-sized chunks (prefer breaking on newlines).
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

// ── Slack wiring ─────────────────────────────────────────────────────────────

const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  appToken: process.env.SLACK_APP_TOKEN,
  socketMode: true,
});

let selfUserId = null; // the bot's own user id, so we can strip @mentions

// Shared handler: react 👀, ask the twin, post the reply in-thread.
async function handle({ text, channel, threadId, say, client }) {
  const clean = text.replace(/<@[A-Z0-9]+>/g, "").trim();
  if (!clean) return;

  console.log(`[slack] thread=${threadId} msg="${clean.slice(0, 80)}"`);

  // Best-effort "I'm on it" signal.
  try {
    await client.reactions.add({ channel, name: "eyes", timestamp: threadId });
  } catch (_) {}

  const reply = await askTwin(threadId, clean);
  for (const part of chunk(reply)) {
    await say({ text: part, thread_ts: threadId });
  }
}

// 1) @mentions in a channel.
app.event("app_mention", async ({ event, say, client }) => {
  const threadId = event.thread_ts || event.ts;
  await handle({ text: event.text, channel: event.channel, threadId, say, client });
});

// 2) DMs, and 3) thread replies in threads the bot is already part of.
app.event("message", async ({ event, say, client }) => {
  // Ignore bots (including ourselves) and edits/joins/etc.
  if (event.bot_id || event.subtype) return;
  if (event.user && event.user === selfUserId) return;

  const isDM = event.channel_type === "im";
  const threadId = event.thread_ts || event.ts;
  const isFollowUp = event.thread_ts && threadSessions.has(event.thread_ts);

  // In channels we only start on an @mention (handled above). Here we only
  // handle DMs and follow-ups inside threads the bot already owns.
  if (!isDM && !isFollowUp) return;

  await handle({ text: event.text, channel: event.channel, threadId, say, client });
});

(async () => {
  await app.start();
  const auth = await app.client.auth.test();
  selfUserId = auth.user_id;
  // If the cronjobs module is also installed, auto-start its scheduler in this
  // same process so scheduled messages fire even when only the Slack bot runs.
  // Best-effort: no-op if scheduler.js isn't present.
  try {
    require("./scheduler.js").startScheduler();
  } catch (_) {}
  console.log(`⚡️ Twin Slack bot is running as @${auth.user} (${selfUserId})`);
  console.log(`   twin dir: ${TWIN_DIR}`);
})();
