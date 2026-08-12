# Voice input: hold Caps Lock to dictate.
#
# Two halves, one hotkey:
#   keyd   — remaps Caps Lock at the evdev level. Quick tap = Escape, hold = F18
#            held for as long as you hold the key. Caps Lock never toggles caps.
#   handy  — local speech-to-text (Whisper / Parakeet, nothing leaves the host),
#            bound to that F18 in push-to-talk mode.
#
# The macOS equivalent is Karabiner-Elements + the Handy cask — see
# dot/karabiner/README.md. Both platforms emit F18 so Handy has one hotkey
# everywhere.
#
# Gated on custom.desktop.enable (isengard, mines): dictation needs a graphical
# session and audio, so the headless hosts and rohan's TTY writerdeck skip it.
{
  config,
  lib,
  pkgs,
  ...
}:
lib.mkIf config.custom.desktop.enable {
  services.keyd = {
    enable = true;
    keyboards.default = {
      ids = ["*"];
      # timeout(<tap action>, <ms>, <hold action>). Thresholds match the
      # Karabiner parameters in dot/karabiner/.config/karabiner/karabiner.json;
      # keep the two in sync so the gesture feels identical on both platforms.
      settings.main.capslock = "timeout(esc, 200, f18)";
    };
  };

  # xdotool is how Handy types the transcription into the focused window on X11
  # (both GUI hosts run Plasma on X11). Wayland would need wtype instead.
  environment.systemPackages = with pkgs; [
    handy
    xdotool
  ];
}
