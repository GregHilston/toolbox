# Shared Homebrew baseline for all Darwin hosts.
#
# homebrew.brews/casks/taps are list options, so each host imports this module
# and *adds* its own host-specific extras on top (the module system concatenates
# the lists). Only this module sets the non-list options (enable, onActivation)
# and the oMLX launchd agent, so hosts never need to repeat them.
{vars, ...}: {
  # Launch omlx LLM inference server at login so pi and other tools can connect.
  # Runs as a user agent (not a system daemon) so it has access to ~/models and ~/.omlx/.
  launchd.user.agents.omlx = {
    command = "/opt/homebrew/bin/omlx serve";
    serviceConfig = {
      RunAtLoad = true;
      KeepAlive = true;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/omlx.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/omlx.log";
    };
  };

  homebrew = {
    enable = true;

    onActivation = {
      autoUpdate = true;
      # "none" — don't touch packages not declared in the config. Change to
      # "check" once manually-installed brew drift has been cleaned up.
      cleanup = "none";
      upgrade = true;
    };

    taps = [
      "nikitabobko/tap" # AeroSpace
      {
        name = "jundot/omlx";
        clone_target = "https://github.com/jundot/omlx";
      } # omlx LLM inference server
      # GOTCHA: newer Homebrew enforces a tap-trust check that silently aborts the
      # omlx source build (it builds from source via rust) with NO output — leaving the
      # host stuck on an old version (this is how dungeon got pinned at 0.3.8 while moria
      # was on 0.4.4rc1). If `brew upgrade jundot/omlx/omlx` fails with a bare
      # "build.rb exited with 1", run `brew trust jundot/omlx` once, or upgrade with
      # HOMEBREW_NO_REQUIRE_TAP_TRUST=1. Not a Command Line Tools / OS-version problem.
    ];

    # Common CLI tools — managed via brew rather than nix for easier macOS updates.
    brews = [
      "stow"
      "tmux"
      "just"
      "pandoc"
      "gh"

      # AI / LLM
      "jundot/omlx/omlx"
      "pi-coding-agent"
    ];

    # Apps every Darwin host gets. Host-specific apps live in each host's config.
    casks = [
      # Core
      "ghostty"
      "firefox"
      "visual-studio-code"
      "1password"

      # Communication
      "slack"

      # Media
      "spotify"
      "vlc"

      # Dev
      "bruno"
      "docker-desktop"
      "dbeaver-community"
      "db-browser-for-sqlite"
      "ngrok"

      # Drivers
      "displaylink"

      # Productivity
      "obsidian"
      "raycast"
      "stats"
      "jordanbaird-ice"
      "aerospace"
    ];
  };
}
