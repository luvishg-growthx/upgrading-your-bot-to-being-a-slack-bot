# Plan of action — upgrade this twin into a Slack bot

**Audience: the coding agent (Claude Code, Codex, or similar) doing the work.**
This is the ordered execution plan. The full source + token setup lives in the
guides — open the one for the detected stack and copy code from it:

- Node: `guide for implementing slack.md`
- Python: `guide for implementing slack (python).md`

Work top to bottom. Don't skip steps. Each step has a ✅ done-check.

---

## Goal
Turn the user's existing terminal twin (`twin.js` / `twin.py`, which dispatches
`claude -p`) **into a Slack bot, in place** — same brain, new face. End state:
one bot file, no leftover terminal twin, replies posting into Slack threads in
the twin's voice.

## Preconditions (verify first)
- [ ] You are inside the user's twin project (a `CLAUDE.md` / persona is present).
- [ ] `claude --version` works (Claude Code installed + logged in). If not, stop
      and tell the user to install/login first.
- [ ] An existing terminal twin file exists. If none, stop — this plan *upgrades*
      one; it doesn't invent a twin.

---

## Steps

### 1. Detect the stack
- [ ] Node if `package.json` / `*.js` (twin usually `twin.js`).
- [ ] Python if `requirements.txt`/`pyproject.toml` / `*.py` (twin usually `twin.py`).
- [ ] If ambiguous, ask the user once. Announce the detected stack.
- ✅ Done when: you've stated "Detected: Node" or "Detected: Python".

### 2. Read the existing twin's brain
- [ ] Open the terminal twin file. Record its `claude -p` invocation: working
      directory, session flags (`--session-id`/`--resume`), and any extra flags
      (`--allowedTools`, `--model`, etc.).
- ✅ Done when: you can list the exact flags the current twin passes.

### 3. Write the bot file (upgrade in place)
- [ ] Create `slack-bot.js` (Node) or `slack_bot.py` (Python) in the project
      **root**, using the code from the matching guide.
- [ ] Merge in the custom flags from Step 2 so the Slack twin behaves identically
      to the terminal one.
- [ ] Confirm `TWIN_DIR` resolves to the project root (where `CLAUDE.md` lives).
- ✅ Done when: the bot file exists and contains the user's brain logic.

### 4. Remove the old terminal twin
- [ ] Delete `twin.js` / `twin.py` (or rename to `*.bak` if the user wants a
      backup). Update any `package.json`/run script that pointed at it.
- ✅ Done when: only the new bot file remains as the app entry point.

### 5. Install dependencies
- [ ] Node: `npm install @slack/bolt dotenv`
- [ ] Python: `pip install slack_bolt python-dotenv` (and add to `requirements.txt`)
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
- [ ] Start the bot from the project root (`node slack-bot.js` / `python slack_bot.py`).
- [ ] Confirm the startup log prints the bot identity + twin dir.
- [ ] In Slack, `@mention` the bot; confirm it reacts 👀 and replies in-thread in
      the twin's voice; confirm a follow-up in that thread works without a mention.
- ✅ Done when: a real Slack message gets a correct in-voice reply.

### 8. Report
- [ ] Give the user a 3-line summary: twin upgraded → bot file, what was added,
      and the exact start command.

---

## Guardrails (hold throughout)
- Upgrade in place — never leave two `claude -p` dispatchers behind.
- Preserve the brain (flags + working dir) so replies match the terminal twin.
- Don't modify `CLAUDE.md` / persona — the voice stays the user's.
- Never print or commit token values.
