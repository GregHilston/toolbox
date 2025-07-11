{
  pkgs,
  lib,
  ...
}:
with lib; {
  # Configure & Theme Waybar
  programs.waybar = {
    enable = true;
    package = pkgs.waybar;
    settings = [
      {
        layer = "top";
        position = "top";
        modules-center = ["sway/workspaces" "clock"];
        modules-left = [
          "custom/startmenu"
          "sway/window"
          "pulseaudio"
          "cpu"
          "memory"
          "idle_inhibitor"
        ];
        modules-right = [
          "custom/hyprbindings"
          "custom/notification"
          "battery"
          "tray"
          "custom/exit"
        ];

        "sway/workspaces" = {
          format = "{name}";
          format-icons = {
            default = " ";
            active = " ";
            urgent = " ";
          };
          on-scroll-up = "hyprctl dispatch workspace e+1";
          on-scroll-down = "hyprctl dispatch workspace e-1";
        };
        "clock" = {
          format = " {:L%I:%M %p}";
          tooltip = true;
          tooltip-format = ''
            <big>{:%A, %d.%B %Y }</big>
            <tt><small>{calendar}</small></tt>'';
        };
        "sway/window" = {
          max-length = 22;
          separate-outputs = false;
          rewrite = {"" = " 🙈 No Windows? ";};
        };
        "memory" = {
          interval = 5;
          format = " {}%";
          tooltip = true;
        };
        "cpu" = {
          interval = 5;
          format = " {usage:2}%";
          tooltip = true;
        };
        "disk" = {
          format = " {free}";
          tooltip = true;
        };
        "network" = {
          format-icons = ["󰤯" "󰤟" "󰤢" "󰤥" "󰤨"];
          format-ethernet = " {bandwidthDownOctets}";
          format-wifi = "{icon} {signalStrength}%";
          format-disconnected = "󰤮";
          tooltip = false;
        };
        "tray" = {spacing = 12;};
        "pulseaudio" = {
          format = "{icon} {volume}% {format_source}";
          format-bluetooth = "{volume}% {icon} {format_source}";
          format-bluetooth-muted = " {icon} {format_source}";
          format-muted = " {format_source}";
          format-source = " {volume}%";
          format-source-muted = "";
          format-icons = {
            headphone = "";
            hands-free = "";
            headset = "";
            phone = "";
            portable = "";
            car = "";
            default = ["" "" ""];
          };
          on-click = "sleep 0.1 && pavucontrol";
        };
        "custom/exit" = {
          tooltip = false;
          format = "";
          on-click = "sleep 0.1 && wlogout";
        };
        "custom/startmenu" = {
          tooltip = false;
          format = "";
          # exec = "rofi -show drun";
          on-click = "sleep 0.1 && rofi-launcher";
        };
        "custom/hyprbindings" = {
          tooltip = false;
          format = "󱕴";
          on-click = "sleep 0.1 && list-hypr-bindings";
        };
        "idle_inhibitor" = {
          format = "{icon}";
          format-icons = {
            activated = "";
            deactivated = "";
          };
          tooltip = "true";
        };
        "custom/notification" = {
          tooltip = false;
          format = "{icon} {}";
          format-icons = {
            notification = "<span foreground='red'><sup></sup></span>";
            none = "";
            dnd-notification = "<span foreground='red'><sup></sup></span>";
            dnd-none = "";
            inhibited-notification = "<span foreground='red'><sup></sup></span>";
            inhibited-none = "";
            dnd-inhibited-notification = "<span foreground='red'><sup></sup></span>";
            dnd-inhibited-none = "";
          };
          return-type = "json";
          exec-if = "which swaync-client";
          exec = "swaync-client -swb";
          on-click = "sleep 0.1 && task-waybar";
          escape = true;
        };
        "battery" = {
          states = {
            warning = 30;
            critical = 15;
          };
          format = "{icon} {capacity}%";
          format-charging = "󰂄 {capacity}%";
          format-plugged = "󱘖 {capacity}%";
          format-icons = ["󰁺" "󰁻" "󰁼" "󰁽" "󰁾" "󰁿" "󰂀" "󰂁" "󰂂" "󰁹"];
          on-click = "";
          tooltip = false;
        };
      }
    ];
    style = concatStrings [
      ''
        * {
          font-family: Fira-Mono Nerd Font;
          font-size: 16px;
          border-radius: 0px;
          border: none;
          min-height: 0px;
        }
        window#waybar {
          background: rgba(0,0,0,0);
        }
        #workspaces {
          margin: 4px 4px;
          padding: 5px 5px;
          border-radius: 16px;
        }
        #workspaces button {
          font-weight: bold;
          padding: 0px 5px;
          margin: 0px 3px;
          border-radius: 16px;
          opacity: 0.5;
          color: #ebdbb2;
          background: linear-gradient(45deg, #fb4934, #83a598);
        }
        #workspaces button.active {
          opacity: 1.0;
          min-width: 40px;
          color: #282828;
          background: linear-gradient(45deg, #b8bb26, #fabd2f);
        }
        #workspaces button:hover {
          color: #282828;
          background: linear-gradient(45deg, #d3869b, #8ec07c);
          opacity: 0.8;
        }
        tooltip {
          background: #282828;
          border: 1px solid #fb4934;
          border-radius: 12px;
        }
        tooltip label {
          color: #fb4934;
        }
        #window, #pulseaudio, #cpu, #memory, #idle_inhibitor {
          font-weight: bold;
          margin: 8px 0px;
          margin-left: 7px;
          padding: 4px 18px;
          background: #7c6f64;
          color: #282828;
          border-radius: 0px;
        }
        #custom-startmenu {
          color: #b8bb26;
          background: #504945;
          font-size: 28px;
          margin: 0px;
          padding: 0px 30px 0px 15px;
          border-radius: 0px;
        }
        #custom-hyprbindings, #network, #battery,
        #custom-notification, #tray, #custom-exit {
          font-weight: bold;
          background: #d65d0e;
          color: #282828;
          margin: 4px 0px;
          margin-right: 7px;
          border-radius: 0px;
          padding: 0px 18px;
        }
        #clock {
          font-weight: bold;
          color: #282828;
          background: linear-gradient(90deg, #d3869b, #8ec07c);
          margin: 0px;
          padding: 0px 15px 0px 30px;
          border-radius: 0px;
        }
      ''
    ];
  };
}
