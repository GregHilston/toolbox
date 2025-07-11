{
  config,
  pkgs,
  lib,
  ...
}: let
  mod = "Mod4";
in {
  wayland.windowManager.sway = {
    config = {
      modifier = mod;
      keybindings = lib.attrsets.mergeAttrsList [
        (lib.attrsets.mergeAttrsList (map (num: let
          ws = toString num;
        in {
          "${mod}+${ws}" = "workspace ${ws}";
          "${mod}+Ctrl+${ws}" = "move container to workspace ${ws}";
        }) [1 2 3 4 5 6 7 8 9 0]))

        (lib.attrsets.concatMapAttrs (key: direction: {
            "${mod}+${key}" = "focus ${direction}";
            "${mod}+Shift+${key}" = "move ${direction}";
          }) {
            h = "left";
            j = "down";
            k = "up";
            l = "right";
          })

        {
          "${mod}+Return" = "exec --no-startup-id ${pkgs.ghostty}/bin/ghostty";
          "${mod}+t" = "exec --no-startup-id ${pkgs.kitty}/bin/kitty";
          # "${mod}+space" =
          # "exec pkill wofi || wofi --normal-window --show drun --allow-images,run";
          "${mod}+Space" = "exec fuzzel";

          "${mod}+Ctrl+x" = "exit";
          "${mod}+y" = "exec emopicker9000";
          "${mod}+s" = "exec screenshootin";

          "${mod}+a" = "focus parent";
          "${mod}+d" = "exec rofi -show drun";
          "${mod}+e" = "layout toggle split";
          "${mod}+f" = "exec firefox";
          "${mod}+p" = ''
            exec /bin/sh -c "cat /home/jr/notes/2nd_brain/commands | ${pkgs.rofi}/bin/rofi -dmenu | ${pkgs.findutils}/bin/xargs ${pkgs.wtype}/bin/wtype"'';
          "Alt+Return" = "fullscreen toggle";
          "${mod}+c" = "exec bash -c 'cliphist list | ${pkgs.wofi}/bin/wofi --dmenu --width 800 --height 500 | cliphist decode | wl-copy'";
          "${mod}+v" = "split v";
          "${mod}+Shift+V" = "split h";
          "${mod}+z" = "layout stacking";
          "${mod}+Shift+W" = "exec wpaperd &";
          # "${mod}+Shift+Space" = "focus mode_toggle";
          "${mod}+n" = "exec thunar";
          "${mod}+w" = "layout tabbed";
          "${mod}+Tab" = "exec swayr switch-window";
          "${mod}+Shift+Tab" = "exec swayr switch-workspace-or-window";

          "${mod}+Shift+r" = "exec swaymsg reload";
          "--release Print" = "exec --no-startup-id ${pkgs.sway-contrib.grimshot}/bin/grimshot copy area";
          "${mod}+Ctrl+l" = "exec ${pkgs.swaylock-fancy}/bin/swaylock-fancy";
          "${mod}+q" = "kill";
          "${mod}+Backspace" = "kill";
          "Ctrl+Alt+Delete" = "exec wlogout";
        }
      ];
      focus.followMouse = true;
      workspaceAutoBackAndForth = true;
    };
    systemd.enable = true;
    wrapperFeatures = {gtk = true;};
  };
}
