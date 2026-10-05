#!/usr/bin/env bash
# FluidVoice activation: hotkey seed, dictionary, managed settings, Handy, fluidvoice-ax.
#
# Runs as the user from postActivation; fluidvoice.nix passes every value in the
# environment, so tests/test_fluidvoice_activate.py can run it against a scratch
# defaults domain. Rationale for each step: nixos/CLAUDE.md → "FluidVoice".
set -eu

: "${DOMAIN:?}" "${APP:?}" "${HANDY_STORE:?}" "${OMLX_SETTINGS:?}"
: "${SEED_DICTATION:?}" "${SEED_DICTATION_LEGACY:?}" "${SEED_COMMAND:?}" "${SEED_WRITE:?}"
: "${DICTIONARY:?}" "${PROVIDER:?}" "${STRINGS:?}"
AX_SOURCE="${AX_SOURCE:-}"
AX_DIR="${AX_DIR:-}"
LAUNCH="${LAUNCH:-}"

hex() { printf '%s' "$1" | xxd -p | tr -d '\n'; }
# Empty when the key is absent.
read_data() {
  defaults export "$DOMAIN" - | plutil -extract "$1" raw -o - - 2>/dev/null | base64 -d
}

gone() {
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    pgrep -xq "$1" || return 0
    sleep "${QUIT_POLL:-1}"
  done
  return 1
}
# Polite first; a wedged app ignores quit.
quit_app() {
  pgrep -xq "$2" || return 0
  osascript -e 'with timeout of 10 seconds' -e "tell application \"$1\" to quit" -e 'end timeout' || true
  gone "$2" && return 0
  echo "fluidvoice: $1 ignored quit; sending SIGTERM" >&2
  pkill -x "$2" || true
  gone "$2" && return 0
  echo "fluidvoice: $1 did not quit" >&2
  return 1
}

if [ ! -d "$APP" ]; then
  echo "fluidvoice: $APP is not installed, skipping"
  exit 0
fi

if ! defaults read "$DOMAIN" PrimaryDictationShortcuts >/dev/null 2>&1; then
  # A running app ignores new defaults.
  if quit_app FluidVoice FluidVoice; then
    echo "fluidvoice: seeding hotkeys (Caps Lock = dictate, +Shift = command, +Option = write)"
    # Short press toggles, long hold talks.
    defaults write "$DOMAIN" HotkeyMode -string automatic
    defaults write "$DOMAIN" PressAndHoldMode -bool false
    defaults write "$DOMAIN" HotkeyShortcutKey -data "$(hex "$SEED_DICTATION_LEGACY")"
    defaults write "$DOMAIN" CommandModeHotkeyShortcut -data "$(hex "$SEED_COMMAND")"
    defaults write "$DOMAIN" CommandModeShortcutEnabled -bool true
    defaults write "$DOMAIN" CommandModeConfirmBeforeExecute -bool true
    # Streaming drops parallel tool calls.
    defaults write "$DOMAIN" EnableAIStreaming -bool false
    defaults write "$DOMAIN" RewriteModeHotkeyShortcut -data "$(hex "$SEED_WRITE")"
    defaults write "$DOMAIN" RewriteModeShortcutEnabled -bool true
    defaults write "$DOMAIN" ShowMainWindowAtLoginLaunch -bool false
    defaults write "$DOMAIN" ShowInDock -bool false
    defaults write "$DOMAIN" OnboardingCompleted -bool false
    # Last: marks the seed done.
    defaults write "$DOMAIN" PrimaryDictationShortcuts -data "$(hex "$SEED_DICTATION")"
  else
    echo "fluidvoice: hotkey seed skipped" >&2
  fi
fi

