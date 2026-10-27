# The Darwin workstation home profile.
#
# Layering: ../home/common.nix (identity) ← ../home/workstation.nix (CLI/dev
# baseline, shared with NixOS) ← this file (macOS-only bits). The
# useGlobalPkgs/useUserPackages/backupFileExtension/extraSpecialArgs wiring is
# shared with the NixOS hosts and lives in flake-modules/hosts.nix.
{
  inputs,
  vars,
  pkgs,
  ...
}: {
  home-manager.users.${vars.user.name} = {
    imports = [
      ../home/workstation.nix
    ];

    # Darwin-only packages. The shared TUI/CLI baseline is in
    # ../home/workstation.nix. pi-coding-agent comes from homebrew instead, for
    # faster updates.
    home.packages =
      (with pkgs; [
        # Fonts
        nerd-fonts.jetbrains-mono
        jetbrains-mono
      ])
      # GNU timeout alone: all of coreutils shadows BSD tools.
      ++ [
        (pkgs.runCommand "gnu-timeout" {} ''
          mkdir -p $out/bin && ln -s ${pkgs.coreutils}/bin/timeout $out/bin/timeout
        '')
      ];

    # mflux — Apple Silicon image generation CLI (pip install mflux, not a brew formula).
    # Installed as a global uv tool so `mflux-generate` is on PATH system-wide.
    # This lets the reproduce commands in imagine_loop HTML reports run without
    # needing to be inside the roger project directory.
    home.activation.install-mflux = inputs.home-manager.lib.hm.dag.entryAfter ["installPackages"] ''
      ${pkgs.uv}/bin/uv tool install --upgrade mflux 2>/dev/null || true
    '';

    # /bin/zsh reads terminfo before TERMINFO_DIRS exists.
    home.file.".terminfo" = {
      source = "${pkgs.ghostty-bin.terminfo}/share/terminfo";
      recursive = true;
    };

    custom.programs.pi.enable = true;
  };
}
