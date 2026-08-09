{lib, ...}: {
  imports = [
    ./hardware-configuration.nix
    ../../../modules/common
  ];

  networking.hostName = "isengard";

  # GUI host: pulls in the KDE Plasma stack (../../../modules/common/desktop.nix)
  # and the GUI home packages (../../../modules/home/default.nix reads this
  # back via osConfig).
  custom.desktop.enable = true;

  boot.loader.grub = {
    enable = true;
    device = "/dev/sda";
    useOSProber = true;
  };

  # Disable auto-reboot for laptop - updates download but reboot manually when convenient
  system.autoUpgrade.allowReboot = lib.mkForce false;

  powerManagement.powertop.enable = true;

  hardware.bluetooth.enable = true; # enables support for Bluetooth
  hardware.bluetooth.powerOnBoot = true; # powers up the default Bluetooth controller on boot
}
