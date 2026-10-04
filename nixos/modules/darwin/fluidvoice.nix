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
  lightModel = config.services.omlxDeploy.lightModel.dir;

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

  # Outside the store, so rebuilds don't move it.
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
    export PATH=${pkgs.jq}/bin:/usr/bin:/bin:/usr/sbin
    export HOME=/Users/${user}
    export DOMAIN=com.FluidApp.app
    export APP=/Applications/FluidVoice.app
    export HANDY_STORE="/Users/${user}/Library/Application Support/com.pais.handy/settings_store.json"
    export OMLX_SETTINGS=/Users/${user}/.omlx/settings.json
    export SEED_DICTATION=${lib.escapeShellArg dictation}
    export SEED_DICTATION_LEGACY=${lib.escapeShellArg dictationLegacy}
    export SEED_COMMAND=${lib.escapeShellArg command}
    export SEED_WRITE=${lib.escapeShellArg write}
    export DICTIONARY=${lib.escapeShellArg (builtins.toJSON dictionary)}
    export PROVIDER=${lib.escapeShellArg (builtins.toJSON omlx)}
    export STRINGS=${lib.escapeShellArg strings}
    export AX_SOURCE=${axSource}
    export AX_DIR=${lib.escapeShellArg axDir}
    export LAUNCH=${launchScript}
    exec /bin/bash ${./fluidvoice-activate.sh}
  '';

  strings = lib.concatStringsSep "\n" [
    "SelectedProviderID=${fluid1}"
    "SelectedDictationPromptID=${fluid1Prompt}"
    "RewriteModeSelectedProviderID=${omlx.id}"
    "RewriteModeSelectedModel=${lightModel}:lab"
    "CommandModeSelectedProviderID=${omlx.id}"
    "CommandModeSelectedModel=${lightModel}"
  ];
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

    # Not AXEnhancedUserInterface: it slows AeroSpace.
    system.defaults.CustomUserPreferences."org.mozilla.firefox" = {
      EnterprisePoliciesEnabled = true;
      Preferences."accessibility.force_disabled" = {
        Value = -1;
        Status = "default";
      };
    };

    # A daemon, unlike open -a: KeepAlive.
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
