# FluidVoice: Caps Lock hold dictates, Shift+hold commands.
# Rationale: nixos/CLAUDE.md → "FluidVoice".
{
  config,
  lib,
  pkgs,
  vars,
  ...
}: let
  cfg = config.services.fluidvoice;
  user = vars.user.name;
  userArg = lib.escapeShellArg user;

  # NSEvent.ModifierFlags.function
  fn = 8388608;
  shortcut = keyCode: modifierFlagsRawValue: {
    kind = "keyboard";
    inherit keyCode modifierFlagsRawValue;
  };
  # kVK_F18 and kVK_F19
  f18 = 79;
  f19 = 80;

  dictation = builtins.toJSON [(shortcut f18 fn) (shortcut f18 0)];
  dictationLegacy = builtins.toJSON (shortcut f18 fn);
  command = builtins.toJSON (shortcut f19 fn);

  # Runs AS THE USER, from postActivation below.
  activateScript = pkgs.writeShellScript "fluidvoice-activate" ''
    set -eu

    DOMAIN="com.FluidApp.app"
    APP="/Applications/FluidVoice.app"
    HANDY_STORE="/Users/${user}/Library/Application Support/com.pais.handy/settings_store.json"

    hex() { printf '%s' "$1" | /usr/bin/xxd -p | /usr/bin/tr -d '\n'; }

    if [ ! -d "$APP" ]; then
      echo "fluidvoice: $APP is not installed, skipping"
      exit 0
    fi

    # Handy rewrites its store on quit.
    if [ -f "$HANDY_STORE" ]; then
      UPDATED="$(${pkgs.jq}/bin/jq '
        .settings.autostart_enabled = false
        | .settings.bindings.transcribe |=
            (if (.current_binding // "" | test("f18")) then .current_binding = .default_binding else . end)
      ' "$HANDY_STORE")"
      if [ "$UPDATED" != "$(${pkgs.jq}/bin/jq . "$HANDY_STORE")" ]; then
        echo "fluidvoice: taking F18 and launch-at-login from Handy"
        if /usr/bin/pgrep -xq handy; then
          /usr/bin/osascript -e 'quit app "Handy"'
          for _ in 1 2 3 4 5 6 7 8 9 10; do
            /usr/bin/pgrep -xq handy || break
            sleep 1
          done
        fi
        printf '%s\n' "$UPDATED" > "$HANDY_STORE"
      fi
    fi

    if /usr/bin/defaults read "$DOMAIN" PrimaryDictationShortcuts >/dev/null 2>&1; then
      if ! /usr/bin/pgrep -xq FluidVoice; then
        exec /usr/bin/open -g -j --env FLUID_SIMULATE_LOGIN_LAUNCH=1 -a "$APP"
      fi
      exit 0
    fi

    echo "fluidvoice: seeding hotkeys (Caps Lock hold = dictate, Shift+Caps Lock hold = command)"
    /usr/bin/defaults write "$DOMAIN" HotkeyMode -string hold
    /usr/bin/defaults write "$DOMAIN" PressAndHoldMode -bool true
    /usr/bin/defaults write "$DOMAIN" HotkeyShortcutKey -data "$(hex '${dictationLegacy}')"
    /usr/bin/defaults write "$DOMAIN" CommandModeHotkeyShortcut -data "$(hex '${command}')"
    /usr/bin/defaults write "$DOMAIN" CommandModeShortcutEnabled -bool true
    /usr/bin/defaults write "$DOMAIN" ShowMainWindowAtLoginLaunch -bool false
    /usr/bin/defaults write "$DOMAIN" ShowInDock -bool false
    /usr/bin/defaults write "$DOMAIN" OnboardingCompleted -bool false
    # Last: it is the marker that stops a re-seed.
    /usr/bin/defaults write "$DOMAIN" PrimaryDictationShortcuts -data "$(hex '${dictation}')"

    # Not silent on purpose: onboarding should show.
    exec /usr/bin/open -a "$APP"
  '';
in {
  options.services.fluidvoice.enable = lib.mkEnableOption ''
    FluidVoice on this Darwin host: the cask, a one-time hotkey seed, taking
    F18 and launch-at-login from Handy, and an `open -a` login agent
  '';

  config = lib.mkIf cfg.enable {
    homebrew.casks = ["fluidvoice"];

    # Setup failure must never fail the rebuild.
    system.activationScripts.postActivation.text = lib.mkAfter ''
      if ! launchctl asuser "$(id -u -- ${userArg})" sudo --user=${userArg} -- ${activateScript}; then
        echo "WARNING: FluidVoice setup did not finish (see above)." >&2
      fi
    '';

    launchd.user.agents.fluidvoice = {
      command = "/usr/bin/open -g -j --env FLUID_SIMULATE_LOGIN_LAUNCH=1 -a /Applications/FluidVoice.app";
      serviceConfig = {
        RunAtLoad = true;
        StandardOutPath = "/Users/${user}/Library/Logs/fluidvoice.log";
        StandardErrorPath = "/Users/${user}/Library/Logs/fluidvoice.log";
      };
    };
  };
}
