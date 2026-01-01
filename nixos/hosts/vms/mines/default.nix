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

  # Setup qemu so we can run x86_64 binaries on aarch64
  # Reference: mitchellh-nixos-config/machines/vm-aarch64.nix:8
  boot.binfmt.emulatedSystems = ["x86_64-linux"];

  # Share macOS host filesystem at /host
  # Provides read-write access to entire macOS filesystem with umask=22
  # Reference: mitchellh-nixos-config/machines/vm-aarch64.nix:21-32
  fileSystems."/host" = {
    fsType = "fuse./run/current-system/sw/bin/vmhgfs-fuse";
    device = ".host:/";
    options = [
      "umask=22" # New files readable by group/others, writable by owner only
      "uid=1000" # Files owned by ghilston user
      "gid=1000" # Files owned by ghilston group
      "allow_other" # Allow other users to access
      "auto_unmount" # Auto-unmount on failure
      "defaults"
    ];
  };

  # Enable SSH for Remote-SSH connections from macOS VS Code
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

  # Fix boot console mode for VMware/Parallels compatibility
  # Prevents "error switching console mode" on boot
  # Reference: mitchellh-nixos-config/machines/vm-shared.nix:41
  boot.loader.systemd-boot.consoleMode = "0";

  # VMware graphics kernel module
  # The vmwgfx module provides the VMware SVGA display driver needed for
  # hardware-accelerated 3D graphics in VMware Fusion. This is critical for
  # proper graphics performance on both x86_64 and aarch64 platforms.
  boot.kernelModules = ["vmwgfx"];

  # Override the hostname from "nixos-vm" to "mines".
  networking.hostName = lib.mkDefault "mines";

  # Disable firewall for VM NAT networking
  # Safe for VM with NAT, easier for web app testing
  # Reference: mitchellh-nixos-config/machines/vm-shared.nix:148-149
  networking.firewall.enable = false;

  # NFS server to share VM filesystem with macOS host
  # Enables performant filesystem access from macOS apps (Bruno, Finder, etc.)
  services.nfs.server = {
    enable = true;
    exports = ''
      /home/ghilston *(rw,sync,no_subtree_check,all_squash,anonuid=1000,anongid=1000,insecure)
    '';
  };

  # Passwordless sudo for VM development workflow
  # Safe for VM-only environment, reduces development friction
  # Reference: mitchellh-nixos-config/machines/vm-shared.nix:54-55
  security.sudo.wheelNeedsPassword = false;

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
