{pkgs, ...}: {
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
      device = "192.168.1.2:/mnt/user/data";
      fsType = "nfs";
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    };

    # Media share
    "/mnt/media" = {
      device = "192.168.1.2:/mnt/user/media";
      fsType = "nfs";
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    };

    # YouTube downloads
    "/mnt/youtube-dl" = {
      device = "192.168.1.2:/mnt/user/youtube-dl";
      fsType = "nfs";
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    };

    # Nextcloud data (separate from container config)
    "/nextcloud-data" = {
      device = "192.168.1.2:/mnt/user/nextcloud_data";
      fsType = "nfs";
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    };

    # Backup share on Unraid
    "/unraid-backup" = {
      device = "192.168.1.2:/mnt/user/backup";
      fsType = "nfs";
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    };

    # Webcam storage
    "/webcam" = {
      device = "192.168.1.2:/mnt/user/webcam";
      fsType = "nfs";
      options = ["x-systemd.automount" "noauto" "x-systemd.idle-timeout=600"];
    };
  };
}
