---
name: slack-message
description: Send, edit, delete, or list Slack messages on the user's behalf. Trigger whenever the user asks to post/send a Slack message, edit/update a message already sent, delete/remove a message, or look up recent messages in a channel.
---

# Act on Slack (send / edit / delete / list)

The project ships a small CLI for outbound Slack actions. Use it via Bash. It
reads the bot token from the Slack module's `.env`. (Node: `slack-actions.js`;
Python: `slack_actions.py` — use whichever exists.)

> Slack only lets the bot **edit or delete messages it posted itself.**

## Commands

```
# Send — prints the message ts (timestamp). SAVE the ts if you may edit/delete it.
node slack-actions.js send   <channel> <text...>
python slack_actions.py send <channel> <text...>

# Edit a message the bot sent
node slack-actions.js edit   <channel> <ts> <new text...>

# Delete a message the bot sent
node slack-actions.js delete <channel> <ts>

# List recent messages (to find a ts to edit/delete) → "ts | user | text"
node slack-actions.js list   <channel> [limit]
```

`<channel>` is a channel ID (e.g. `C0123ABC`) or a user ID (e.g. `U0123ABC`) for
a DM.

## How to handle common requests

- **"Send X to <channel>"** → run `send`. Report back the ts you got.
- **"Edit / change that message to Y"** → if you already have the ts from a
  recent `send`, use it. Otherwise run `list <channel>` to find the bot's
  message, then `edit`.
- **"Delete that / remove my last message"** → run `list <channel>`, pick the
  bot's most recent message, then `delete <channel> <ts>`. If it's ambiguous
  which message they mean, confirm before deleting.
- **Needs a channel/user ID you don't have** → ask the user for it (or they can
  right-click the channel in Slack → "Copy link" — the ID is in the URL).

Keep the message wording in the agent's voice (see `CLAUDE.md` / `PERSONA.md`)
unless the user gave exact text to send.
