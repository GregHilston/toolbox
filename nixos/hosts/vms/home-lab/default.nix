{
  pkgs,
  vars,
  ...
}: {
  imports = [
    ./hardware-configuration.nix
    ../../../modules/common
    ../../../modules/services/ssh.nix
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
  services.ssh.enable = true;

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

  # NFS mounts for Unraid shares
  # These match the paths expected by docker-compose.yaml
  fileSystems = {
    # Main data share (TRaSH Guides structure: books, movies, music, tv, comics)
    "/mnt/data" = {
      device = "${vars.networking.hosts.unraid.lan}:/mnt/user/data";
      fsType = "nfs";
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    };

    # Media share
    "/mnt/media" = {
      device = "${vars.networking.hosts.unraid.lan}:/mnt/user/media";
      fsType = "nfs";
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    };

    # YouTube downloads
    "/mnt/youtube-dl" = {
      device = "${vars.networking.hosts.unraid.lan}:/mnt/user/youtube-dl";
      fsType = "nfs";
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    };

    # Nextcloud data (separate from container config)
    "/nextcloud-data" = {
      device = "${vars.networking.hosts.unraid.lan}:/mnt/user/nextcloud_data";
      fsType = "nfs";
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    };

    # Backup share on Unraid
    "/unraid-backup" = {
      device = "${vars.networking.hosts.unraid.lan}:/mnt/user/backup";
      fsType = "nfs";
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    };

    # Webcam storage
    "/webcam" = {
      device = "${vars.networking.hosts.unraid.lan}:/mnt/user/webcam";
      fsType = "nfs";
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    };
  };
}
