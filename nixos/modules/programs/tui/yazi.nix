{
  config,
  lib,
  pkgs,
  # inputs,
  ...
}: let
  yazi-plugins = pkgs.fetchFromGitHub {
    owner = "yazi-rs";
    repo = "plugins";
    rev = "ceb053f";
    hash = "sha256-yBcbvzWU2FI7vkeqL7+ZIoQboybaPIiH4fV9yMqdHlM=";
  };
in {
  options.custom.yazi.enable = lib.mkEnableOption "Enable Yazi file manager module";

  config = lib.mkIf config.custom.yazi.enable {
    programs.yazi = {
      # package = inputs.yazi.packages.${pkgs.system}.yazi;
      enable = true;
      shellWrapperName = "y";
      settings = {
        mgr = {
          show_hidden = false;
          sort_dir_first = true;
          sort_by = "mtime";
          sort_reverse = true;
          linemode = "size";
          editor = "hx";
        };
        preview = {
          max_width = 1920;
          max_height = 1080;
        };
      };
      plugins = {
        chmod = "${yazi-plugins}/chmod.yazi";
        full-border = "${yazi-plugins}/full-border.yazi";
        toggle-pane = "${yazi-plugins}/toggle-pane.yazi";
        starship = pkgs.fetchFromGitHub {
          owner = "Rolv-Apneseth";
          repo = "starship.yazi";
          rev = "6c639b4";
          sha256 = "sha256-bhLUziCDnF4QDCyysRn7Az35RAy8ibZIVUzoPgyEO1A=";
        };
      };

      initLua = ''
        require("full-border"):setup()
        require("starship"):setup()
      '';

      keymap.mgr.prepend_keymap = [
        {
          on = "T";
          run = "plugin toggle-pane max-preview";
          desc = "Maximize or restore the preview pane";
        }
        {
          on = [
            "c"
            "m"
          ];
          run = "plugin chmod";
          desc = "Chmod on selected files";
        }
      ];
    };
  };
}
