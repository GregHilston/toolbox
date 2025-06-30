{
  config,
  pkgs,
  ...
}: {
  # Enable the Nix daemon for multi-user support
  services.nix-daemon.enable = true;

  # Enable flakes and the new Nix CLI
  nix.settings.experimental-features = ["nix-command" "flakes"];

  # Set the state version (update if you know a newer one is needed)
  system.stateVersion = 4;

  # Specify the platform (Apple Silicon Mac)
  nixpkgs.hostPlatform = "aarch64-darwin";

  # Declare the main user
  users.users.ghilston = {
    name = "ghilston";
    home = "/Users/ghilston";
  };

  # Enable Zsh shell integration
  programs.zsh.enable = true;

  # Example system packages (edit as needed)
  environment.systemPackages = with pkgs; [
    neofetch
    vim
  ];
}
