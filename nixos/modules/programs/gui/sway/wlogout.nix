{config, ...}: {
  programs.wlogout = {
    enable = true;
    layout = [
      {
        label = "shutdown";
        action = "sleep 1; systemctl poweroff";
        text = "Shutdown";
        keybind = "s";
      }
      {
        "label" = "reboot";
        "action" = "sleep 1; systemctl reboot";
        "text" = "Reboot";
        "keybind" = "r";
      }
      {
        "label" = "logout";
        "action" = "sleep 1; hyprctl dispatch exit";
        "text" = "Exit";
        "keybind" = "e";
      }
      {
        "label" = "suspend";
        "action" = "sleep 1; systemctl suspend";
        "text" = "Suspend";
        "keybind" = "u";
      }
      {
        "label" = "lock";
        "action" = "sleep 1; hyprlock";
        "text" = "Lock";
        "keybind" = "l";
      }
      {
        "label" = "hibernate";
        "action" = "sleep 1; systemctl hibernate";
        "text" = "Hibernate";
        "keybind" = "h";
      }
    ];
    style = ''
      * {
        font-family: "JetBrainsMono NF", FontAwesome, sans-serif;
        background-image: none;
        transition: 20ms;
      }
      window {
        background-color: rgba(40, 40, 40, 0.1); /* Gruvbox dark0 */
      }
      button {
        color: #928374; /* Gruvbox gray_245 */
        font-size:20px;
        background-repeat: no-repeat;
        background-position: center;
        background-size: 25%;
        border-style: solid;
        background-color: rgba(40, 40, 40, 0.3); /* Gruvbox dark0 */
        border: 3px solid #928374; /* Gruvbox gray_245 */
        box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);
      }
      button:focus,
      button:active,
      button:hover {
        color: #b8bb26; /* Gruvbox bright_green */
        background-color: rgba(40, 40, 40, 0.5); /* Gruvbox dark0 */
        border: 3px solid #b8bb26; /* Gruvbox bright_green */
      }
      #logout {
        margin: 10px;
        border-radius: 20px;
        background-image: image(url("icons/logout.png"));
      }
      #suspend {
        margin: 10px;
        border-radius: 20px;
        background-image: image(url("icons/suspend.png"));
      }
      #shutdown {
        margin: 10px;
        border-radius: 20px;
        background-image: image(url("icons/shutdown.png"));
      }
      #reboot {
        margin: 10px;
        border-radius: 20px;
        background-image: image(url("icons/reboot.png"));
      }
      #lock {
        margin: 10px;
        border-radius: 20px;
        background-image: image(url("icons/lock.png"));
      }
      #hibernate {
        margin: 10px;
        border-radius: 20px;
        background-image: image(url("icons/hibernate.png"));
      }
    '';
  };
}
