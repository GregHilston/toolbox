{
  lib,
  pkgs,
  vars,
  ...
}: {
  imports = [
    ./hardware-configuration.nix
    ../../../modules/common
  ];

  networking.hostName = "home-lab";

  boot.loader.grub = {
    enable = true;
    device = "/dev/sda";
    useOSProber = false;
  };

  # Proxmox/QEMU guest support
  services.spice-vdagentd.enable = true;
  services.qemuGuest.enable = true;

  # Shared sshd settings come from ../../../modules/common.
  services.openssh.enable = true;

  # Docker configuration for home-lab services
  virtualisation.docker.autoPrune = {
    enable = true;
    dates = "weekly";
  };

  # Disable firewall - services are protected by Tailscale/Caddy
  # All 60+ docker services need various ports
  networking.firewall.enable = false;

  # NFS client support
  environment.systemPackages = with pkgs; [
    nfs-utils
  ];

  # NFS mounts for Unraid shares — mountpoint -> Unraid share name.
  # These match the paths expected by docker-compose.yaml. Every one is the
  # same automounted NFS export off unraid, so the only per-entry facts are
  # those two strings.
  fileSystems =
    lib.mapAttrs (_: share: {
      device = "${vars.networking.hosts.unraid.lan}:/mnt/user/${share}";
      fsType = "nfs";
      # Automount on first access and unmount after 10 idle minutes, so boot
      # doesn't block on unraid being up.
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    }) {
      # TRaSH Guides structure: books, movies, music, tv, comics
      "/mnt/data" = "data";
      "/mnt/media" = "media";
      "/mnt/youtube-dl" = "youtube-dl";
      # Nextcloud user data, separate from the container's config volume
      "/nextcloud-data" = "nextcloud_data";
      "/unraid-backup" = "backup";
      "/webcam" = "webcam";
    };
}
