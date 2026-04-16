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
    withRuby = true;
    withPython3 = true;
    extraLuaPackages = ps: [
      ps.lua
      ps.luarocks-nix
      ps.magick
    ];
    extraPackages = with pkgs; [
      imagemagick

      # Language Servers (LSP)
      erlang_27
      elixir
      elixir-ls
      lua-language-server
      nil
      nixd
      svelte-language-server
      pyright
      tailwindcss-language-server
      gopls

      # Formatters
      black
      nixfmt
      prettierd
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
