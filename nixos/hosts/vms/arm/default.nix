{
  inputs,
  outputs,
  lib,
  config,
  pkgs,
  vars,
  ...
}: {
  imports = [
    ./hardware-configuration.nix
    ../../../modules/common
  ];

  # Add these kernel modules for ARM virtualization
  boot.initrd.availableKernelModules = [
    "virtio_pci" # Virtio PCI devices
    "virtio_blk" # Block storage (disks)
    "virtio_net" # Network interfaces
    "virtio_mmio" # Memory-mapped I/O
    "ext4" # Root filesystem support
    "nvme" # If using NVMe storage
  ];

  # Ensure virtio modules are included in initrd
  boot.initrd.kernelModules = [
    "virtio_pci"
    "virtio_blk"
    "virtio_net"
  ];

  networking.hostName = "nixos-vm";

  # Use the systemd-boot EFI boot loader.
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  services.spice-vdagentd.enable = true;
  services.qemuGuest.enable = true;

  services.openssh = {
    enable = true;
    ports = [22];
    settings = {
      PasswordAuthentication = true;
      AllowUsers = null; # Allows all users by default. Can be [ "user1" "user2" ]
      UseDns = true;
      X11Forwarding = false;
      PermitRootLogin = "prohibit-password"; # "yes", "without-password", "prohibit-password", "forced-commands-only", "no"
    };
  };
}
