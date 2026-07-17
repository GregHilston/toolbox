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
      beam27Packages.erlang # was erlang_27 (deprecated → beamPackages sets)
      beamPackages.elixir # was elixir (deprecated → beamPackages sets)
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
    # Filter out lazy-lock.json — it must be writable for lazy.nvim to update
    # plugin versions, but Nix store symlinks are read-only.
    source =
      builtins.filterSource
      (path: _: baseNameOf path != "lazy-lock.json")
      ./nvim;
    recursive = true;
  };
}
