# Launch Handy at login (macOS half of "hold Caps Lock to dictate").
#
# Handy is a menu-bar app, so it has to already be running for the F18 that
# Karabiner emits on a Caps Lock hold to land anywhere. Without this you get a
# silent failure mode: Caps Lock behaves correctly, nothing dictates.
#
# Why an `open -a` agent instead of the inner binary, why no KeepAlive, and why
# not Handy's own `autostart_enabled` setting: nixos/CLAUDE.md → "Launching GUI
# apps at login". Handy is one of two users of that pattern; ./ice.nix is the
# other. The cask itself is in ./homebrew-base.nix; the Linux half is the systemd
# user service in ../home/default.nix.
#
# Handy-specific: imported per-host (citadel, moria) rather than from
# ./common.nix, because headless dungeon has no microphone or interactive user to
# dictate for. Add the import to its host file if that ever changes.
{vars, ...}: {
  launchd.user.agents.handy = {
    command = "/usr/bin/open -g -j -a /Applications/Handy.app";
    serviceConfig = {
      RunAtLoad = true;
      # Where "Unable to find application named 'Handy'" shows up if the cask
      # hasn't installed yet on a fresh host.
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/handy.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/handy.log";
    };
  };
}
