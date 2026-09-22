# Hermes' own environment, generated into ~/.hermes/.env by `just secrets`.
#
# Hermes reads THIS file, not the shell. The gateway runs as a launchd agent
# and inherits nothing from your interactive environment, so platform
# credentials have to live here rather than in nixos/secrets/.env.
#
# That difference already caused confusion once: .zshrc does `set -a; source
# nixos/secrets/.env`, which auto-exports SLACK_BOT_TOKEN and TELEGRAM_BOT_TOKEN
# into every shell, so `hermes gateway setup` reported Slack and Telegram as
# already configured while channel_directory.json still held no platforms at
# all. Credentials visible to the wizard are not credentials the gateway has.
#
# CAUTION: this file is generated, so `hermes config set` writes and anything
# the setup wizard stores in .env are overwritten on the next `just secrets`.
# Add such keys here instead. The eleven defaults below came from the installer
# and are reproduced verbatim so regenerating does not drop them.

BROWSER_INACTIVITY_TIMEOUT=120
BROWSER_SESSION_TIMEOUT=300
BROWSERBASE_ADVANCED_STEALTH=false
BROWSERBASE_PROXIES=true
IMAGE_TOOLS_DEBUG=false
MOA_TOOLS_DEBUG=false
TERMINAL_LIFETIME_SECONDS=300
TERMINAL_MODAL_IMAGE=nikolaik/python-nodejs:python3.11-nodejs20
TERMINAL_TIMEOUT=60
VISION_TOOLS_DEBUG=false
WEB_TOOLS_DEBUG=false

# Home Assistant. Setting HASS_TOKEN alone activates ha_list_entities,
# ha_get_state, ha_list_services and ha_call_service, and the gateway platform
# for state changes; no toolset needs enabling. HA runs on dungeon and this URL
# is reachable from moria over Tailscale — verified with
# `curl -H "Authorization: Bearer <token>" <url>/api/` returning 200.
#
# Reuses the token pi's harness already had (dot/pi/.pi/agent/homeassistant.json).
HASS_URL=https://home-assistant.grehg2.xyz
HASS_TOKEN={{ op://Infra/Hermes/hass_token_pi_harness }}

# Telegram. Hermes' allowlist variable is TELEGRAM_ALLOWED_USERS, NOT the
# TELEGRAM_ALLOWED_CHAT_IDS our deleted bot used — same 1Password field, the
# name the tool actually reads. Without an allowlist anyone who finds the bot
# can drive it.
TELEGRAM_BOT_TOKEN={{ op://Infra/Telegram/bot_token }}
TELEGRAM_ALLOWED_USERS={{ op://Infra/Telegram/allowed_chat_ids }}
TELEGRAM_HOME_CHANNEL={{ op://Infra/Telegram/chat_id }}

# Slack, over Socket Mode: outbound WebSocket, so no public endpoint and
# nothing to open on the firewall.
SLACK_BOT_TOKEN={{ op://Infra/SlackBot/bot_token }}
SLACK_APP_TOKEN={{ op://Infra/SlackBot/app_token }}

# Email, on a dedicated account — the docs are explicit that the agent gets
# full IMAP access to whatever inbox this points at, so it is not the personal
# one. EMAIL_ALLOWED_USERS is the access control: unlisted senders are ignored
# silently rather than refused, which is the right default for an address that
# will inevitably receive spam.
EMAIL_ADDRESS=grehgpi@gmail.com
EMAIL_PASSWORD={{ op://Infra/Hermes/gmail_app_password }}
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_ALLOWED_USERS=Gregory.Hilston@gmail.com