# Add-only by replacement, so in-app edits stay.
merge_dictionary() {
  CURRENT="$(read_data CustomDictionaryEntries)"
  N="$(printf '%s' "$DICTIONARY" | jq length)"
  # shellcheck disable=SC2046 # one uuid per word
  printf '%s' "${CURRENT:-"[]"}" | jq -c --argjson want "$DICTIONARY" '
    . as $have
    | [$want[] | select(.replacement as $r | $have | all(.replacement != $r))]
    | if length == 0 then empty
      else $have + [to_entries[] | .value + {id: $ARGS.positional[.key]}] end
  ' --args $(for _ in $(seq "$N"); do uuidgen; done)
}
if [ -n "$(merge_dictionary)" ]; then
  if quit_app FluidVoice FluidVoice && MERGED="$(merge_dictionary)" && [ -n "$MERGED" ]; then
    echo "fluidvoice: adding Custom Dictionary entries"
    defaults write "$DOMAIN" CustomDictionaryEntries -data "$(hex "$MERGED")"
  else
    echo "fluidvoice: dictionary entries skipped" >&2
  fi
fi

# Enforced every deploy; in-app edits revert.
KEY="$(jq -r '.auth.api_key // empty' "$OMLX_SETTINGS" 2>/dev/null || true)"
BASE_URL="$(printf '%s' "$PROVIDER" | jq -r .baseURL)"
PROVIDER_ID="$(printf '%s' "$PROVIDER" | jq -r .id)"
# Sorted by id: in-app additions don't reorder.
providers() {
  CURRENT="$(read_data SavedProviders)"
  printf '%s' "${CURRENT:-"[]"}" | jq -cS --arg key "$1" --argjson p "$PROVIDER" \
    '[.[] | select(.id != $p.id and .baseURL != $p.baseURL)] + [$p + {name: "oMLX", apiKey: $key}] | sort_by(.id)'
}
fingerprints() {
  CURRENT="$(read_data VerifiedProviderFingerprints)"
  FP="$(printf '%s' "$BASE_URL|$KEY" | shasum -a 256 | cut -d' ' -f1)"
  printf '%s' "${CURRENT:-"{}"}" | jq -cS --arg k "custom:$PROVIDER_ID" --arg fp "$FP" '.[$k] = $fp'
}
# Its own model would outrank Fluid-1.
prompt_configs() {
  CURRENT="$(read_data DictationPromptConfigurations)"
  printf '%s' "${CURRENT:-"{}"}" | jq -cS \
    'if has("__default__") then .__default__ += {providerID: "", modelName: ""} else . end'
}
# Command Mode reads only this list (1.6.9).
listed_models() {
  defaults export "$DOMAIN" - | plutil -extract "AvailableModelsByProvider.custom:$PROVIDER_ID" json -o - - 2>/dev/null || echo '[]'
}
models_listed() {
  listed_models | jq -e --argjson p "$PROVIDER" '($p.models - .) == []' >/dev/null 2>&1
}
# Union, so an in-app refresh is kept.
models_xml() {
  listed_models | jq -r --argjson p "$PROVIDER" \
    '(. + $p.models) | reduce .[] as $m ([]; if index([$m]) then . else . + [$m] end)
     | "<array>" + (map("<string>\(@html)</string>") | join("")) + "</array>"'
}
# Fluid-1 refuses Write and Command Mode.
BOOLS="RewriteModeLinkedToGlobal CommandModeLinkedToGlobal"

drifted() {
  for pair in $STRINGS; do
    [ "$(defaults read "$DOMAIN" "${pair%%=*}" 2>/dev/null)" = "${pair#*=}" ] || return 0
  done
  for k in $BOOLS; do
    [ "$(defaults read "$DOMAIN" "$k" 2>/dev/null)" = 0 ] || return 0
  done
  [ "$(read_data SavedProviders | jq -cS 'sort_by(.id)' 2>/dev/null)" = "$(providers "" 2>/dev/null)" ] || return 0
  [ "$(read_data DictationPromptConfigurations | jq -cS . 2>/dev/null)" = "$(prompt_configs 2>/dev/null)" ] || return 0
  models_listed || return 0
  [ -z "$KEY" ] || [ "$(read_data VerifiedProviderFingerprints | jq -cS . 2>/dev/null)" = "$(fingerprints 2>/dev/null)" ] || return 0
  return 1
}

