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
# TERMINAL_TIMEOUT deliberately absent. It was 60 here, from the installer,
# while config.yaml carried a reasoned 180 — and config wins, because
# `terminal_tool.py:606` bridges an explicit `terminal` section with
# override=True. Two files disagreeing about one number, with no way to tell
# from either which one the agent obeys, is worse than one file owning it.
VISION_TOOLS_DEBUG=false
WEB_TOOLS_DEBUG=false

# The model key. config.yaml says `api_key: ${OMLX_API_KEY}`, and a gateway
# resolves that against THIS file, not the shell -- which is why the first
# Telegram question came back "HTTP 401: Invalid API key" from oMLX.
OMLX_API_KEY={{ op://Infra/oMLX/api_key }}

# Telegram. moria's bot only: dungeon's Hermes is reached over Slack and email,
# not Telegram, so this token (freed when the toolbox's own bot was deleted) is
# uncontended. Hermes reads TELEGRAM_ALLOWED_USERS, not the
# TELEGRAM_ALLOWED_CHAT_IDS our bot used -- same 1Password field, the name the
# tool actually reads. Without it, anyone who finds the bot can drive it.
TELEGRAM_BOT_TOKEN={{ op://Infra/Telegram/bot_token }}
TELEGRAM_ALLOWED_USERS={{ op://Infra/Telegram/allowed_chat_ids }}
TELEGRAM_HOME_CHANNEL={{ op://Infra/Telegram/chat_id }}

# DELIBERATELY ABSENT, each because something else already owns it.
#
# SLACK — OFF ON PURPOSE. Uncomment the two lines to turn it back on, and read
#   this first. `Infra/SlackBot` is Old Gregg's, and home-lab/hermes/README.md
#   is explicit that "there is no Hermes Slack app": Old Gregg (`roger slack` on
#   dungeon) holds the one Socket Mode connection and relays
#   `@Old Gregg hermes <question>`. Slack load-balances events across
#   connections sharing an app token, so a second consumer does not add a
#   listener, it steals a random share of Old Gregg's messages. Turning this on
#   means giving moria its OWN Slack app, not reusing these tokens.
#
# SLACK_BOT_TOKEN={{ op://Infra/SlackBot/bot_token }}
# SLACK_APP_TOKEN={{ op://Infra/SlackBot/app_token }}
#
# EMAIL_* — grehgpi@gmail.com is dungeon's Hermes inbox. Two IMAP pollers on one
#   mailbox race for the same mail.
#
# HASS_TOKEN — home-lab/hermes/README.md §8: the ha_* toolset "is deliberately
#   not enabled, and the token is not named HASS_TOKEN because that name would
#   enable it", because HA has no per-entity permissions and the locks are S2
#   Authenticated. Read-only is the whole design. `hass_token_pi_harness` is
#   also NOT read-only -- a POST to a bogus service returns 400, not 401, so it
#   gets past auth and can call services. Giving moria's bots HASS_TOKEN would
#   hand a local 35B `ha_call_service`. If moria needs HA, it wants its own
#   token from the read-only `hermes` user, and probably a read-only script
#   rather than the toolset.

# tirith, the bundled security scanner, never downloaded on this host
# (~/.hermes/.tirith-install-failed reads "download_failed"), so every scan
# fails and trips a circuit breaker -- four failures inside one Telegram
# question. Off until it is actually installed.
TIRITH_ENABLED=false
