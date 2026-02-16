{pkgs, ...}: {
  programs.swaylock = {
    enable = true;
    package = pkgs.swaylock-effects;

    settings = {
      screenshots = true;
      daemonize = true;
      # Makes it so the circle doesn't show up looking for your password
      # ignore-empty-password = true;
      clock = true;
      indicator = true;
      effect-blur = "10x5";
    };
  };
}
