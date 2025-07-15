{pkgs, ...}: {
  services.swayidle = {
    enable = true;
    events = [
      {
        event = "before-sleep";
        command = "${pkgs.swaylock-effects}/bin/swaylock-effects";
      }
      {
        event = "lock";
        command = "${pkgs.swaylock-effects}/bin/swaylock-effects";
      }
    ];
    timeouts = [
      {
        timeout = 300; # 5 min
        command = "${pkgs.swaylock-effects}/bin/swaylock-effects -fF";
      }
      {
        timeout = 900; # 15 minutes (900 seconds)
        command = "${pkgs.systemd}/bin/systemctl suspend";
      }
    ];
  };
}
