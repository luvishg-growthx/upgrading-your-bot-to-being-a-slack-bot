#!/usr/bin/env node
// slack-actions.js — let your agent SEND, EDIT, DELETE, and LIST Slack messages.
//
// The Slack bot (slack-bot.js) *replies* to people. This CLI gives your twin the
// other half: acting on Slack on its own. Your agent calls it via Bash, e.g.
// when you say "post 'standup in 5' to #general" or "delete that last message".
//
// Uses the same SLACK_BOT_TOKEN from your .env. Note: Slack only lets a bot
// edit/delete messages IT posted.
//
// Usage:
//   node slack-actions.js send   <channel> <text...>      → posts, prints the ts
//   node slack-actions.js edit   <channel> <ts> <text...> → updates that message
//   node slack-actions.js delete <channel> <ts>           → deletes that message
//   node slack-actions.js list   <channel> [limit]        → recent msgs (ts | user | text)
//
// <channel> is a channel ID (e.g. C0123ABC) or a user ID (e.g. U0123ABC) for a DM.

const path = require("path");
require("dotenv").config({ path: path.join(__dirname, ".env") });

const TOKEN = process.env.SLACK_BOT_TOKEN;
if (!TOKEN) {
  console.error("Missing SLACK_BOT_TOKEN (set it in .env).");
  process.exit(1);
}

async function slack(method, payload) {
  const res = await fetch(`https://slack.com/api/${method}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      Authorization: `Bearer ${TOKEN}`,
    },
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
      console.log(`sent ts=${r.ts}`); // capture this ts to edit/delete later
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

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
