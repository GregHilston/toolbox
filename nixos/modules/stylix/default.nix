{pkgs, ...}: let
  opacity = 0.95;
  fontSize = 11;
in {
  stylix = {
    enable = true;
    image = ./a-house-in-the-snow.png;
    polarity = "dark";
    base16Scheme = "${pkgs.base16-schemes}/share/themes/gruvbox-dark-medium.yaml";

    fonts = {
      # Set each font family individually
      serif = {
        package = pkgs.dejavu_fonts;
        name = "DejaVu Serif";
      };
      sansSerif = {
        package = pkgs.dejavu_fonts;
        name = "DejaVu Sans";
      };
      monospace = {
        # CHANGED: Use the new individual package for JetBrains Mono Nerd Font
        package = pkgs.nerd-fonts.jetbrains-mono; # This is the corrected line
        name = "JetBrainsMono Nerd Font Mono";
      };
      # Optionally, you can add emoji support
      # emoji = {
      #   package = pkgs.noto-fonts-emoji;
      #   name = "Noto Color Emoji";
      # };

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
