{ pkgs, inputs, ... }:

{
  programs.neovim = {
    enable = true;
    package = inputs.neovim-nightly-overlay.packages.${pkgs.system}.default;
    defaultEditor = true;
    viAlias = true;
    vimAlias = true;
    extraLuaPackages = ps: [
      ps.lua
      ps.luarocks-nix
      ps.magick
    ];
    extraPackages = with pkgs; [
      imagemagick

      # Language Servers
      erlang_26
      elixir
      elixir_ls
      lua-language-server
      nil
      nixd
      nodePackages_latest.svelte-language-server
      pyright
      nodePackages."@tailwindcss/language-server"

      # Formatters
      black
      nixfmt-rfc-style
      nodePackages.prettier
      biome
      shfmt
      stylelint
      stylua
    ];
  };

  home.file.".config/nvim" = {
    source = ./nvim;
    recursive = true;
  };
}
