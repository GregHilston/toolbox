{
  config,
  lib,
  ...
}: let
  cfg = config.services.ssh;
in {
  options.services.ssh = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Enable SSH server with standard VM configuration";
    };
  };

  config = lib.mkIf cfg.enable {
    services.openssh = {
      enable = true;
      ports = [22];
      settings = {
        PasswordAuthentication = true;
        AllowUsers = null; # Allows all users by default
        UseDns = true;
        X11Forwarding = false;
        PermitRootLogin = "prohibit-password";
      };
    };
  };
}
