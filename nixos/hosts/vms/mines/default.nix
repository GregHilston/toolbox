# nixos/hosts/vms/mines/default.nix
{lib, ...}: {
  # Imports your common/default.nix to share settings
  imports = [
    ../../../modules/common
    # run `sudo nixos-generate-config --show-hardware-config > hardware-configuration.nix` to generate
    ./hardware-configuration.nix
  ];

  # VMWare Tools
  virtualisation.vmware.guest.enable = true;

  # Use the systemd-boot EFI boot loader.
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # Add these kernel modules for ARM virtualization
  boot.initrd.availableKernelModules = [
    # "virtio_pci" # Virtio PCI devices
    # "virtio_blk" # Block storage (disks)
    # "virtio_net" # Network interfaces
    # "virtio_mmio" # Memory-mapped I/O
    "ext4" # Root filesystem support
    # "nvme" # If using NVMe storage
  ];

  # Ensure virtio modules are included in initrd
  # boot.initrd.kernelModules = [
  #   "virtio_pci"
  #   "virtio_blk"
  #   "virtio_net"
  # ];
  # Override the hostname from "nixos-vm" to "mines".
  networking.hostName = lib.mkDefault "mines";

  # VMware Fusion specific packages
  environment.systemPackages = with pkgs; [
    # wl-clipboard: Required for Wayland clipboard integration with VMware Fusion
    # Enables proper clipboard sync between Alacritty terminal and macOS host
    wl-clipboard
  ];
}
