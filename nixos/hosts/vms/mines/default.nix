# nixos/hosts/vms/mines/default.nix
{lib, ...}: {
  # Imports your common/default.nix to share settings
  imports = [
    ../../../modules/common
    # run `sudo nixos-generate-config --show-hardware-config > hardware-configuration.nix` to generate
    ./hardware-configuration.nix
  ];

  # Use the systemd-boot EFI boot loader.
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

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
  # Override the hostname from "nixos-vm" to "mines".
  networking.hostName = lib.mkDefault "mines";

  # Add any other specific configurations for 'mines' here if it needs
  # anything truly unique or different compared to the generic ARM VM.
  # For example:
  # services.something-unique-to-mines.enable = true;
  # environment.systemPackages = with pkgs; [ specific-tool ];
}