# Compute first: a bad value writes nothing.
apply_settings() {
  quit_app FluidVoice FluidVoice || return 1
  P="$(providers "$KEY")" && [ -n "$P" ] || return 1
  C="$(prompt_configs)" && [ -n "$C" ] || return 1
  M="$(models_xml)" && [ -n "$M" ] || return 1
  F=""
  if [ -n "$KEY" ]; then
    F="$(fingerprints)" && [ -n "$F" ] || return 1
  fi
  echo "fluidvoice: applying managed settings (Fluid-1 dictation, oMLX for Write and Command Mode)"
  for pair in $STRINGS; do
    defaults write "$DOMAIN" "${pair%%=*}" -string "${pair#*=}"
  done
  for k in $BOOLS; do
    defaults write "$DOMAIN" "$k" -bool false
  done
  # The app moves apiKey into Keychain.
  defaults write "$DOMAIN" SavedProviders -data "$(hex "$P")"
  defaults write "$DOMAIN" DictationPromptConfigurations -data "$(hex "$C")"
  defaults write "$DOMAIN" AvailableModelsByProvider -dict-add "custom:$PROVIDER_ID" "$M"
  [ -z "$F" ] || defaults write "$DOMAIN" VerifiedProviderFingerprints -data "$(hex "$F")"
}

if [ -z "$KEY" ]; then
  echo "fluidvoice: no oMLX key in $OMLX_SETTINGS (run just secrets); Write and Command Mode stay unverified" >&2
fi
# Onboarding writes these too; don't fight it.
if [ "$(defaults read "$DOMAIN" OnboardingCompleted 2>/dev/null || echo 0)" != 1 ]; then
  echo "fluidvoice: onboarding unfinished; managed settings apply on the next deploy"
elif drifted; then
  apply_settings || echo "fluidvoice: managed settings skipped; nothing written" >&2
fi

# Best effort. `if` disables set -e here.
if [ -f "$HANDY_STORE" ] && ! (
  UPDATED="$(jq '
    .settings.autostart_enabled = false
    | .settings.bindings.transcribe |=
        (if (.current_binding // "" | test("f18")) then .current_binding = .default_binding else . end)
  ' "$HANDY_STORE")" || exit 1
  CURRENT="$(jq . "$HANDY_STORE")" || exit 1
  [ "$UPDATED" != "$CURRENT" ] || exit 0
  echo "fluidvoice: taking F18 and launch-at-login from Handy"
  # Handy rewrites its store on quit.
  quit_app Handy handy || exit 1
  printf '%s\n' "$UPDATED" > "$HANDY_STORE" || exit 1
); then
  echo "fluidvoice: could not update Handy's settings; it may still own F18" >&2
fi

# Rebuild only when the source changes.
if [ -n "$AX_SOURCE" ] && [ "$(cat "$AX_DIR/source" 2>/dev/null || true)" != "$AX_SOURCE" ]; then
  if xcode-select -p >/dev/null 2>&1; then
    mkdir -p "$AX_DIR"
    if swiftc -O "$AX_SOURCE" -o "$AX_DIR/fluidvoice-ax"; then
      printf '%s' "$AX_SOURCE" > "$AX_DIR/source"
      echo "fluidvoice: built fluidvoice-ax; re-allow it under Accessibility (see nixos/CLAUDE.md)"
      launchctl kickstart -k "gui/$(id -u)/org.nixos.fluidvoice-ax" >/dev/null 2>&1 || true
    else
      echo "fluidvoice: fluidvoice-ax did not build; Write Mode stays blind in Electron apps" >&2
    fi
  else
    echo "fluidvoice: no Command Line Tools (xcode-select --install); fluidvoice-ax not built" >&2
  fi
fi

[ -z "$LAUNCH" ] || exec "$LAUNCH"
