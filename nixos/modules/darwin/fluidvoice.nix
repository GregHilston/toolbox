# FluidVoice: Caps Lock dictates; modifiers pick modes.
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
  # kVK_F18, kVK_F19, kVK_F20
  f18 = 79;
  f19 = 80;
  f20 = 90;

  dictation = builtins.toJSON [(shortcut f18 fn) (shortcut f18 0)];
  dictationLegacy = builtins.toJSON (shortcut f18 fn);
  command = builtins.toJSON (shortcut f19 fn);
  # Measured on moria: F20 arrives without fn.
  write = builtins.toJSON (shortcut f20 0);

  # Shipped ids, read from the binary.
  fluid1 = "fluid-1";
  fluid1Prompt = "__FLUID_1__";

  # A fixed id, so every host matches.
  omlx = {
    id = "omlx";
    baseURL = "http://localhost:8000/v1";
    models = [lightModel "${lightModel}:lab"];
  };
  lightModel = "Qwen3.6-35B-A3B-4bit";

  # Jargon Parakeet and cleanup models mangle.
  dictionary = [
    {
      triggers = ["quinn" "quen" "kwen"];
      replacement = "Qwen";
    }
    {
      triggers = ["o mlx" "oh mlx"];
      replacement = "oMLX";
    }
    {
      triggers = ["one password"];
      replacement = "1Password";
    }
    {
      triggers = ["fluid voice"];
      replacement = "FluidVoice";
    }
  ];

  # A stable path: the Accessibility grant follows it.
  axDir = "/Users/${user}/Library/Application Support/fluidvoice-ax";
  axBin = "${axDir}/fluidvoice-ax";
  axSource = ./fluidvoice-ax.swift;

  # Unfinished onboarding must stay visible.
  launchScript = pkgs.writeShellScript "fluidvoice-launch" ''
    APP="/Applications/FluidVoice.app"
    if [ "$(/usr/bin/defaults read com.FluidApp.app OnboardingCompleted 2>/dev/null || echo 0)" != "1" ]; then
      exec /usr/bin/open -a "$APP"
    fi
    /usr/bin/pgrep -xq FluidVoice && exit 0
    # Not -j: a hidden app hides its overlay.
    exec /usr/bin/open -g --env FLUID_SIMULATE_LOGIN_LAUNCH=1 -a "$APP"
  '';

  # Runs AS THE USER, from postActivation below.
  activateScript = pkgs.writeShellScript "fluidvoice-activate" ''
    set -eu

    DOMAIN="com.FluidApp.app"
    APP="/Applications/FluidVoice.app"
    HANDY_STORE="/Users/${user}/Library/Application Support/com.pais.handy/settings_store.json"

    hex() { printf '%s' "$1" | /usr/bin/xxd -p | /usr/bin/tr -d '\n'; }
    # Empty when the key is absent.
    read_data() {
      /usr/bin/defaults export "$DOMAIN" - | /usr/bin/plutil -extract "$1" raw -o - - 2>/dev/null | /usr/bin/base64 -d
    }

    gone() {
      for _ in 1 2 3 4 5 6 7 8 9 10; do
        /usr/bin/pgrep -xq "$1" || return 0
        sleep 1
      done
      return 1
    }
    # Quit politely, then SIGTERM: a wedged app ignores quit.
    quit_app() {
      /usr/bin/pgrep -xq "$2" || return 0
      /usr/bin/osascript -e 'with timeout of 10 seconds' -e "tell application \"$1\" to quit" -e 'end timeout' || true
      gone "$2" && return 0
      echo "fluidvoice: $1 ignored quit; sending SIGTERM" >&2
      /usr/bin/pkill -x "$2" || true
      gone "$2" && return 0
      echo "fluidvoice: $1 did not quit" >&2
      return 1
    }

    if [ ! -d "$APP" ]; then
      echo "fluidvoice: $APP is not installed, skipping"
      exit 0
    fi

    if ! /usr/bin/defaults read "$DOMAIN" PrimaryDictationShortcuts >/dev/null 2>&1; then
      # A running app ignores new defaults.
      quit_app FluidVoice FluidVoice
      echo "fluidvoice: seeding hotkeys (Caps Lock = dictate, +Shift = command, +Option = write)"
      # Short press toggles, long hold talks.
      /usr/bin/defaults write "$DOMAIN" HotkeyMode -string automatic
      /usr/bin/defaults write "$DOMAIN" PressAndHoldMode -bool false
      /usr/bin/defaults write "$DOMAIN" HotkeyShortcutKey -data "$(hex '${dictationLegacy}')"
      /usr/bin/defaults write "$DOMAIN" CommandModeHotkeyShortcut -data "$(hex '${command}')"
      /usr/bin/defaults write "$DOMAIN" CommandModeShortcutEnabled -bool true
      /usr/bin/defaults write "$DOMAIN" CommandModeConfirmBeforeExecute -bool true
      # Streaming drops parallel tool calls.
      /usr/bin/defaults write "$DOMAIN" EnableAIStreaming -bool false
      /usr/bin/defaults write "$DOMAIN" RewriteModeHotkeyShortcut -data "$(hex '${write}')"
      /usr/bin/defaults write "$DOMAIN" RewriteModeShortcutEnabled -bool true
      /usr/bin/defaults write "$DOMAIN" ShowMainWindowAtLoginLaunch -bool false
      /usr/bin/defaults write "$DOMAIN" ShowInDock -bool false
      /usr/bin/defaults write "$DOMAIN" OnboardingCompleted -bool false
      # Last: marks the seed done.
      /usr/bin/defaults write "$DOMAIN" PrimaryDictationShortcuts -data "$(hex '${dictation}')"
    fi

    # Add-only by replacement, so in-app edits stay.
    merge_dictionary() {
      CURRENT="$(read_data CustomDictionaryEntries)"
      printf '%s' "''${CURRENT:-"[]"}" | ${pkgs.jq}/bin/jq -c --argjson want '${builtins.toJSON dictionary}' '
        . as $have
        | [$want[] | select(.replacement as $r | $have | all(.replacement != $r))]
        | if length == 0 then empty
          else $have + [to_entries[] | .value + {id: $ARGS.positional[.key]}] end
      ' --args $(for _ in $(/usr/bin/seq ${toString (builtins.length dictionary)}); do /usr/bin/uuidgen; done)
    }
    if [ -n "$(merge_dictionary)" ]; then
      quit_app FluidVoice FluidVoice
      MERGED="$(merge_dictionary)"
      if [ -n "$MERGED" ]; then
        echo "fluidvoice: adding Custom Dictionary entries"
        /usr/bin/defaults write "$DOMAIN" CustomDictionaryEntries -data "$(hex "$MERGED")"
      fi
    fi

    # Enforced every deploy; in-app edits revert.
    JQ=${pkgs.jq}/bin/jq
    KEY="$($JQ -r '.auth.api_key // empty' "/Users/${user}/.omlx/settings.json" 2>/dev/null || true)"
    providers() {
      CURRENT="$(read_data SavedProviders)"
      printf '%s' "''${CURRENT:-"[]"}" | $JQ -cS --arg key "$1" --argjson p '${builtins.toJSON omlx}' \
        '[.[] | select(.id != $p.id and .baseURL != $p.baseURL)] + [$p + {name: "oMLX", apiKey: $key}]'
    }
    fingerprints() {
      CURRENT="$(read_data VerifiedProviderFingerprints)"
      FP="$(printf '%s' "${omlx.baseURL}|$KEY" | /usr/bin/shasum -a 256 | /usr/bin/cut -d' ' -f1)"
      printf '%s' "''${CURRENT:-"{}"}" | $JQ -cS --arg fp "$FP" '.["custom:${omlx.id}"] = $fp'
    }
    # Its own model would outrank Fluid-1.
    prompt_configs() {
      CURRENT="$(read_data DictationPromptConfigurations)"
      printf '%s' "''${CURRENT:-"{}"}" | $JQ -cS \
        'if has("__default__") then .__default__ += {providerID: "", modelName: ""} else . end'
    }
    STRINGS="
    SelectedProviderID=${fluid1}
    SelectedDictationPromptID=${fluid1Prompt}
    RewriteModeSelectedProviderID=${omlx.id}
    RewriteModeSelectedModel=${lightModel}:lab
    CommandModeSelectedProviderID=${omlx.id}
    CommandModeSelectedModel=${lightModel}
    "
    # Fluid-1 refuses Write and Command Mode.
    BOOLS="RewriteModeLinkedToGlobal CommandModeLinkedToGlobal"

    drifted() {
      for pair in $STRINGS; do
        [ "$(/usr/bin/defaults read "$DOMAIN" "''${pair%%=*}" 2>/dev/null)" = "''${pair#*=}" ] || return 0
      done
      for k in $BOOLS; do
        [ "$(/usr/bin/defaults read "$DOMAIN" "$k" 2>/dev/null)" = 0 ] || return 0
      done
      [ "$(read_data SavedProviders | $JQ -cS . 2>/dev/null)" = "$(providers "")" ] || return 0
      [ "$(read_data DictationPromptConfigurations | $JQ -cS . 2>/dev/null)" = "$(prompt_configs)" ] || return 0
      [ -z "$KEY" ] || [ "$(read_data VerifiedProviderFingerprints | $JQ -cS . 2>/dev/null)" = "$(fingerprints)" ] || return 0
      return 1
    }

    if [ -z "$KEY" ]; then
      echo "fluidvoice: no oMLX key in ~/.omlx/settings.json (run just secrets); Write and Command Mode stay unverified" >&2
    fi
    if drifted; then
      quit_app FluidVoice FluidVoice
      echo "fluidvoice: applying managed settings (Fluid-1 dictation, oMLX for Write and Command Mode)"
      for pair in $STRINGS; do
        /usr/bin/defaults write "$DOMAIN" "''${pair%%=*}" -string "''${pair#*=}"
      done
      for k in $BOOLS; do
        /usr/bin/defaults write "$DOMAIN" "$k" -bool false
      done
      # The app moves this into Keychain.
      /usr/bin/defaults write "$DOMAIN" SavedProviders -data "$(hex "$(providers "$KEY")")"
      /usr/bin/defaults write "$DOMAIN" DictationPromptConfigurations -data "$(hex "$(prompt_configs)")"
      if [ -n "$KEY" ]; then
        /usr/bin/defaults write "$DOMAIN" VerifiedProviderFingerprints -data "$(hex "$(fingerprints)")"
      fi
    fi

    # Best effort. `if` disables set -e here.
    if [ -f "$HANDY_STORE" ] && ! (
      UPDATED="$(${pkgs.jq}/bin/jq '
        .settings.autostart_enabled = false
        | .settings.bindings.transcribe |=
            (if (.current_binding // "" | test("f18")) then .current_binding = .default_binding else . end)
      ' "$HANDY_STORE")" || exit 1
      CURRENT="$(${pkgs.jq}/bin/jq . "$HANDY_STORE")" || exit 1
      [ "$UPDATED" != "$CURRENT" ] || exit 0
      echo "fluidvoice: taking F18 and launch-at-login from Handy"
      # Handy rewrites its store on quit.
      quit_app Handy handy || exit 1
      printf '%s\n' "$UPDATED" > "$HANDY_STORE" || exit 1
    ); then
      echo "fluidvoice: could not update Handy's settings; it may still own F18" >&2
    fi

    # Rebuilt only when the source's store path changes.
    if [ "$(cat "${axDir}/source" 2>/dev/null || true)" != "${axSource}" ]; then
      if /usr/bin/xcode-select -p >/dev/null 2>&1; then
        mkdir -p "${axDir}"
        if HOME="/Users/${user}" /usr/bin/swiftc -O "${axSource}" -o "${axBin}"; then
          printf '%s' "${axSource}" > "${axDir}/source"
          echo "fluidvoice: built fluidvoice-ax; allow it under Accessibility if asked"
          /bin/launchctl kickstart -k "gui/$(id -u)/org.nixos.fluidvoice-ax" >/dev/null 2>&1 || true
        else
          echo "fluidvoice: fluidvoice-ax did not build; Write Mode stays blind in Electron apps" >&2
        fi
      else
        echo "fluidvoice: no Command Line Tools (xcode-select --install); fluidvoice-ax not built" >&2
      fi
    fi

    exec ${launchScript}
  '';
in {
  options.services.fluidvoice.accessibleApps = lib.mkOption {
    type = lib.types.listOf lib.types.str;
    default = [
      "com.tinyspeck.slackmacgap"
      "md.obsidian"
      "com.microsoft.VSCode"
    ];
    description = ''
      Bundle ids of Electron apps whose accessibility fluidvoice-ax turns on,
      so FluidVoice's Write Mode can read their selected text. Electron only;
      other apps ignore the attribute it sets.
    '';
  };

  options.services.fluidvoice.enable = lib.mkEnableOption ''
    FluidVoice on this Darwin host: the cask, a one-time hotkey seed, its
    model routing (Fluid-1 dictation, oMLX for Write and Command Mode), taking
    F18 and launch-at-login from Handy, an `open -a` login agent, and
    fluidvoice-ax, which lets Write Mode read selections in Electron apps
  '';

  config = lib.mkIf cfg.enable {
    homebrew.casks = ["fluidvoice"];

    # Setup failure must never fail the rebuild.
    system.activationScripts.postActivation.text = lib.mkAfter ''
      if ! launchctl asuser "$(id -u -- ${userArg})" sudo --user=${userArg} -- ${activateScript}; then
        echo "WARNING: FluidVoice setup did not finish (see above)." >&2
      fi
    '';

    # A real daemon, so KeepAlive, unlike the open -a agent.
    launchd.user.agents.fluidvoice-ax.serviceConfig = {
      ProgramArguments = [axBin] ++ cfg.accessibleApps;
      RunAtLoad = true;
      KeepAlive = true;
      # Absent until activation first builds it.
      ThrottleInterval = 30;
      StandardOutPath = "/Users/${user}/Library/Logs/fluidvoice-ax.log";
      StandardErrorPath = "/Users/${user}/Library/Logs/fluidvoice-ax.log";
    };

    launchd.user.agents.fluidvoice = {
      command = "${launchScript}";
      serviceConfig = {
        RunAtLoad = true;
        StandardOutPath = "/Users/${user}/Library/Logs/fluidvoice.log";
        StandardErrorPath = "/Users/${user}/Library/Logs/fluidvoice.log";
      };
    };
  };
}
