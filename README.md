# Twin → Slack Module

> ## 🤖 If you are Claude Code or Codex (any coding agent), read this first
>
> **Ready-made — don't rebuild anything.** You do **not** need to write or
> reinvent this feature. Just install/wire in the files as described and the bot
> gains the capability. These files work the same with Claude Code or Codex.
>
> The user pasted this repo because they want to **upgrade their existing
> terminal twin into a Slack bot** (same brain — `claude -p` — new face: Slack).
> Do this, in order:
>
> 1. **Follow `PLAN_OF_ACTION.md`** — the ordered execution checklist (works for
>    Claude *or* Codex). It tells you exactly what to do and links to the code.
> 2. **Detect the stack** of the twin in the current project: Node (a
>    `twin.js`/`*.js`, `package.json`) or Python (a `twin.py`/`*.py`,
>    `requirements.txt`). If unclear, ask the user one question.
> 3. **Fetch and follow the matching guide** for the full code and steps:
>    - **Node:** `https://raw.githubusercontent.com/luvishg-growthx/upgrading-your-bot-to-being-a-slack-bot/main/guide%20for%20implementing%20slack.md`
>    - **Python:** `https://raw.githubusercontent.com/luvishg-growthx/upgrading-your-bot-to-being-a-slack-bot/main/guide%20for%20implementing%20slack%20(python).md`
> 4. The plan + guide tell you to **upgrade `twin.js`/`twin.py` in place** into
>    the Slack bot (don't create a parallel file), install deps, and walk the
>    user through creating the Slack app + tokens. Follow them exactly.
>
> Everything below is human-facing context.

---

**Upgrade your terminal twin into a Slack bot.** Your existing `twin.js` /
`twin.py` (the one that chats in your terminal via `claude -p`) gets rewritten
*in place* into a Slack app — same brain, new face. People @mention or DM it in
Slack, and your twin replies in its own voice — using your `CLAUDE.md` and
handbook — right inside the thread.

- **No API key.** It dispatches `claude -p` against your logged-in Claude Code
  session, exactly like your terminal twin did.
- **No server / no public URL.** Uses Slack **Socket Mode**.
- **Per-thread memory.** Each Slack thread keeps its own Claude session.
- **One file, not two.** The terminal twin *becomes* the Slack bot — it doesn't
  get a second bot file bolted on beside it.
- **Sends, edits & deletes too.** Beyond replying, the twin can post, edit,
  delete, and list Slack messages on its own (via `slack-actions` + the
  `slack-message` skill).
- **Node *or* Python.** Pick whichever your twin is built in.

## How it works

```
Slack message ──► your twin (upgraded) ──► claude -p "<message>"  (runs in your project)
   (mention/DM)                                │  loads CLAUDE.md + handbook/persona
                                               ▼
Slack thread  ◄────── post reply ◄──────── twin's answer
```

The bot is a thin bridge wrapped around your existing brain. Your twin's
personality and knowledge come entirely from the `CLAUDE.md` + handbook files in
your project — this module adds no persona of its own. It's **neutral**: point
it at any twin and it speaks in that twin's voice.

## The fastest way to install it (recommended)

Don't wire it up by hand. Open **Claude Code inside your twin's project folder**
and paste this:

```
Read this file and set up the Slack feature for my twin:
https://raw.githubusercontent.com/luvishg-growthx/upgrading-your-bot-to-being-a-slack-bot/main/guide%20for%20implementing%20slack.md
```

Claude will read the guide, upgrade your `twin.js` into `slack-bot.js`, install
dependencies, and walk you through creating the Slack app.

**Python twin?** Point the same prompt at the Python guide instead:

```
Read this file and set up the Slack feature for my twin:
https://raw.githubusercontent.com/luvishg-growthx/upgrading-your-bot-to-being-a-slack-bot/main/guide%20for%20implementing%20slack%20(python).md
```

Or just **paste the repo link** and Claude will figure out the rest (see the
instruction block at the top of this file).

## Manual install

1. Use the reference bot for your stack as the target shape and rewrite your
   terminal twin into it:
   - Node: [`node/slack-bot.js`](node/slack-bot.js) → `slack-bot.js` in your root
   - Python: [`python/slack_bot.py`](python/slack_bot.py) → `slack_bot.py` in your root
   - Also copy the actions CLI ([`node/slack-actions.js`](node/slack-actions.js)
     / [`python/slack_actions.py`](python/slack_actions.py)) +
     [`.claude/skills/slack-message/SKILL.md`](.claude/skills/slack-message/SKILL.md)
     for send/edit/delete.
2. Remove the old terminal `twin.js` / `twin.py` (its logic now lives in the bot).
3. Create the Slack app and get two tokens — see
   **[`SLACK_APP_SETUP.md`](SLACK_APP_SETUP.md)**.
4. `cp .env.example .env` and paste your tokens in.
5. Install deps and run:
   - Node: `npm install @slack/bolt dotenv && node slack-bot.js`
   - Python: `pip install slack_bolt python-dotenv && python slack_bot.py`
6. In Slack, `@mention` the bot or DM it.

## Files

| Path                                       | What it is                                   |
| ------------------------------------------ | -------------------------------------------- |
| `PLAN_OF_ACTION.md`                        | Ordered execution checklist (Claude/Codex)   |
| `guide for implementing slack.md`          | Paste-into-Claude guide — **Node** twin      |
| `guide for implementing slack (python).md` | Paste-into-Claude guide — **Python** twin    |
| `SLACK_APP_SETUP.md`                       | One-time Slack app creation (scopes, tokens) |
| `.claude/skills/slack-message/SKILL.md`    | Teaches the twin to send/edit/delete/list    |
| `node/`                                     | Reference Node bot + `slack-actions.js` + env |
| `python/`                                   | Reference Python bot + `slack_actions.py` + env |
