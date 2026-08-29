# Vorssaint — one menu bar app in place of a dozen small Mac utilities.
#
# https://github.com/vorssaint/vorssaint-utils (GPL-3.0-or-later, Swift, bundle
# id com.vorssaint.utils). Installed from the `vorssaint` cask, which is
# Developer-ID signed, notarized, and `depends_on arch: :arm64` — the macOS 14
# floor is the app's own (LSMinimumSystemVersion). Every Mac here clears both.
#
# The cask is also `auto_updates true`, which means `brew upgrade` SKIPS it
# without `--greedy`: despite `onActivation.upgrade = true` in
# ./homebrew-base.nix, the app's own updater is what actually keeps it current,
# and the installed version drifts from the cask's. That is left alone on
# purpose — pinning it by turning the in-app updater off would freeze the app
# at whatever version first landed, since nothing else would move it.
#
# This module does three things, and each is enabled per host by importing it
# and setting `services.vorssaint.enable`:
#   1. adds the cask (nix-darwin concatenates it onto the host's casks list),
#   2. launches the app at login with the usual `open -a` agent,
#   3. seeds the Features hub ONCE, so a fresh host comes up with the feature
#      set below already chosen instead of the app's own setup wizard.
#
# ## Why (3) is a seed and not a declarative `system.defaults` block
#
# Vorssaint has no config file. The Features hub is GUI-only, and its "export
# settings" writes a plist through an NSSavePanel — there is no CLI, no watched
# file and no import flag. What it *does* have is an ordinary UserDefaults
# domain: one boolean per feature, `featureAvailable.<id>`, where the ids are
# the AppFeature raw values (Sources/Vorssaint/Core/FeatureCatalog.swift).
#
# So the keys could go straight into `system.defaults.CustomUserPreferences` and
# be rewritten on every `just dr`. They deliberately are not, for two reasons:
#
#   * The app owns this state at runtime. Every toggle in the Features hub, and
#     every preset button, writes these same keys. Enforcing them on activation
#     would silently undo anything flipped in the GUI — the same reason oMLX's
#     downloaded models and CrossOver's bottles are left to their apps.
#   * Availability is only read at launch. A mid-session rewrite would not take
#     effect until a relaunch anyway (the app relaunches itself after its own
#     settings import for exactly this reason), so "declarative" would buy a
#     value that disagrees with what is on screen.
#
# The seed is gated on `hasOnboarded`, which the app itself sets the moment
# setup finishes. So it fires exactly once per Mac — on the first activation
# after the cask lands — and never fights the hub afterwards. To re-seed a host
# deliberately (say, after changing the list below), clear the marker and let
# the agent re-run:
#
#   defaults delete com.vorssaint.utils hasOnboarded
#   launchctl kickstart -k "gui/$(id -u)/org.nixos.vorssaint"
#
# A plain `brew uninstall --cask vorssaint` does NOT reset this: its cask only
# quits the app and removes the bundle, and the preferences plist is listed
# under `zap`. So reinstalling after a plain uninstall keeps `hasOnboarded` and
# does not re-seed; `brew uninstall --zap --cask vorssaint` is the one that
# takes the plist with it.
#
# ## Why the seed runs in postActivation and not in the login agent
#
# It ran in the agent first, and moria proved that wrong on its first deploy —
# worth writing down, because the failure is invisible until it has already
# cost you the one chance the seed gets.
#
# nix-darwin's activation order (modules/system/activation-scripts.nix) is:
# user agents, then Homebrew, then postActivation. So an agent-hosted seed
# always fires on a Mac where the cask has not been installed yet, and every
# option from there is bad. Seeding blind is wrong on its own terms: the
# update-tour markers below are read out of the app bundle, so there is
# nothing to read. Waiting and retrying — what this did — leaves a window
# between `just dr` finishing and the retry in which the app is installed,
# unconfigured, and one click away in Spotlight. Whoever opens it gets the
# wizard, and the wizard sets `hasOnboarded` itself, so the seed is locked out
# for good. A seed that only gets one chance must not spend it racing a human.
#
# postActivation has none of that: Homebrew has already run, and the person who
# typed `just dr` is still watching it finish.
#
# The root objection to postActivation is real but solved upstream — activation
# runs as root and `defaults` resolves its domain from the effective user, so
# an unwrapped write configures root's Vorssaint. nix-darwin's own
# `system.defaults` path answers it with
# `launchctl asuser "$(id -u -- user)" sudo --user=user --`
# (modules/system/defaults-write.nix), and that is exactly what is copied here.
#
# What is left in the agent is only the launch, in the plain shape ./ice.nix
# and ./handy.nix use. Why `open -g -j -a` and not the inner binary, why
# RunAtLoad without KeepAlive, and why the app's own launch-at-login toggle
# stays off: nixos/CLAUDE.md → "Launching GUI apps at login". This is that
# pattern's third user, and it needs no exception to it.
#
# ## Permissions are still manual
#
# Nothing here can grant TCC. Accessibility and Screen Recording are clicked
# through by hand per host exactly like Ice and Handy — see
# ../../docs/darwin-post-deploy.md. Features that need a grant simply sit inert
# until it is given, so a half-configured host is quiet rather than broken.
#
# ## Overlap with what these Macs already run
#
# Vorssaint is wide enough to reach into four things already deployed here.
# The list below does not dodge all of them, and that is a choice made at the
# machine rather than an oversight — worth knowing before reading it as an
# accident:
#
#   * `switcher` and `dockPreview` overlap the `aerospace` cask. AeroSpace
#     tiles; these replace ⌘Tab and add Dock hover previews, which is a
#     different job, so they coexist. The tiling-hostile half of Vorssaint —
#     `windowLayout` (edge snapping, drag-to-move) and `windowMaximizer` — is
#     the part left out.
#   * `commandBar` and `clipboardHistory` overlap the `raycast` cask outright.
#     See the shortcut note below; this is the overlap most likely to bite.
#   * The `monitor*` features overlap the `stats` cask. Both put CPU, GPU,
#     memory, network and battery readouts in the menu bar, so this is two sets
#     of samplers for one set of numbers. If Vorssaint's version earns its
#     place — it carries the speed test, disk health and battery power draw in
#     the same panel — dropping `stats` from ./homebrew-base.nix is the
#     follow-up.
#
# `superKey` is the one genuine incompatibility and stays out for good. It
# reimplements the Caps Lock hold this repo already does in
# ../../../dot/karabiner (macOS) and ../common/keyd.nix (NixOS): hold for a
# modifier, tap for Escape. Two event taps grabbing one key is broken rather
# than merely redundant.
#
# ## The one shortcut this deliberately leaves off
#
# `commandBar` is installed but its shortcut is NOT switched on, and it is the
# only chosen feature treated that way. Its default binding is ⌥Space, which is
# also Raycast's default hotkey — turning it on from here would quietly take
# over the launcher key on both Macs. The bar still opens from the menu panel,
# and picking a combination for it is a decision to make in Settings with
# Raycast's own binding in view. Everything else that needed switching on got
# switched on; see `featureEnableKeys`.
#
# `scrollInverter` is absent for a different reason, and it is the subtle one.
# Its whole purpose is to invert the wheel for a mouse *only*, leaving natural
# scrolling on for the trackpad. But ./common.nix sets
# `NSGlobalDomain."com.apple.swipescrolldirection" = false`, which already
# inverts both, so adding the feature on top would invert the mouse twice and
# hand back exactly the behavior it exists to fix. To adopt it properly, flip
# that global back to `true` (trackpad returns to natural scrolling) and add
# "scrollInverter" to the list in the same commit — one or the other alone is
# a regression.
#
# ## Where the feature list came from
#
# It started as the set https://youtu.be/s8dzlv4WuNk singles out after a month
# of use. It is now moria's actual hub, read back off the machine after that
# host was set up by hand, so citadel comes up matching moria rather than
# matching a video. Two things changed in that trip worth noticing if you are
# reconsidering the list: `keepAwake` — the video's headline feature, closing
# the lid on an external display without the charger — is NOT in it, and
# neither are `uninstaller`, `cleaner` or `homebrew`.
#
{
  config,
  lib,
  pkgs,
  vars,
  ...
}: let
  cfg = config.services.vorssaint;
  user = vars.user.name;
  domain = "com.vorssaint.utils";

  # Every id the Features hub understands, in the app's own grouping. These are
  # the raw values of `enum AppFeature` in
  # Sources/Vorssaint/Core/FeatureCatalog.swift, which its comment promises are
  # stable ("cases can be added but never renamed") — they are what gets
  # persisted inside the availability key. Used as the option's enum, so a typo
  # fails evaluation with the valid list rather than writing a dead key.
  knownFeatures = [
    # Windows and Dock
    "switcher"
    "dockPreview"
    "dockClick"
    "windowMaximizer"
    "windowLayout"
    "autoQuit"
    # Mouse and keyboard
    "scrollInverter"
    "focusFollowsMouse"
    "smoothScroll"
    "mouseNavigation"
    "mouseButtonShortcuts"
    "middleClick"
    "keyboardDebounce"
    "textSnippets"
    "superKey"
    # Clipboard and files
    "clipboardHistory"
    "pastePlain"
    "finderCutPaste"
    "finderRename"
    "shelf"
    "urlCleaner"
    "diskImageInstaller"
    # Sound
    "mixer"
    "soundOutputSwitcher"
    "micMute"
    "musicBlock"
    # Energy and display
    "keepAwake"
    "brightness"
    "extraBrightness"
    "bluetoothSleep"
    # Tools
    "quickLauncher"
    "quickToggles"
    "colorPicker"
    "screenOCR"
    "cleaningMode"
    "mediaTools"
    "cleaner"
    "uninstaller"
    "homebrew"
    "appUpdates"
    "screenshot"
    "cameraPreview"
    "radialMenu"
    "scratchpad"
    "commandBar"
    "screenRecorder"
    "killProcess"
    # System monitor, one entry per metric family
    "monitorCPU"
    "monitorGPU"
    "monitorMemory"
    "monitorNetwork"
    "monitorDisk"
    "monitorPower"
    "fanControl"
  ];

  # Write EVERY id, not just the chosen ones. The off writes are what make the
  # seed total: without them an unlisted feature falls back to whatever the app
  # registered as its default, so the list below would describe the host only
  # by accident. This mirrors the app's own first-run pass.
  #
  # A plain string, not an indented one, and the two leading spaces are on
  # purpose: this lands inside the seed script's `else` branch, and nix strips
  # an indented string's indentation at parse time — before interpolation ever
  # happens — so the alignment has to be part of the value or it is lost.
  featureWrites =
    lib.concatMapStringsSep "\n" (
      feature:
        "  /usr/bin/defaults write \"$DOMAIN\" featureAvailable.${feature} -bool "
        + lib.boolToString (builtins.elem feature cfg.features)
    )
    knownFeatures;

  # Availability is a layer ABOVE each feature's own enable key
  # (FeatureCatalog.swift, `enabledKeys`): installing a feature makes it appear
  # in Settings and instantiate its service, but a feature that listens for
  # something — a wheel event, a window closing, a ⌘X — still checks its own
  # switch, and every one of those ships off. Seeding availability alone would
  # hand over five features that are present and do nothing.
  #
  # So: for each chosen feature, also switch on what makes it act. The last two
  # are not `enabledKeys` at all but the shortcut switches for two on-demand
  # tools, off by default, without which the capture and OCR bindings
  # (⌃⌥⌘4, ⌃⌥⌘T) are printed in Settings but dead. Everything omitted here —
  # mixer, keepAwake, the monitors, quickToggles, cleaningMode, uninstaller,
  # cleaner, homebrew — is on-demand: `enabledKeys` is empty for those, and the
  # app counts being installed as being engaged.
  #
  # Only ever written `true`, and only for chosen features: an unchosen feature
  # is uninstalled anyway, and writing its switch off would reach past what
  # this seed is for into settings the hub owns.
  featureEnableKeys = {
    # `enabledKeys`: without these the feature is installed and does nothing.
    autoQuit = "autoQuitEnabled";
    brightness = "brightnessControlEnabled";
    clipboardHistory = "clipboardHistoryEnabled";
    dockPreview = "dockPreviewEnabled";
    pastePlain = "pastePlainEnabled";
    shelf = "shelfEnabled";
    smoothScroll = "smoothScrollEnabled";
    urlCleaner = "urlCleanerEnabled";
    # Already ships on; written anyway so the seed describes the host outright
    # rather than by agreeing with a default that could change.
    switcher = "switcherEnabled";
    # The feature's other key, finderPasteImageAsFile (paste an image as a
    # PNG), is a second behavior rather than the ⌘X/⌘V this is here for.
    # `enabledKeys` is an any-of, so the one below is what engages it.
    finderCutPaste = "finderCutPasteEnabled";

    # Not `enabledKeys` — these tools work from the menu panel regardless. They
    # are here because a capture tool you cannot reach from the keyboard is
    # most of a capture tool missing, and all four default onto the free ⌃⌥⌘
    # layer, which nothing else here uses.
    screenshot = "screenshotShortcutEnabled";
    screenOCR = "screenOCRShortcutEnabled";
    screenRecorder = "recorderShortcutEnabled";
    cameraPreview = "cameraPreviewShortcutEnabled";
  };

  enableWrites = lib.concatMapStringsSep "\n" (
    feature: "  /usr/bin/defaults write \"$DOMAIN\" ${featureEnableKeys.${feature}} -bool true"
  ) (builtins.filter (feature: featureEnableKeys ? ${feature}) cfg.features);

  # Only ever reaches ~/Library/Logs/vorssaint.log, but it is the one place a
  # host says out loud which set it came up with.
  userArg = lib.escapeShellArg user;

  # Runs AS THE USER — see the postActivation block below for how, and why it
  # is not in the login agent.
  seedScript = pkgs.writeShellScript "vorssaint-seed" ''
    # `set -e` matters more than it looks: without it a `defaults write` that
    # fails part way through still falls through to the `hasOnboarded` write at
    # the end, marking a half-seeded Mac as done for ever.
    set -eu

    DOMAIN="${domain}"
    APP="/Applications/Vorssaint.app"

    # Reached only after Homebrew has run, so a missing app means the cask
    # failed rather than "not yet". Nothing to do, and not our error to raise.
    if [ ! -d "$APP" ]; then
      echo "vorssaint: $APP is not installed, skipping the seed"
      exit 0
    fi

    # `hasOnboarded` is the app's own "setup is finished" marker. Absent (a Mac
    # that has never run it) or false is the only state we write in — so a hub
    # you have since curated by hand is never overwritten.
    if [ "$(/usr/bin/defaults read "$DOMAIN" hasOnboarded 2>/dev/null || echo 0)" = "1" ]; then
      echo "vorssaint: already set up, leaving the Features hub alone"
    else
      echo "vorssaint: seeding the Features hub with ${chosen}"

    ${featureWrites}

    ${enableWrites}

      # Setting `hasOnboarded` behind the app's back skips the setup wizard but
      # lands on the other branch of its first-launch check, which is the post-
      # UPDATE path: a release-notes tour and a support ask whose window
      # deliberately has no close button. The app's own markOnboardingComplete()
      # suppresses all three for a clean install; this does the same by hand.
      #
      # Each is gated on `appVersion == <a constant compiled into that build> &&
      # lastSeen != <same constant>`, so writing the running version into
      # `lastSeen` makes both readings false whatever the version is — no
      # release number to keep up to date here, and a genuine tour after a
      # genuine future update still shows, because this only ever runs once.
      VERSION="$(/usr/bin/defaults read "$APP/Contents/Info" CFBundleShortVersionString)"
      for KEY in updateHighlightsSeenVersion supportUpdateIntroVersion updateShowcaseIntroVersion; do
        /usr/bin/defaults write "$DOMAIN" "$KEY" -string "$VERSION"
      done

      # The in-app launch-at-login toggle registers an SMAppService login item
      # that nix neither owns nor can assert, and the agent below already does
      # the job. Pin it off so the two never both register. See nixos/CLAUDE.md
      # → "Launching GUI apps at login".
      /usr/bin/defaults write "$DOMAIN" launchAtLoginWanted -bool false

      # Last, deliberately: it is the marker that stops the next run. A seed
      # that dies before here leaves it unset and simply redoes the whole thing.
      /usr/bin/defaults write "$DOMAIN" hasOnboarded -bool true
    fi

    # So a fresh `just dr` ends with the app running and configured, rather than
    # configured but not visible until the next login. Idempotent: `open` on a
    # running app just activates it, and -g/-j keep it quiet and hidden.
    exec /usr/bin/open -g -j -a "$APP"
  '';

  chosen =
    if cfg.features == []
    then "nothing"
    else lib.concatStringsSep ", " cfg.features;
