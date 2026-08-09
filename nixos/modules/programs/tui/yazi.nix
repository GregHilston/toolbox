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
      enable = true;
      # The `y` shell wrapper is defined in ../zsh (shellWrapperName only feeds
      # home-manager's programs.zsh, which we don't manage — see that header).
      settings = {
        mgr = {
          show_hidden = false;
          sort_dir_first = true;
          sort_by = "mtime";
          sort_reverse = true;
          linemode = "size";
          editor = "nvim";
        };
        preview = {
          max_width = 1920;
          max_height = 1080;
        };
      };
      # No starship.yazi plugin: the prompt here is powerlevel10k and the
      # starship binary is installed on no host, so `require("starship"):setup()`
      # only ever errored in yazi's header.
      plugins = {
        chmod = "${yazi-plugins}/chmod.yazi";
        full-border = "${yazi-plugins}/full-border.yazi";
        toggle-pane = "${yazi-plugins}/toggle-pane.yazi";
      };

      initLua = ''
        require("full-border"):setup()
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
