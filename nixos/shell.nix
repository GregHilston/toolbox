{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.git
    pkgs.vim
    pkgs.just
    pkgs.tmux
    pkgs.nixos-rebuild
  ];
}
