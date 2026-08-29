# Vorssaint — one menu bar app in place of a dozen small Mac utilities.
#
# https://github.com/vorssaint/vorssaint-utils (GPL-3.0-or-later, Swift, bundle
# id com.vorssaint.utils). Installed from the `vorssaint` cask: arm64 + macOS 14
# only, which every Mac here satisfies, and Developer-ID signed + notarized.
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
# Note that `brew uninstall --cask vorssaint` deletes the whole preferences
# plist, which clears `hasOnboarded` too — so a reinstall re-seeds on its own.
#
# ## Why the seed lives in the launchd agent rather than postActivation
#
# `system.activationScripts.postActivation` runs as root, and `defaults write`
# resolves its domain from the effective user: seeding there would configure
# root's Vorssaint, not the one with a menu bar. A launchd *user* agent already
# runs as the user, in their GUI session, so cfprefsd sees the writes. Folding
# the seed and the launch into one script also fixes the ordering for free —
# the app can never start before its features are chosen, which matters because
# a first launch with nothing written runs the app's own Essentials preset and
# opens the wizard (Sources/Vorssaint/Core/FeaturePresets.swift).
#
# Its one cost: on a fresh host the agent can bootstrap before Homebrew has
# installed the cask. The seed still lands (the domain needs no app), and the
# `open` fails into ~/Library/Logs/vorssaint.log until the next activation.
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
        # `set -u` and nothing more: nix-darwin's shell for a launchd script is
        # not guaranteed to be bash, and there is nothing here to pipefail.
        set -u

        DOMAIN="${domain}"

        # `hasOnboarded` is the app's own "setup is finished" marker. Absent (a
        # Mac that has never run it) or false is the only state we write in.
        if [ "$(/usr/bin/defaults read "$DOMAIN" hasOnboarded 2>/dev/null || echo 0)" = "1" ]; then
          echo "vorssaint: already set up, leaving the Features hub alone"
        else
          echo "vorssaint: seeding the Features hub with ${chosen}"

        ${featureWrites}

          # The in-app launch-at-login toggle registers an SMAppService login
          # item that nix neither owns nor can assert, and the agent this script
          # runs from already does the job. Pin it off so the two never both
          # register. See nixos/CLAUDE.md → "Launching GUI apps at login".
          /usr/bin/defaults write "$DOMAIN" launchAtLoginWanted -bool false

          # Last, deliberately: it is the marker that stops the next run. An
          # interrupted seed leaves it unset and simply redoes the whole thing.
          /usr/bin/defaults write "$DOMAIN" hasOnboarded -bool true
        fi

        # `open` on a running app just activates it, so this is safe to re-run
        # on every activation. -g = don't steal focus, -j = launch hidden.
        exec /usr/bin/open -g -j -a /Applications/Vorssaint.app
      '';

      serviceConfig = {
        RunAtLoad = true;
        # Where "Unable to find application named 'Vorssaint'" shows up if the
        # cask hasn't installed yet on a fresh host, and where the seed reports
        # whether it ran.
        StandardOutPath = "/Users/${user}/Library/Logs/vorssaint.log";
        StandardErrorPath = "/Users/${user}/Library/Logs/vorssaint.log";
      };
    };
  };
}
