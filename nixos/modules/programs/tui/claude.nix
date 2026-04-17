{
  config,
  lib,
  ...
}: let
  toolboxDir = "${config.home.homeDirectory}/Git/toolbox";
in {
  # Declaratively symlink Claude Code user-level commands and skills
  # from the toolbox repo so any host that runs home-manager gets them.
  home.activation.claudeCodeSetup = lib.hm.dag.entryAfter ["writeBoundary"] ''
    mkdir -p "${config.home.homeDirectory}/.claude"

    if [ ! -e "${config.home.homeDirectory}/.claude/commands" ]; then
      ln -sf "${toolboxDir}/claude-commands" "${config.home.homeDirectory}/.claude/commands"
    fi

    if [ ! -e "${config.home.homeDirectory}/.claude/skills" ]; then
      ln -sf "${toolboxDir}/claude-skills" "${config.home.homeDirectory}/.claude/skills"
    fi
  '';
}
