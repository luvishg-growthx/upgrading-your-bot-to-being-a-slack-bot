# Create your Slack app (one-time, ~3 minutes)

This bot uses **Socket Mode**, so you do **not** need a public URL, ngrok, or a
server. You just need two tokens. Do this once.

## 1. Create the app

1. Go to <https://api.slack.com/apps> → **Create New App** → **From scratch**.
2. Name it (e.g. "My Twin") and pick your workspace.

## 2. Turn on Socket Mode

1. Left sidebar → **Socket Mode** → toggle **Enable Socket Mode** on.
2. When prompted, create an **App-Level Token**:
   - Name it anything (e.g. `socket`).
   - Add the scope **`connections:write`**.
   - Click **Generate**, then copy the token. It starts with **`xapp-`**.
   - This is your **`SLACK_APP_TOKEN`**.

## 3. Add bot permissions (scopes)

Left sidebar → **OAuth & Permissions** → **Scopes** → **Bot Token Scopes**, add:

| Scope               | Why                                            |
| ------------------- | ---------------------------------------------- |
| `app_mentions:read` | see when someone @mentions the bot             |
| `chat:write`        | post replies                                   |
| `im:history`        | read direct messages sent to the bot           |
| `channels:history`  | read thread replies in public channels         |
| `groups:history`    | read thread replies in private channels        |
| `reactions:write`   | add the 👀 "on it" reaction (optional)         |

## 4. Subscribe to events

Left sidebar → **Event Subscriptions** → toggle on. Under
**Subscribe to bot events**, add:

- `app_mention`
- `message.im`     (DMs)
- `message.channels`  (public channel threads)
- `message.groups`    (private channel threads)

(With Socket Mode on, you do **not** need a Request URL.)

## 5. Install the app & get the bot token

1. Left sidebar → **Install App** → **Install to Workspace** → **Allow**.
2. Copy the **Bot User OAuth Token**. It starts with **`xoxb-`**.
   - This is your **`SLACK_BOT_TOKEN`**.

## 6. Invite the bot to a channel

In Slack, open a channel and type:

```
/invite @YourBotName
```

(DMs work without an invite.)

## 7. Put the tokens in `.env`

Paste both tokens into your `.env` file:

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

That's it. Start the bot, then `@mention` it in the channel or DM it.

> If you change scopes later, you must **reinstall the app** (step 5) for the
> new permissions to take effect.
