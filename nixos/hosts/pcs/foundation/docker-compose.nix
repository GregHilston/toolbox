{
  pkgs,
  vars,
  lib,
  config,
  ...
}: let
  cfg = config.docker-compose;
in {
  options.docker-compose = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Enable docker-compose module";
    };
  };
  config = lib.mkIf cfg.enable {
    # Only enable either docker or podman -- Not both
    virtualisation = {
      libvirtd.enable = false;
      docker.enable = true;
      podman.enable = false;
    };
    programs = {
      virt-manager.enable = false;
    };
    environment.systemPackages = with pkgs; [
      docker-compose
      # virt-viewer # View Virtual Machines
    ];
    users.users.${vars.user.name}.extraGroups = ["docker"];
  };
}
