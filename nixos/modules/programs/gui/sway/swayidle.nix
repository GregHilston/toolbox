{pkgs, ...}: {
  services.swayidle = {
    enable = true;
    events = [
      {
        event = "before-sleep";
        command = "${pkgs.swaylock-effects}/bin/swaylock";
      }
      {
        event = "lock";
        command = "${pkgs.swaylock-effects}/bin/swaylock";
      }
    ];
    timeouts = [
      {
        timeout = 300; # 5 min
        command = "${pkgs.swaylock-effects}/bin/swaylock -fF";
      }
      {
        timeout = 900; # 15 minutes (900 seconds)
        command = "${pkgs.systemd}/bin/systemctl suspend";
      }
    ];
  };
}
