# ~/.zshenv — read by EVERY zsh invocation: login or not, interactive or not.
#
# Why this file exists
# ──────────────────────────────────────────────────────────────────────────────
# Homebrew's installer writes `eval "$(brew shellenv)"` into ~/.zprofile, and
# zsh reads .zprofile only for *login* shells. A non-login, non-interactive
# shell — exactly what `ssh <host> '<cmd>'` runs — never sources it, so
# /opt/homebrew/bin is absent and remote commands die with
#
#   zsh:1: command not found: just
#   zsh:1: command not found: op
#
# even though both are installed. .zshenv is the only startup file zsh reads in
# that context, so the PATH entry has to live here.
#
# PATH is set directly instead of via `brew shellenv` because this file is
# sourced by every zsh process, including short-lived ones spawned by scripts,
# and forking `brew` each time is measurable overhead. ~/.zprofile still runs
# the full shellenv on login, so interactive sessions keep HOMEBREW_PREFIX,
# HOMEBREW_CELLAR, MANPATH, and friends exactly as before.
#
# Portable: the guard makes this a no-op on Linux hosts, where /opt/homebrew
# does not exist — consistent with dot/README.md's "portable base" philosophy.

if [[ -d /opt/homebrew/bin && ":$PATH:" != *":/opt/homebrew/bin:"* ]]; then
  export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
fi
