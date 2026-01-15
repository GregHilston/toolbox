{lib, ...}: {
  imports = [
    ./hardware-configuration.nix
    ../../../modules/common
  ];

  networking.hostName = "isengard";

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
