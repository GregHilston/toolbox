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
