{
  vars,
  pkgs,
  ...
}: let
  basePackages = import ../../config/base-packages.nix pkgs;
in {
  imports = [
    # Launch Ice (menu bar manager) at login. Here rather than per-host because
    # every Mac gets the cask from ./homebrew-base.nix and wants it running.
    ./ice.nix
  ];

  # Let Determinate manage the Nix daemon; disable nix-darwin's nix management
  nix.enable = false;

  # nixpkgs overlays + allowUnfree come from the shared nixpkgsModule in
  # flake-modules/hosts.nix.

  # Primary user (required for system.defaults, homebrew, etc.)
  system.primaryUser = vars.user.name;

  # User setup
  users.users.${vars.user.name} = {
    home = "/Users/${vars.user.name}";
    shell = pkgs.${vars.user.packages.shell};
  };

  # System packages (CLI tools available system-wide).
  # The baseline is shared with NixOS via config/base-packages.nix.
  environment = {
    inherit (basePackages) systemPackages;

    variables = {
      EDITOR = "nvim";
    };
  };

  # macOS system preferences (declarative)
  system.defaults = {
    dock = {
      autohide = true;
      show-recents = false;
      mru-spaces = false;
      minimize-to-application = true;
      # Disable the bottom-right hot corner (defaults to Quick Note, which opens
      # the Notes app when the cursor hits that corner). 1 = Disabled, 14 = Quick Note.
      wvous-br-corner = 1;
      # NOTE: Finder is intentionally omitted — macOS always pins it to the far
      # left automatically. Listing /System/Applications/Finder.app produces a
      # second, broken "?" tile.
      persistent-apps = [
        "/Applications/Firefox.app"
        "/Applications/Ghostty.app"
        "/Applications/Slack.app"
        "/Applications/Obsidian.app"
        "/Applications/Visual Studio Code.app"
        "/Applications/Bruno.app"
      ];
    };

    finder = {
      AppleShowAllExtensions = true;
      FXPreferredViewStyle = "Nlsv"; # List view
      ShowPathbar = true;
      ShowStatusBar = true;
      _FXShowPosixPathInTitle = true;
    };

    NSGlobalDomain = {
      ApplePressAndHoldEnabled = false; # repeat key on hold instead of accent picker
      AppleShowAllExtensions = true;
      AppleInterfaceStyle = "Dark";
      InitialKeyRepeat = 15;
      KeyRepeat = 2;
      NSAutomaticCapitalizationEnabled = false;
      NSAutomaticSpellingCorrectionEnabled = false;
      "com.apple.swipescrolldirection" = false; # Disable natural scrolling
    };

    trackpad = {
      Clicking = true;
      TrackpadRightClick = true;
      TrackpadThreeFingerDrag = false; # false = three fingers used for Mission Control gestures (swipe up, switch spaces); true = three fingers drag windows/select text
    };

    screencapture = {
      location = "/Users/${vars.user.name}/Pictures/screenshots";
    };

    # Disable the ⌘M "Minimize" shortcut globally by remapping the Minimize
    # menu item to an obscure chord (Ctrl+Option+Shift+M). ⌘M is then bound to
    # nothing and does nothing. No typed NSUserKeyEquivalents option exists in
    # this nix-darwin, so we use CustomUserPreferences against the global domain.
    # Chord encoding: @=Cmd, ~=Option, ^=Control, $=Shift.
    CustomUserPreferences = {
      NSGlobalDomain = {
        NSUserKeyEquivalents = {
          "Minimize" = "~^$m";
        };
      };
    };
  };

  # Power management - display sleep timeout (in minutes)
  power.sleep.display = 5;

  # Touch ID for sudo.
  #
  # `reattach` pulls in pam_reattach, which reattaches the auth attempt to the
  # user's GUI bootstrap session. Without it pam_tid.so cannot reach the Touch ID
  # UI from inside tmux/screen and silently falls back to a typed password — and
  # `just dr` is normally run from tmux. Harmless on headless dungeon.
  security.pam.services.sudo_local = {
    touchIdAuth = true;
    reattach = true;
  };

  # Let Homebrew's own sudo calls through without a password, so `just dr` asks
  # exactly once (for darwin-rebuild itself) instead of again at every cask.
  #
  # Why a sudoers rule is the ONLY thing that works here: Homebrew runs
  # `sudo --reset-timestamp` unconditionally at the top of every invocation
  # (Library/Homebrew/brew.sh, "Reset sudo timestamp to avoid running
  # unauthorized sudo commands"). It deliberately destroys the caller's ticket,
  # so nothing ticket-based survives — not a longer timestamp_timeout, not
  # timestamp_type=global, not a `sudo -v` keep-alive loop in the justfile.
  #
  # And it fires constantly, not just for the odd package: any cask with an
  # `uninstall launchctl:` stanza probes with sudo *unconditionally* — the
  # `booleans = [false, true]` loop in cask/artifact/abstract_uninstall.rb runs
  # the sudo pass with no writability check. That's 12 of the ~47 casks
  # installed here (1password, docker, chrome, vscode, steam, spotify, …).
  #
  # Scope: only the binaries brew actually escalates. Interactive
  # `sudo <anything else>` still prompts normally, which a blanket NOPASSWD
  # would not. Be honest about the limit though — root `cp`/`rm` can be turned
  # into full root, so this is a speed bump against casual misuse, not a
  # security boundary.
  #
  # SETENV is required, not optional. Homebrew installs a `.pkg` cask with
  #   /usr/bin/sudo -u root -E LOGNAME=… USER=… -- /usr/sbin/installer -pkg …
  # and `-E` is refused unless the matching sudoers rule carries SETENV, with
  # "sorry, you are not allowed to preserve the environment". Because this alias
  # names /usr/sbin/installer it is the rule that matches, so WITHOUT SETENV the
  # entry added to help Homebrew is precisely what breaks it — and it fails
  # closed, aborting the whole `brew bundle` and with it `darwin-rebuild switch`.
  #
  # It only bites on `.pkg` casks; the ~47 `.app` drag-installs here never invoke
  # /usr/sbin/installer at all. karabiner-elements is a .pkg, which is why it was
  # the only one failing on dungeon (2026-08-15) while every other cask reported
  # "Using", and why moria never hit it — Karabiner was installed there before
  # this rule existed, so its installer never re-ran.
  #
  # SETENV does not widen the hole in any way that matters: this rule already
  # grants passwordless root `cp`/`rm`, which is game over on its own, as the
  # paragraph above says.
  security.sudo.extraConfig = ''
    Cmnd_Alias BREW_CMDS = /bin/launchctl, /bin/cp, /bin/rm, /bin/chmod, /bin/mkdir, /bin/rmdir, /usr/sbin/chown, /usr/sbin/installer
    ${vars.user.name} ALL=(root) NOPASSWD: SETENV: BREW_CMDS
  '';

  # Timezone
  time.timeZone = vars.system.timeZone;

  # Ensure screenshot directory exists
  system.activationScripts.preActivation.text = ''
    mkdir -p /Users/${vars.user.name}/Pictures/screenshots
  '';

  # Post-activation reminder for manual setup steps
  system.activationScripts.postActivation.text = ''
    echo ""
    echo "NOTE: There are manual steps that may need to be applied for an initial setup."
    echo "      See nixos/modules/darwin/README.md"
    echo ""

    # Reduce spacing between menu bar icons to fit more items
    # https://news.ycombinator.com/item?id=47618946
    defaults -currentHost write -globalDomain NSStatusItemSpacing -int 2
    defaults -currentHost write -globalDomain NSStatusItemSelectionPadding -int 2
  '';

  # Enable zsh system-wide so nix-darwin registers it as a valid shell.
  # The actual shell config is stow-managed (dot/zsh/.zshrc).
  programs.zsh.enable = true;

  # nix-darwin state version
  system.stateVersion = 6;
}
