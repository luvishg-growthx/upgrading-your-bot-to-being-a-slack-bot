# Plan of action — upgrade this twin into a Slack bot

**Audience: the coding agent (Claude Code, Codex, or any similar agent) doing the work.** These files are ready-made — integrate them as-is; don't rebuild the feature.
This is the ordered execution plan. The full source + token setup lives in the
guide — open it and copy code from it:

- `guide for implementing slack.md`

Work top to bottom. Don't skip steps. Each step has a ✅ done-check.

---

## Goal
Turn the user's existing terminal twin (`twin.js`, which dispatches
`claude -p`) **into a Slack bot, in place** — same brain, new face. End state:
one bot file, no leftover terminal twin, replies posting into Slack threads in
the twin's voice, **plus** the twin can send / edit / delete Slack messages on
its own (Step 8).

## Preconditions (verify first)
- [ ] You are inside the user's twin project (a `CLAUDE.md` / persona is present).
- [ ] `claude --version` works (Claude Code installed + logged in). If not, stop
      and tell the user to install/login first.
- [ ] An existing terminal twin file exists. If none, stop — this plan *upgrades*
      one; it doesn't invent a twin.

---

## Steps

### 1. Confirm it's a Node.js project
- [ ] Node.js if `package.json` / `*.js` (twin usually `twin.js`). This module is
      for Node.js twins.
- ✅ Done when: you've confirmed it's a Node.js project.

### 2. Read the existing twin's brain
- [ ] Open the terminal twin file. Record its `claude -p` invocation: working
      directory, session flags (`--session-id`/`--resume`), and any extra flags
      (`--allowedTools`, `--model`, etc.).
- ✅ Done when: you can list the exact flags the current twin passes.

### 3. Write the bot file (upgrade in place)
- [ ] Create `slack-bot.js` in the project **root**, using the code from the guide.
- [ ] Merge in the custom flags from Step 2 so the Slack twin behaves identically
      to the terminal one.
- [ ] Confirm `TWIN_DIR` resolves to the project root (where `CLAUDE.md` lives).
- ✅ Done when: the bot file exists and contains the user's brain logic.

### 4. Remove the old terminal twin
- [ ] Delete `twin.js` (or rename to `*.bak` if the user wants a
      backup). Update any `package.json`/run script that pointed at it.
- ✅ Done when: only the new bot file remains as the app entry point.

### 5. Install dependencies
- [ ] `npm install @slack/bolt dotenv`
- ✅ Done when: deps install without error.

### 6. Slack app + tokens (USER does this — you can't)
- [ ] Print the Slack-app steps from the guide (create app → Socket Mode →
      App-Level Token `connections:write` → bot scopes → event subscriptions →
      install → bot token → `/invite`).
- [ ] Wait for the user to paste back `SLACK_BOT_TOKEN` (xoxb-) and
      `SLACK_APP_TOKEN` (xapp-).
- [ ] Write them into `.env`; ensure `.env` is git-ignored.
- ✅ Done when: `.env` has both tokens and is ignored by git.

### 7. Run & verify
- [ ] Start the bot from the project root (`node slack-bot.js`).
- [ ] Confirm the startup log prints the bot identity + twin dir.
- [ ] In Slack, `@mention` the bot; confirm it reacts 👀 and replies in-thread in
      the twin's voice; confirm a follow-up in that thread works without a mention.
- ✅ Done when: a real Slack message gets a correct in-voice reply.

### 8. Outbound actions — send / edit / delete messages
- [ ] Create `slack-actions.js` (from the guide's Step 6) in
      the project root — a CLI for `send` / `edit` / `delete` / `list`.
- [ ] Create `.claude/skills/slack-message/SKILL.md` (from the guide) so the twin
      knows it can act on Slack and calls the CLI via Bash.
- [ ] No new scopes needed: `chat:write` covers send/edit/delete of the bot's own
      messages; `*:history` covers `list` (both already added in Step 6 tokens).
- ✅ Done when: `node slack-actions.js send <channel> "test"` posts a message and
      prints its ts (and `delete`/`edit` work on it).

### 9. Report
- [ ] Give the user a 3-line summary: twin upgraded → bot file, send/edit/delete
      added, and the exact start command.

---

## Guardrails (hold throughout)
- Upgrade in place — never leave two `claude -p` dispatchers behind.
- Preserve the brain (flags + working dir) so replies match the terminal twin.
- Don't modify `CLAUDE.md` / persona — the voice stays the user's.
- Never print or commit token values.
