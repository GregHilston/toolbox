{
  pkgs,
  vars,
  ...
}: {
  imports = [
    ../../../modules/darwin/common.nix
    ../../../modules/darwin/homebrew.nix
    ../../../modules/darwin/home.nix
  ];

  networking.hostName = "moria";

  # Moria-specific packages (Whisper for local transcription)
  home-manager.users.${vars.user.name}.home.packages = with pkgs; [
    whisper-ctranslate2
  ];
}
