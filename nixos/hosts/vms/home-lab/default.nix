{...}: {
  imports = [
    ./hardware-configuration.nix
    ../../../modules/common
    ../../../modules/services/ssh.nix
    ../../../modules/services/gaming.nix
  ];

  networking.hostName = "home-lab";

  boot.loader.grub = {
    enable = true;
    device = "/dev/sda"; # Typical for VMs
    useOSProber = false; # Usually not needed in VMs
  };

  gaming.enable = true;

  services.spice-vdagentd.enable = true;
  services.qemuGuest.enable = true;
  services.ssh.enable = true;
}
