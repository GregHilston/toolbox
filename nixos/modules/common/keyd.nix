# Caps Lock as the voice-input key (Linux half).
#
# keyd remaps Caps Lock at the evdev level to F18, held for as long as the key
# is down. Caps Lock never toggles caps. Handy binds that F18 as its
# push-to-talk key — the package itself is a GUI/per-user app, so it lives in
# ../home/default.nix behind the same custom.desktop.enable gate, per
# nixos/CLAUDE.md's app-placement rule.
#
# The macOS half is Karabiner-Elements + FluidVoice — see dot/karabiner/.
# Both platforms emit F18 for dictation. No tap = Escape on either: a tap/hold
# split delays every recording, and Escape has its own key.
#
# Gated on custom.desktop.enable (isengard, mines): dictation needs a graphical
# session and audio, so the headless hosts and rohan's TTY writerdeck skip it.
#
# NOT YET EXERCISED ON LINUX. The macOS half worked end to end on moria with
# Handy; this half is verified only by eval. The risk worth knowing when you do
# deploy it: Handy's X11 hotkey path has historically delivered key-press more
# reliably than key-release, and push-to-talk needs the release. If a hold starts
# recording and never stops, switch Handy to toggle mode rather than chasing keyd.
# Test on isengard first — mines is RAM-capped and OOM-prone (see nixos/CLAUDE.md).
{
  config,
  lib,
  ...
}:
lib.mkIf config.custom.desktop.enable {
  services.keyd = {
    enable = true;
    keyboards.default = {
      # The wildcard only matches devices keyd identifies as keyboards, so this
      # won't grab pointers.
      ids = ["*"];
      settings.main.capslock = "f18";
    };
  };
}
