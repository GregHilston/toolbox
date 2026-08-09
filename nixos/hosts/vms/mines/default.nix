# nixos/hosts/vms/mines/default.nix
{
  lib,
  pkgs,
  vars,
  ...
}: {
  # Imports your common/default.nix to share settings
  imports = [
    ../../../modules/common
    # run `sudo nixos-generate-config --show-hardware-config > hardware-configuration.nix` to generate
    ./hardware-configuration.nix
  ];

  # GUI host: pulls in the KDE Plasma stack (../../../modules/common/desktop.nix)
  # and the GUI home packages (../../../modules/home/default.nix reads this
  # back via osConfig).
  custom.desktop.enable = true;

  # Pin the Plasma X11 session (Plasma 6 otherwise defaults to Wayland,
  # defaultSession = "plasma"). VMware Fusion's host<->guest clipboard and
  # drag-drop are driven by open-vm-tools' `vmware-user`, which the
  # virtualisation.vmware.guest module launches ONLY in the X11 session (via
  # services.xserver.displayManager.sessionCommands -> vmware-user-suid-wrapper).
  # Under Wayland that daemon never starts and the clipboard is dead; open-vm-tools
  # Wayland clipboard support is not there yet for KDE. X11 is the seamless path.
  services.displayManager.defaultSession = "plasmax11";

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

  # Enable SSH for Remote-SSH connections from macOS VS Code.
  # Shared sshd settings come from ../../../modules/common.
  services.openssh.enable = true;

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

  # Disable the EDNS0 resolver option (drops `options edns0` from resolv.conf).
  #
  # VMware Fusion's NAT DNS proxy (192.168.180.2) cannot handle EDNS0 queries: with
  # it enabled, every glibc lookup (git, curl, ping, nix substituters) fails with
  # "server returned answer with no data", while `host`/`dig` mislead by resolving
  # fine. Confirmed by isolation — the exact same NAT nameserver resolves correctly
  # the instant `options edns0` is removed. Raw IP routing is unaffected. This is the
  # minimal, root-cause fix; no need to hardcode public resolvers.
  networking.resolvconf.dnsExtensionMechanism = false;

  # zram swap: give the kernel reclaimable headroom so a memory spike doesn't
  # instantly OOM-kill the foreground scope (tmux/Claude Code/nix eval). The VM
  # ships with NO swap (Swap: 0B), so any transient overshoot of its RAM cap goes
  # straight to the OOM killer. zram is compressed RAM-backed swap — no disk I/O,
  # ideal for a VM — sized at 50% of RAM (zstd ~3:1, so ~15GiB device costs ~5GiB).
  # Complementary host-side lever: raise this guest's RAM in VMware Fusion (moria
  # has 128GB; the guest currently sees ~31GiB) if builds still press against it.
  zramSwap = {
    enable = true;
    memoryPercent = 50;
  };

  # NFS server to share VM filesystem with macOS host
  # Enables performant filesystem access from macOS apps (Bruno, Finder, etc.)
  services.nfs.server = {
    enable = true;
    exports = ''
      /home/${vars.user.name} *(rw,sync,no_subtree_check,all_squash,anonuid=1000,anongid=1000,insecure)
    '';
  };

  # Passwordless sudo for VM development workflow
  # Safe for VM-only environment, reduces development friction
  # Reference: mitchellh-nixos-config/machines/vm-shared.nix:54-55
  security.sudo.wheelNeedsPassword = false;

  # VMware Fusion specific packages
  environment.systemPackages = with pkgs; [
    # gtkmm3: required by open-vm-tools' `vmware-user`, the GTK process that syncs
    # the X11 clipboard between the VM and the macOS host. Without it the clipboard
    # integration silently fails on aarch64 (Apple Silicon).
    # Reference: Mitchell Hashimoto's vm-shared.nix configuration.
    gtkmm3

    # xrandr-auto: fallback that forces the guest display to refit the Fusion
    # window. On X11 with vmware-user running, KDE's kscreen usually auto-resizes;
    # this is here for when the udev/RandR event isn't honored. Verify the output
    # name with `xrandr` if it stops working (vmwgfx names it Virtual-1).
    (writeShellScriptBin "xrandr-auto" ''
      exec ${xorg.xrandr}/bin/xrandr --output Virtual-1 --auto
    '')
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
  # See modules/programs/gui/vscode/default.nix for extension reference list.
  # Disabling via the module's own gate (not mkForce) means the extension list is
  # never evaluated on this host.
  home-manager.users.${vars.user.name} = {
    custom.programs.vscode.enable = false;

    # HiDPI: keep the pointer from being tiny on the Mac's Retina panel.
    home.pointerCursor = {
      name = "breeze_cursors";
      package = pkgs.kdePackages.breeze;
      size = 48;
      x11.enable = true;
    };

    # HiDPI global scale, declaratively. Under the Plasma X11 session (which we pin
    # above for the VMware clipboard) startplasma-x11 enforces its OWN font DPI —
    # that's why `Xft.dpi` reads 96 and everything is tiny on the Retina panel, and
    # why a bare `services.xserver.dpi` (Mitchell Hashimoto's i3 approach) gets
    # overridden here. The Plasma-native lever is `forceFontDPI` in ~/.config/kcmfonts
    # — exactly what System Settings -> Text & Fonts -> "Force fonts DPI" writes. It
    # drives font-metric-based scaling across Qt/Plasma and Ghostty. `force = true`
    # overwrites Plasma's runtime-written file instead of trying to back it up (which
    # would hit the .backup-clobber activation failure). 144 ≈ 1.5x (96 = 100%); bump
    # to 168 (~1.75x) or 192 (2x) if still small, lower if it overshoots. On X11 this
    # scales fonts/most Qt UI; pixel-fixed panel icons don't scale (an X11 limitation
    # — true fractional scaling is Wayland-only, which we traded away for clipboard).
    xdg.configFile."kcmfonts".force = true;
    xdg.configFile."kcmfonts".text = ''
      [General]
      forceFontDPI=144
    '';
  };
}
