# nixos/modules/programs/tui/zellij/default.nix
#
# Installed everywhere tmux is; tmux still owns the default multiplexer role
# (see ../tmux). Config is stow-managed from dot/zellij, not nix-declarative —
# KDL has no include directive, so it can't split into a portable base + nix
# overlay the way .tmux.conf does (see dot/README.md). Keybinds are
# tmux-prefix-compatible (Ctrl-b c/n/p/%/"), theme is gruvbox-dark; see
# dot/zellij/.config/zellij/config.kdl.
{
  lib,
  pkgs,
  ...
}: {
  programs.zellij.enable = true;

  # zjstatus (github.com/dj95/zjstatus) status bar plugin, referenced by the
  # stow-managed dot/zellij/.config/zellij/layouts/default.kdl. Symlinked to a
  # fixed path rather than embedding the /nix/store path in that portable KDL
  # file (which, unlike home.file, cannot be nix-templated — see the header
  # above). home.file's target is regenerated every activation, so this stays
  # GC-safe the same way ~/.zshrc.local's embedded store paths are.
  #
  # force = true on both: a home.file.<x>.source pointing at a bare-file
  # derivation (not a directory) gets linked straight to that /nix/store path,
  # bypassing home-manager's own "*-home-manager-files/*" aggregate. Its
  # collision check (check-link-targets.sh) only recognizes symlinks that
  # point into that aggregate as "already ours" — so every later activation
  # sees a foreign symlink here and aborts with "would be clobbered", and
  # backupFileExtension can't save it either (that path only backs up plain
  # files, not symlinks). force skips the check outright, which is safe since
  # nothing but this module ever writes these two paths.
  home.file.".local/share/zellij/plugins/zjstatus.wasm" = {
    source = pkgs.zellijPlugins.zjstatus;
    force = true;
  };

  # autolock (github.com/fresh2dev/zellij-autolock): headless plugin that
  # switches zellij to "Locked" mode while the focused pane runs nvim/git/
  # fzf/zoxide/atuin, so Ctrl-h/j/k/l reach those tools' own keymaps instead
  # of zellij's — see dot/zellij/.config/zellij/config.kdl's plugins/
  # load_plugins/keybinds blocks. Same GC-safe home.file pattern as zjstatus.
  home.file.".local/share/zellij/plugins/autolock.wasm" = {
    source = pkgs.zellijPlugins.autolock;
    force = true;
  };

  # Plugin permission grants. Zellij has every plugin request permissions as it
  # loads and caches the answer in a KDL file under its *cache* dir; until an
  # answer is cached the plugin loads and then draws nothing. That is the entire
  # failure mode for the status bar — the log reads
  # "Loaded plugin '.../zjstatus.wasm' in 7.1ms" and the bar is blank — and it
  # is silent, because a headless plugin like autolock keeps working regardless.
  #
  # Upstream's instruction is "focus the pane and press `y`", which is not usable
  # here. Verified on zellij 0.44.3: the pending-permission pane renders no text
  # at all (just an empty frame), and ours is a `size=1 borderless=true` row, so
  # there is nothing to read and almost nothing to aim at. The keypress does
  # register, which is how the sets below were obtained — granted by hand once,
  # then copied verbatim out of the file zellij wrote.
  #
  # Seeded additively, and only for a plugin with no entry yet, so a hand-made
  # grant survives and so does a deliberate *denial* (which zellij records as an
  # entry with an empty block). Keyed on the fixed ~/.local/share path above
  # rather than the /nix/store path, so a nixpkgs bump does not revoke it —
  # upstream's "this must be repeated on updates" only applies to the versioned
  # `https://` plugin URLs.
  home.activation.zellijPluginPermissions = lib.hm.dag.entryAfter ["writeBoundary"] (
    let
      permissions = {
        zjstatus = ["ChangeApplicationState" "ReadApplicationState" "RunCommands"];
        autolock = ["ChangeApplicationState" "ReadApplicationState"];
      };
      # Whatever the `directories` crate calls the cache dir, which is what zellij asks.
      cacheDir =
        if pkgs.stdenv.hostPlatform.isDarwin
        then "$HOME/Library/Caches/org.Zellij-Contributors.Zellij"
        else "\${XDG_CACHE_HOME:-$HOME/.cache}/zellij";
    in ''
      permFile="${cacheDir}/permissions.kdl"
      ${pkgs.coreutils}/bin/mkdir -p "${cacheDir}"
      [ -e "$permFile" ] || : > "$permFile"

      grantZellijPlugin() {
        local plugin="$1"
        shift
        local path="$HOME/.local/share/zellij/plugins/$plugin.wasm"
        # A case-glob, not grep: activation runs with a stripped PATH.
        case "$(< "$permFile")" in
          *"\"$path\""*) return 0 ;;
        esac
        {
          printf '"%s" {\n' "$path"
          printf '    %s\n' "$@"
          printf '}\n'
        } >>"$permFile"
        echo "zellij: seeded plugin permissions for $plugin"
      }

      ${lib.concatStringsSep "\n" (lib.mapAttrsToList
        (plugin: perms: "grantZellijPlugin ${plugin} ${lib.concatStringsSep " " perms}")
        permissions)}
    ''
  );

  home.activation.stowZellij = lib.hm.dag.entryAfter ["writeBoundary"] ''
    DOTFILES="$HOME/Git/toolbox/dot"
    if [ -d "$DOTFILES" ]; then
      cd "$DOTFILES"
      # --no-folding: ~/.config/zellij must stay a *real* directory so
      # zellij's own runtime writes (config.kdl.bak, Configuration-UI
      # rewrites) land there, not — via a folded directory symlink — inside
      # this repo's working tree. See dot/justfile's zellij caveat.
      ${pkgs.stow}/bin/stow -v --no-folding -t "$HOME" zellij 2>&1 \
        || echo "stow: conflict for zellij — backup conflicting dotfiles in ~ then re-run home-manager"
    fi
  '';
}
