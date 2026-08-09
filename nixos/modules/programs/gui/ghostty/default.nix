_: {
  programs.ghostty = {
    enable = true;
    settings = {
      copy-on-select = true;
      clipboard-read = "allow";
      clipboard-write = "allow";

      # macOS muscle memory: the Mac Command key maps to Super inside a VM guest,
      # so bind Super+C/Super+V (and the Shift variants) to copy/paste. Harmless on
      # bare-metal Linux hosts too. keybind is a duplicate-key list.
      keybind = [
        "super+c=copy_to_clipboard"
        "super+v=paste_from_clipboard"
        "super+shift+c=copy_to_clipboard"
        "super+shift+v=paste_from_clipboard"
      ];
    };
  };
}
