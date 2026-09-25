{
  config,
  lib,
  ...
}: let
  cfg = config.custom.programs.hermes;
  toolboxDir = "${config.home.homeDirectory}/Git/toolbox";
  hermesDir = "${config.home.homeDirectory}/.hermes";
  profilesDir = "${hermesDir}/profiles";

  # Each of these is a Bot. The docs are explicit that "a Bot is a profile --
  # isolated config, memory, skills, credentials and chat history under
  # ~/.hermes/profiles/<name>/", so the roster in the Desktop app and the
  # directories in this repo are the same objects seen from two ends.
  # Bot -> our skills. Ours, not Hermes'. The bundled library lives in the same
  # tree, so these are linked individually — see the activation script.
  botSkills = {
    builder = ["verify-agent-output"];
    researcher = ["verify-agent-output"];
    orchestrator = ["verify-agent-output"];
    reviewer = ["verify-agent-output"];
    librarian = ["llm-wiki-review"];
  };
  bots = lib.attrNames botSkills;
in {
  options.custom.programs.hermes.enable =
    lib.mkEnableOption "Hermes bot profiles symlinked from the toolbox repo";

  config = lib.mkIf cfg.enable {
    # Writable symlinks into the repo, not read-only /nix/store paths, and the
    # reason is in Hermes' own configuration docs: config.yaml "is not safe to
    # make read-only for production deployments", and SOUL.md, skills/ and
    # memories/ are agent-modified at runtime. A store path would break the
    # first time a bot edited its own soul or `hermes config set` ran.
    #
    # This is the same trade claude.nix makes for ~/.claude/settings.json:
    # runtime writes land as git diffs in the toolbox repo, to commit or
    # discard. It also means a bot can write into a git repo, which is worth
    # knowing before pointing an unsupervised one at it.
    #
    # Only the declarative half is linked. memories/, sessions/, state.db,
    # cron/ and logs/ are runtime state and stay where Hermes puts them.
    home.activation.hermesProfiles = lib.hm.dag.entryAfter ["writeBoundary"] ''
      mkdir -p "${profilesDir}"

      # link_repo SRC DST -- refresh a symlink, create a missing one, and refuse
      # to clobber a real file so a hand-made profile is never silently lost.
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

      link_repo "${toolboxDir}/hermes/config.yaml" "${hermesDir}/config.yaml"
      link_repo "${toolboxDir}/hermes/hooks"       "${hermesDir}/hooks"

      # Our own skills go in each BOT's own skills/ directory, not the global
      # one. `hermes skills list` on the CLI reads ~/.hermes/skills/ and will
      # happily report a skill as "enabled" that no bot can see: a profile's
      # own `skills_list` tool reads profiles/<bot>/skills/ and answered "No
      # skills found in skills/ directory" while the CLI listed it fine. The
      # orchestrator then tried to run the skill as a shell command and got
      # `verify-agent-output: command not found`.

      ${lib.concatMapStringsSep "\n      " (bot: ''
            mkdir -p "${profilesDir}/${bot}"
            link_repo "${toolboxDir}/hermes/profiles/${bot}/SOUL.md"     "${profilesDir}/${bot}/SOUL.md"
          link_repo "${toolboxDir}/hermes/profiles/${bot}/config.yaml" "${profilesDir}/${bot}/config.yaml"
          mkdir -p "${profilesDir}/${bot}/skills"
          ${lib.concatMapStringsSep "\n          " (skill: ''
              link_repo "${toolboxDir}/hermes/skills/${skill}" "${profilesDir}/${bot}/skills/${skill}"
            '')
            botSkills.${bot}}
        '')
        bots}

      # llm-wiki-review wraps the bundled llm-wiki and loads it by name, and a
      # bot sees only its own skills/. Linked from Hermes' copy, so updates land.
      link_repo "${hermesDir}/skills/research/llm-wiki" "${profilesDir}/librarian/skills/llm-wiki"

      echo "✓ Hermes bots linked: ${lib.concatStringsSep ", " bots}"
    '';
  };
}
