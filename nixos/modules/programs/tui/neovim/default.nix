# https://github.com/water-sucks/nixed/blob/main/home/profiles/base/nvim/default.nix
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
      # https://github.com/neovim/nvim-lspconfig/blob/master/doc/server_configurations.md
      erlang_26
      elixir
      elixir_ls
      # inputs.next-ls
      # vimPlugins.elixir-tools-nvim
      lua-language-server
      nil
      nixd
      nodePackages_latest.svelte-language-server
      pyright
      nodePackages."@tailwindcss/language-server"

      # Formatters
      # https://github.com/stevearc/conform.nvim?tab=readme-ov-file#formatters
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
