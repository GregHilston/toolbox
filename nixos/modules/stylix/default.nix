{ pkgs, ... }: 

let
  opacity = 0.95;
  fontSize = 11;
in
{
  stylix = {
    enable = true;
    image = ./a-house-in-the-snow.png;
    polarity = "dark";
    base16Scheme = "${pkgs.base16-schemes}/share/themes/gruvbox-dark-medium.yaml";

    fonts = {
      monospace = {
        # package = pkgs.nerdfonts.jetbrains-mono;
        package = pkgs.nerdfonts.override { fonts = [ "JetBrainsMono" ]; };
        name = "JetBrainsMono Nerd Font Mono";
      };
      sansSerif = {
        package = pkgs.dejavu_fonts;
        name = "DejaVu Sans";
      };
      serif = {
        package = pkgs.dejavu_fonts;
        name = "DejaVu Serif";
      };

      sizes = {
        applications = fontSize;
        desktop = fontSize;
        popups = fontSize;
        terminal = fontSize;
      };
    };

    opacity = {
      applications = opacity;
      terminal = opacity;
      desktop = opacity;
      popups = opacity;
    };
  };
}
