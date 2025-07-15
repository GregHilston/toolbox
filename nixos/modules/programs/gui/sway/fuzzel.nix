{pkgs, ...}: {
  programs.fuzzel = {
    enable = true;
    settings = {
      main = {
        terminal = "${pkgs.alacritty}/bin/alacritty";
      };
    };
  };
}
