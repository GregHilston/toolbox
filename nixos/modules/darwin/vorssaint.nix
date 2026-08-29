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
# ## Why the seed lives in the launchd agent rather than postActivation
#
# `system.activationScripts.postActivation` runs as root, and `defaults write`
# resolves its domain from the effective user, so a naive seed there would
# configure root's Vorssaint rather than the one with a menu bar. That much is
# only half an argument, and worth being honest about: nix-darwin's own
# `system.defaults` path solves exactly this with
# `launchctl asuser … sudo --user=…`, and so could a postActivation block.
#
# The reason it lives here anyway is ordering. A launchd user agent already
# runs as the user, and folding the seed and the launch into ONE script makes
# it impossible for the app to start before its features are chosen — which
# matters, because a first launch with nothing written runs the app's own
# Essentials preset and opens the wizard
# (Sources/Vorssaint/Core/FeaturePresets.swift). The tradeoff is that agents
# activate before Homebrew, handled just below.
#
# Its one cost is ordering: nix-darwin activates user agents BEFORE it runs
# Homebrew, so on a fresh host the first run finds no app. The script treats
# that as "not yet" and exits non-zero rather than seeding blind, and the
# `KeepAlive`/`ThrottleInterval` pair below is what brings it back a few
# minutes later once the cask has landed. Waiting is not optional: the update-
# tour markers are read out of the app bundle, so a seed with nothing to read
# would write the wrong ones.
#
# Why `open -g -j -a` and not the inner binary, why RunAtLoad without KeepAlive,
# and why the app's own launch-at-login toggle stays off: nixos/CLAUDE.md →
# "Launching GUI apps at login". This is the third user of that pattern, after
# ./ice.nix and ./handy.nix; it is the only one that also writes preferences.
#
# ## Permissions are still manual
#
# Nothing here can grant TCC. Accessibility and Screen Recording are clicked
# through by hand per host exactly like Ice and Handy — see
# ../../docs/darwin-post-deploy.md. Features that need a grant simply sit inert
# until it is given, so a half-configured host is quiet rather than broken.
#
# ## Conflicts with what these Macs already run
#
# Vorssaint's feature list is wide enough to collide with four things already
# deployed here. Three of the collisions are settled by simply not installing
# the feature — an uninstalled feature does not merely sit idle, it never
# instantiates its service — so they cost nothing but need to stay uninstalled:
#
#   * `superKey` reimplements the Caps Lock hold this repo already does in
#     ../../../dot/karabiner (macOS) and ../common/keyd.nix (NixOS): hold for a
#     modifier, tap for Escape. Two event taps grabbing the same key is the one
#     conflict here that is genuinely broken rather than merely redundant.
#   * `switcher`, `windowLayout`, `windowMaximizer`, `dockPreview` and
#     `dockClick` are a window manager, and the `aerospace` cask is already the
#     window manager. Edge snapping and drag-to-move in particular fight tiling.
#   * `commandBar`, `quickLauncher`, `clipboardHistory` and `textSnippets`
#     duplicate the `raycast` cask, down to competing for global shortcuts.
#
# The fourth is a real choice rather than an obvious no: the `monitor*` features
# below overlap the `stats` cask in ./homebrew-base.nix. Both put CPU, GPU,
# memory, network and battery readouts in the menu bar, and running both means
# two sets of samplers for one set of numbers. They are enabled here because
# Vorssaint's version carries the speed test, disk health and battery power draw
# in the same panel — but if they earn their place, dropping `stats` from
# ./homebrew-base.nix is the follow-up, and if they do not, delete the six ids.
#
# `scrollInverter` is the subtle one, and it is deliberately absent. Its whole
# purpose is to invert the wheel for a mouse *only*, leaving natural scrolling
# on for the trackpad. But ./common.nix sets
# `NSGlobalDomain."com.apple.swipescrolldirection" = false`, which already
# inverts both, so adding the feature on top would invert the mouse twice and
# hand back exactly the behavior it exists to fix. To adopt it properly, flip
# that global back to `true` (trackpad returns to natural scrolling) and add
# "scrollInverter" to the list below in the same commit — one or the other
# alone is a regression.
#
# ## Where the feature list came from
#
# The default below is the set https://youtu.be/s8dzlv4WuNk singles out as the
# ones actually worth having after a month of use, minus the two that video
# tried and did not keep (`commandBar`, `quickLauncher`) and minus the conflicts
# above. It is a starting point, not a verdict: the hub is one click
# per feature, and this list is only ever read on a Mac that has never run the
# app.
{
  config,
  lib,
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
    autoQuit = "autoQuitEnabled";
    smoothScroll = "smoothScrollEnabled";
    # The feature's other key, finderPasteImageAsFile (paste an image as a PNG),
    # is a second behavior rather than the ⌘X/⌘V this is here for. `enabledKeys`
    # is an any-of, so the one below is what engages the feature.
    finderCutPaste = "finderCutPasteEnabled";
    shelf = "shelfEnabled";
    urlCleaner = "urlCleanerEnabled";
    screenshot = "screenshotShortcutEnabled";
    screenOCR = "screenOCRShortcutEnabled";
  };

  enableWrites = lib.concatMapStringsSep "\n" (
    feature: "  /usr/bin/defaults write \"$DOMAIN\" ${featureEnableKeys.${feature}} -bool true"
  ) (builtins.filter (feature: featureEnableKeys ? ${feature}) cfg.features);

  # Only ever reaches ~/Library/Logs/vorssaint.log, but it is the one place a
  # host says out loud which set it came up with.
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
        # Sound. Per-app volume, and per-app *output* with it: music out of the
        # speakers while a call or an editor stays in the headphones. macOS has
        # no equivalent at all. Wants the System Audio Recording grant.
        "mixer"

        # Stay awake with the lid closed. The reason clamshell mode works on
        # battery instead of sleeping the moment the charger comes out --
        # `caffeinate` keeps the Mac up but drops the external display.
        "keepAwake"

        # Give a mouse wheel trackpad-style glide. Note the deliberate absence
        # of "scrollInverter" beside it: see the header's conflicts section, it
        # would double-invert against this repo's own global setting.
        "smoothScroll"

        # Capture and OCR, both on the free control-option-command layer
        # (screenshot on 4, text-from-screen on T), so macOS keeps its own
        # command-shift-3/4/5 and screencapture.location in ./common.nix stands.
        "screenshot"
        "screenOCR"

        # command-X then command-V moves a file in Finder, instead of the
        # command-option-V that nothing outside macOS uses.
        "finderCutPaste"

        # Closing the last window quits the app, for the handful (Obsidian,
        # Notes, browsers) that otherwise linger with no window at all.
        "autoQuit"

        # System monitor, one id per metric family. OVERLAPS the `stats` cask in
        # ./homebrew-base.nix — see the header's conflicts section before
        # deciding which of the two keeps the menu bar.
        "monitorCPU"
        "monitorGPU"
        "monitorMemory"
        "monitorNetwork"
        "monitorDisk"
        "monitorPower"

        # One-click system actions: light/dark, keyboard backlight, empty the
        # Trash, eject every disk. Wants the Finder automation grant.
        "quickToggles"

        # Lock the keyboard and black out the displays to wipe them down.
        "cleaningMode"

        # Removal and leftovers. `uninstaller` takes an app's caches, prefs and
        # helpers with it; `cleaner` sweeps what a normal drag-to-Trash left
        # behind. Both reach further with the optional Full Disk Access grant.
        "uninstaller"
        "cleaner"

        # Homebrew formulae and casks without a terminal. Read-mostly here --
        # ./homebrew-base.nix is authoritative for anything that should survive
        # a rebuild, and `onActivation.cleanup = "none"` means a cask installed
        # by hand through this pane simply persists undeclared.
        "homebrew"

        # Strip tracking parameters from copied links.
        "urlCleaner"

        # A floating shelf to park files mid-drag and drop them somewhere else
        # later, instead of holding a drag across a window switch.
        "shelf"
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

    launchd.user.agents.vorssaint = {
      script = ''
        # `set -e` matters more than it looks: without it a `defaults write`
        # that fails part way through still falls through to the `hasOnboarded`
        # write at the end, marking a half-seeded Mac as done forever.
        set -eu

        DOMAIN="${domain}"
        APP="/Applications/Vorssaint.app"

        # Do nothing at all until the cask has landed. nix-darwin activates user
        # agents BEFORE it runs Homebrew, so on a fresh host this is the first
        # run's normal outcome, not an error. Seeding anyway would be worse than
        # waiting: the version markers below are read out of the bundle, so a
        # seed with no app to read would write the wrong ones and let the update
        # tour through on the very launch this exists to keep clean. Exiting
        # non-zero is what gets us called again — see KeepAlive below.
        if [ ! -d "$APP" ]; then
          echo "vorssaint: $APP is not installed yet, retrying later"
          exit 1
        fi

        # `hasOnboarded` is the app's own "setup is finished" marker. Absent (a
        # Mac that has never run it) or false is the only state we write in.
        if [ "$(/usr/bin/defaults read "$DOMAIN" hasOnboarded 2>/dev/null || echo 0)" = "1" ]; then
          echo "vorssaint: already set up, leaving the Features hub alone"
        else
          echo "vorssaint: seeding the Features hub with ${chosen}"

        ${featureWrites}

        ${enableWrites}

          # Setting `hasOnboarded` behind the app's back skips the setup wizard
          # but lands on the other branch of its first-launch check, which is
          # the post-UPDATE path: a release-notes tour and a support ask whose
          # window deliberately has no close button. The app's own
          # markOnboardingComplete() suppresses all three for a clean install;
          # this does the same by hand.
          #
          # Each is gated on `appVersion == <a constant compiled into that
          # build> && lastSeen != <same constant>`, so writing the running
          # version into `lastSeen` makes both readings false whatever the
          # version is — no release number to keep up to date here, and a
          # genuine tour after a genuine future update still shows, because
          # this whole block only ever runs once.
          VERSION="$(/usr/bin/defaults read "$APP/Contents/Info" CFBundleShortVersionString)"
          for KEY in updateHighlightsSeenVersion supportUpdateIntroVersion updateShowcaseIntroVersion; do
            /usr/bin/defaults write "$DOMAIN" "$KEY" -string "$VERSION"
          done

          # The in-app launch-at-login toggle registers an SMAppService login
          # item that nix neither owns nor can assert, and the agent this script
          # runs from already does the job. Pin it off so the two never both
          # register. See nixos/CLAUDE.md → "Launching GUI apps at login".
          /usr/bin/defaults write "$DOMAIN" launchAtLoginWanted -bool false

          # Last, deliberately: it is the marker that stops the next run. A seed
          # that dies before here leaves it unset and simply redoes the whole
          # thing.
          /usr/bin/defaults write "$DOMAIN" hasOnboarded -bool true
        fi

        # `open` on a running app just activates it, so this is safe to re-run
        # on every activation. -g = don't steal focus, -j = launch hidden.
        exec /usr/bin/open -g -j -a "$APP"
      '';

      serviceConfig = {
        RunAtLoad = true;

        # The one place this departs from ./ice.nix and ./handy.nix, and it is
        # narrower than the "never KeepAlive" those two carry. What that rule
        # forbids is a bare `KeepAlive = true`, which reads `open`'s immediate
        # exit as a crash and respawns for ever. `SuccessfulExit = false` is the
        # opposite: retry only while the script FAILS, which here means only
        # while the cask is missing. The moment Homebrew installs it the seed
        # runs, `open` succeeds, and the job stops being restarted.
        #
        # It is needed because the alternative recovery does not exist.
        # nix-darwin only reloads a user agent when its generated plist differs
        # from the installed one, so an unchanged config means the agent is
        # never re-bootstrapped and RunAtLoad never fires again: without this,
        # a fresh host whose first activation ran before Homebrew would stay
        # unseeded until the next login, and `just dr` would not fix it.
        KeepAlive = {
          SuccessfulExit = false;
        };
        ThrottleInterval = 300;

        # Where the seed says whether it ran, which set it wrote, or that it is
        # still waiting on the cask.
        StandardOutPath = "/Users/${user}/Library/Logs/vorssaint.log";
        StandardErrorPath = "/Users/${user}/Library/Logs/vorssaint.log";
      };
    };
  };
}
