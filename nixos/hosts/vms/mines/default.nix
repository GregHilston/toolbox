# nixos/hosts/vms/mines/default.nix
{
  lib,
  pkgs,
  ...
}: {
  # Imports your common/default.nix to share settings
  imports = [
    ../../../modules/common
    # run `sudo nixos-generate-config --show-hardware-config > hardware-configuration.nix` to generate
    ./hardware-configuration.nix
  ];

  # VMWare Tools
  virtualisation.vmware.guest.enable = true;

  # Hardware Graphics Acceleration for VMware Fusion
  # Enables 3D acceleration using Mesa's SVGA driver (vmwgfx module)
  # This dramatically improves rendering performance and enables GPU acceleration
  # in the VM, resulting in smoother mouse movement and better graphics performance.
  # Reference: https://github.com/mitchellh/nixos-config/commit/62b0e17fd6b422aa89115681f3cb43cd5711a898
  # Note: enable32Bit is not available on aarch64 systems
  hardware.graphics.enable = true;

  # Use the systemd-boot EFI boot loader.
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # VMware graphics kernel module
  # The vmwgfx module provides the VMware SVGA display driver needed for
  # hardware-accelerated 3D graphics in VMware Fusion. This is critical for
  # proper graphics performance on both x86_64 and aarch64 platforms.
  boot.kernelModules = ["vmwgfx"];

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

    # gtkmm3: Required for VMware user tools clipboard on aarch64
    # Without this, clipboard integration between the VM and macOS host may not
    # function properly on ARM-based systems (Apple Silicon).
    # Reference: Mitchell Hashimoto's vm-shared.nix configuration
    gtkmm3
  ];

  # Disable NixOS-managed VS Code on this VM
  # VS Code runs on the macOS host and connects to this VM via Remote-SSH
  #
  # Architecture:
  # ┌─────────────────────────┐
  # │   macOS (Host)          │
  # │  VS Code (GUI app)      │ ← Extensions managed here normally
  # │  + Remote-SSH extension │
  # └────────────┬────────────┘
  #              │ SSH Connection
  #              ▼
  # ┌─────────────────────────┐
  # │   NixOS VM (Guest)      │
  # │  VS Code Server         │ ← Auto-installed by VS Code
  # │  (runs in background)   │
  # │  Your code, git, etc.   │
  # └─────────────────────────┘
  #
  # nix-ld is already enabled in common/default.nix to support VS Code Server
  # See modules/programs/gui/vscode/default.nix for extension reference list
  programs.vscode.enable = lib.mkForce false;
}
