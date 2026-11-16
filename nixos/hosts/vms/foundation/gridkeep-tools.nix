# Home-manager module: what a gridkeep orchestrator host needs on PATH, and
# pi's stowed config. Replaces the hand-made ~/lptools on foundation.
{
  lib,
  pkgs,
  ...
}: {
  # Gridkeep's gate pins godot 4.7.2 and gdscript-formatter 0.27.0 exactly.
  # nixpkgs' godot is patched with the X11, GL and audio libraries the
  # screenshot harness loads, so no LD_LIBRARY_PATH wrapper is needed.
  home.packages = with pkgs; [
    godot_4
    gdscript-formatter
    gdtoolkit_4 # gdlint, gdformat
    sqlite
  ];

  # `assertions` fails the build when nixpkgs moves off a pinned version.
  assertions = [
    {
      assertion = lib.hasPrefix "4.7.2" pkgs.godot_4.version;
      message = "gridkeep needs godot 4.7.2, nixpkgs has ${pkgs.godot_4.version}";
    }
    {
      assertion = pkgs.gdscript-formatter.version == "0.27.0";
      message = "gridkeep needs gdscript-formatter 0.27.0, nixpkgs has ${pkgs.gdscript-formatter.version}";
    }
  ];

  # Like moria: stow dot/pi (extensions, prompts, permission policy). The
  # generated models.json is ignored: home-manager writes it. Must
  # run before installPiPackages, which npm-installs the stowed extensions.
  home.activation.stowPi = lib.hm.dag.entryBetween ["installPiPackages"] ["writeBoundary"] ''
    DOTFILES="$HOME/Git/toolbox/dot"
    if [ -d "$DOTFILES/pi" ]; then
      cd "$DOTFILES"
      # --no-folding: pi writes sessions and logs under ~/.pi.
      ${pkgs.stow}/bin/stow -v --no-folding -t "$HOME" \
        --ignore='/models\.json$' pi 2>&1 \
        || echo "stow: conflict for pi: remove the hand-made link it names, then re-run home-manager"
    fi
  '';
}