in {
  options.services.vorssaint = {
    enable = lib.mkEnableOption ''
      Vorssaint on this Darwin host: the cask, an `open -a` login agent, and a
      one-time seed of the Features hub from `services.vorssaint.features`
    '';

    features = lib.mkOption {
      type = lib.types.listOf (lib.types.enum knownFeatures);
      default = [
        # Sound. Per-app volume and per-app output; macOS has no equivalent.
        "mixer"

        # Windows and Dock. `switcher` is the one to know about: its enable key
        # ships ON and its default binding is ⌘Tab, so installing it replaces
        # the system app switcher rather than sitting beside it.
        "switcher"
        "dockPreview"
        "autoQuit"

        # Clipboard and files. `pastePlain` binds ⇧⌥⌘V, the same combination
        # macOS uses for Paste and Match Style, deliberately — it does the same
        # job everywhere rather than only where an app implements it.
        "clipboardHistory"
        "pastePlain"
        "finderCutPaste"
        "urlCleaner"

        # Display. Brightness for external screens over their own control
        # channel, which the keyboard keys do not reach.
        "brightness"

        # Capture and tools. The three capture tools share one selector and sit
        # on the free ⌃⌥⌘ layer (4, T, 5), so macOS keeps ⌘⇧3/4/5 and the
        # screencapture.location in ./common.nix still stands.
        "screenshot"
        "screenOCR"
        "screenRecorder"
        "cameraPreview"
        "mediaTools"
        "commandBar"

        # System monitor, one id per metric family. Overlaps the `stats` cask
        # in ./homebrew-base.nix — see the header's conflicts section.
        "monitorCPU"
        "monitorGPU"
        "monitorMemory"
        "monitorNetwork"
        "monitorDisk"
        "monitorPower"
      ];
      description = ''
        Features to install on a fresh host. Everything omitted is written off,
        which in Vorssaint means uninstalled: it disappears from Settings, the
        menu panel and the menu bar, its service never instantiates, and it
        spends no CPU or energy. Nothing is deleted — a feature switched back on
        later, here or in the hub, returns with its old settings.

        Only ever applied to a Mac that has not been set up yet; see the header.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    homebrew.casks = ["vorssaint"];

    # Seed the Features hub here, and NOT from the login agent below, because
    # ordering is the whole problem. nix-darwin's activation runs
    # `userLaunchd` (agents) BEFORE `homebrew`, and `postActivation` after it
    # — modules/system/activation-scripts.nix, in that order. A seed in the
    # agent therefore fires on a Mac with no app yet, and whatever it does
    # next is a race: launch the app unseeded, or wait and retry and lose to
    # whoever opens Vorssaint first. Losing that race is permanent, because
    # the wizard sets `hasOnboarded` itself and the seed never runs again.
    #
    # From here the cask is already installed and the human is still watching
    # `just dr` finish, so there is no race left to lose.
    #
    # `launchctl asuser … sudo --user=…` is nix-darwin's own idiom for this
    # (modules/system/defaults-write.nix): activation runs as root, and
    # `defaults` resolves its domain from the effective user, so an unwrapped
    # write would configure root's Vorssaint rather than the one with a menu
    # bar.
    #
    # Never fatal. The activation script runs under `set -e`, and a Mac that
    # cannot be seeded — no GUI session to attach to, Homebrew failed earlier
    # — is not a reason to fail the whole rebuild. The app just shows its own
    # wizard, which is exactly where this started.
    system.activationScripts.postActivation.text = lib.mkAfter ''
      if ! launchctl asuser "$(id -u -- ${userArg})" sudo --user=${userArg} -- ${seedScript}; then
        echo "WARNING: the Vorssaint seed did not finish (see above)." >&2
        echo "         Vorssaint will show its own setup wizard on first launch." >&2
      fi
    '';

    # Plain ./ice.nix shape, now that the seed has moved out: RunAtLoad, no
    # KeepAlive, `open -a` rather than the inner binary. See nixos/CLAUDE.md →
    # "Launching GUI apps at login" for why each of those.
    launchd.user.agents.vorssaint = {
      command = "/usr/bin/open -g -j -a /Applications/Vorssaint.app";
      serviceConfig = {
        RunAtLoad = true;
        # Where "Unable to find application named 'Vorssaint'" shows up if the
        # cask hasn't installed yet on a fresh host — the agent is bootstrapped
        # before Homebrew runs, so that is the normal first-deploy outcome and
        # the postActivation seed above is what launches it that time round.
        StandardOutPath = "/Users/${user}/Library/Logs/vorssaint.log";
        StandardErrorPath = "/Users/${user}/Library/Logs/vorssaint.log";
      };
    };
  };
}
