{
  pkgs,
  inputs,
  ...
}: {
  programs.neovim = {
    enable = true;
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

      # Language Servers (LSP)
      erlang_26
      elixir
      elixir-ls
      lua-language-server
      nil
      nixd
      nodePackages_latest.svelte-language-server
      pyright
      nodePackages."@tailwindcss/language-server"
      gopls

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
