{
  config,
  lib,
  pkgs,
  ...
}: let
  toolboxDir = "${config.home.homeDirectory}/Git/toolbox";
  claudeDir = "${config.home.homeDirectory}/.claude";
  claudeBin = "${config.home.homeDirectory}/.local/bin/claude";
in {
  # Declaratively symlink Claude Code user-level config from the toolbox repo so
  # any host that runs home-manager gets the same commands, skills, settings,
  # hooks, and global CLAUDE.md.
  #
  # We use writable symlinks into the repo (not read-only /nix/store links) on
  # purpose: Claude Code writes back to settings.json at runtime (theme, survey
  # state, /config toggles). Runtime edits therefore show up as git diffs in the
  # toolbox repo, which can be committed or discarded.
  home.activation.claudeCodeSetup = lib.hm.dag.entryAfter ["writeBoundary"] ''
    mkdir -p "${claudeDir}"

    # link_repo SRC DST
    #   - DST is already a symlink   -> refresh it (safe, idempotent)
    #   - DST does not exist         -> create the symlink
    #   - DST is a real file/dir     -> refuse to clobber; warn loudly and skip.
    #     Migrate the real file into SRC, delete the original, then re-run.
    link_repo() {
      if [ -L "$2" ]; then
        ln -sfn "$1" "$2"
      elif [ ! -e "$2" ]; then
        ln -s "$1" "$2"
      else
        echo "WARNING: $2 is a real file, not a symlink — leaving it untouched." >&2
        echo "  To bring it under nix management, migrate it into:" >&2
        echo "    $1" >&2
        echo "  then delete the original and re-run home-manager." >&2
      fi
    }

    link_repo "${toolboxDir}/claude-commands"             "${claudeDir}/commands"
    link_repo "${toolboxDir}/claude-skills"               "${claudeDir}/skills"
    link_repo "${toolboxDir}/dot/claude/.claude/CLAUDE.md"     "${claudeDir}/CLAUDE.md"
    link_repo "${toolboxDir}/dot/claude/.claude/settings.json" "${claudeDir}/settings.json"
    link_repo "${toolboxDir}/dot/claude/.claude/hooks"         "${claudeDir}/hooks"
  '';

  # Install the Claude Code CLI via Anthropic's official *native* installer —
  # NOT Homebrew. https://code.claude.com/docs/en/quickstart recommends the
  # native install (`curl -fsSL https://claude.ai/install.sh | bash`), which
  # drops a launcher at ~/.local/bin/claude (already on $PATH via dot/zsh/.zshrc)
  # pointing at ~/.local/share/claude/versions/<v>, and then self-updates in
  # place. So we only need to *bootstrap* it once per machine; thereafter Claude
  # keeps itself current and this step no-ops.
  #
  # Idempotent + non-fatal: skips when the launcher already exists, and never
  # fails activation if the network is down (just warns). The installer does not
  # edit shell rc files when ~/.local/bin is already on PATH (verified), so it
  # won't dirty the stow-managed ~/.zshrc.
  home.activation.claudeCodeInstall = lib.hm.dag.entryAfter ["writeBoundary"] ''
    if [ ! -x "${claudeBin}" ] && ! command -v claude >/dev/null 2>&1; then
      echo "Installing Claude Code via native installer (https://claude.ai/install.sh)…"
      ${pkgs.curl}/bin/curl -fsSL https://claude.ai/install.sh | ${pkgs.bash}/bin/bash \
        || echo "WARNING: Claude Code native install failed (offline?). Re-run later: curl -fsSL https://claude.ai/install.sh | bash" >&2
    fi
  '';
}
