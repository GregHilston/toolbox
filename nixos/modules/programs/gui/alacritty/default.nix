{
  config,
  pkgs,
  ...
}: {
  programs.alacritty = {
    enable = true;
    settings.selection.save_to_clipboard = true;
  };
}
