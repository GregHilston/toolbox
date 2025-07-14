{
  pkgs,
  inputs,
  ...
}: {
  home.file = {
    "Pictures/Wallpapers" = {
      source = ./Wallpapers;
      recursive = true;
    };
    ".face.icon".source = ./face.png;
    ".config/face.png".source = ./face.png;
    ".config/swappy/config".text = ''
      [Default]
      save_dir=/home/ghilston/Pictures/Screenshots
      save_filename_format=swappy-%Y%m%d-%H%M%S.png
      show_panel=false
      line_size=5
      text_size=20
      text_font=Ubuntu
      paint_mode=brush
      early_exit=true
      fill_shape=false
    '';
    ".config/wpaperd/config.toml".text = ''
      [default]
       path = "./Wallpapers/"
       duration = "30m"
       transition-time = 600
    '';
  };
  # systemd.user.services.wpaperd = {
  #   Unit = {
  #     description = "wpaperd wallpaper daemon";
  #     wantedBy = ["sway-session.target"];
  #     after = ["sway-session.target"];
  #   };
  #   Service = {
  #     Type = "simple";
  #     ExecStart = "${pkgs.wpaperd}/bin/wpaperd -d";
  #     ExecStartPre = "${pkgs.coreutils}/bin/mkdir -p ~/.cache/fontconfig"; # Ensure cache directory
  #     Restart = "on-failure";
  #     RestartSec = 5;
  #   };
  # };
}
