# Caps Lock as the voice-input key (Linux half).
#
# keyd remaps Caps Lock at the evdev level: quick tap = Escape, hold = F18 held
# for as long as the key is down (keyd sends the hold key_down on timer expiry
# and the key_up from its cache on physical release). Caps Lock never toggles
# caps. Handy binds that F18 as its push-to-talk key — the package itself is a
# GUI/per-user app, so it lives in ../home/default.nix behind the same
# custom.desktop.enable gate, per nixos/CLAUDE.md's app-placement rule.
#
# The macOS half is Karabiner-Elements + the Handy cask — see dot/karabiner/.
# Both platforms emit F18 so Handy needs one hotkey everywhere.
#
# THRESHOLD COUPLING: the 200 below is the tap/hold split and must equal BOTH
# Karabiner parameters in dot/karabiner/.config/karabiner/karabiner.json. keyd
# has one threshold where Karabiner has two; see that package's README for why
# they must stay equal to each other as well. Retune all three together.
#
# Known platform divergence, not worth fixing: when Caps Lock is chorded with
# another key inside the threshold, keyd resolves to the tap branch and emits
# Escape+X, while Karabiner suppresses the tap and emits just X. Nobody
# deliberately chords with Caps Lock, so both are acceptable.
#
# Gated on custom.desktop.enable (isengard, mines): dictation needs a graphical
# session and audio, so the headless hosts and rohan's TTY writerdeck skip it.
#
# NOT YET EXERCISED ON LINUX. The macOS half is confirmed working end to end on
# moria; this half is verified only by eval. The risk worth knowing when you do
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
      # timeout(<tap action>, <ms>, <hold action>) — argument order confirmed
      # against keyd's src/config.c, because `man keyd` has a typo here that
      # lists the same action for both branches.
      settings.main.capslock = "timeout(esc, 250, f18)";
    };
  };
}
