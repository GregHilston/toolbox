# Launch Ice at login on every Mac.
#
# Ice (jordanbaird-ice) is a menu bar manager: it hides the overflow icons that
# macOS otherwise silently drops behind the notch. It's a menu-bar-only app
# (LSUIElement = true in its Info.plist), so if it isn't running you don't get an
# error, you just get the stock cluttered menu bar back.
#
# Why an `open -a` agent instead of the inner binary, why no KeepAlive, and why
# not Ice's own Settings → General → "Launch Ice at login" toggle: nixos/CLAUDE.md
# → "Launching GUI apps at login". Ice is one of two users of that pattern;
# ./handy.nix is the other. The cask itself is in ./homebrew-base.nix.
#
# Ice-specific: imported from ./common.nix so all three Macs (moria, dungeon,
# citadel) get it without a per-host import — even headless dungeon has a menu bar
# worth managing over VNC. Contrast ./handy.nix, per-host on purpose. Ice's grants
# are Accessibility (move/hide items) + Screen Recording (item search, menu bar
# appearance); see docs/darwin-post-deploy.md.
{vars, ...}: {
  launchd.user.agents.ice = {
    command = "/usr/bin/open -g -j -a /Applications/Ice.app";
    serviceConfig = {
      RunAtLoad = true;
      # Where "Unable to find application named 'Ice'" shows up if the cask
      # hasn't installed yet on a fresh host.
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/ice.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/ice.log";
    };
  };
}
