{
  config,
  lib,
  pkgs,
  vars,
  ...
}: let
  cfg = config.custom.programs.pi;

  # A packages entry is either a source string or pi's filtering object form.
  # `pi install` only ever takes the source, so unwrap it for the activation
  # script while settings.json keeps the full entry.
  packageSource = pkg:
    if builtins.isString pkg
    then pkg
    else pkg.source;

  # One oMLX model entry. Everything except id/name has a sane default because
  # every model we serve shares the same shape, and `cost` is not an option at
  # all — local inference is free, so it is always zero.
  modelType = lib.types.submodule {
    options = {
      id = lib.mkOption {
        type = lib.types.str;
        description = "Model id exactly as oMLX serves it.";
      };
      name = lib.mkOption {
        type = lib.types.str;
        description = "Human-readable label shown in pi's model picker.";
      };
      contextWindow = lib.mkOption {
        type = lib.types.int;
        default = 262144;
        description = "Context window in tokens.";
      };
      maxTokens = lib.mkOption {
        type = lib.types.int;
        default = 81920;
        description = "Maximum tokens the model may generate in one response.";
      };
      input = lib.mkOption {
        type = lib.types.listOf (lib.types.enum ["text" "image"]);
        default = ["text" "image"];
        description = "Input modalities the model accepts.";
      };
    };
  };
in {
  options.custom.programs.pi = {
    enable = lib.mkEnableOption "pi (pi-mono coding agent)";

    defaultModel = lib.mkOption {
      type = lib.types.str;
      default = "Qwen3.6-35B-A3B-8bit";
      description = "Default model to use";
    };

    # DeepSeek needs NO models.json entry: pi ships it as a built-in provider
    # (docs/providers.md -> DEEPSEEK_API_KEY / `deepseek`), and
    # `pi --list-models deepseek` lists deepseek-v4-pro and deepseek-v4-flash
    # the moment the env var is present. Declaring a `deepseek` provider by hand
    # — as api-docs.deepseek.com still instructs — SHADOWS that catalog and
    # leaves us owning contextWindow/maxTokens/cost forever. Don't.
    #
    # The key comes from nixos/secrets/.env (op inject -> .zshrc), so this
    # option only decides whether the models are offered in the picker. On
    # citadel the key is not injected at all, which is the real control.
    deepseek = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = ''
        Offer DeepSeek's models in pi's model picker and Ctrl+P cycle.
        Requires DEEPSEEK_API_KEY in the environment; the default local oMLX
        provider is unaffected either way.
      '';
    };

    # models.json normally comes from stow + `just secrets` (it holds the oMLX
    # api key, so it is templated from 1Password). Hosts that talk to *another*
    # machine's oMLX server have no secret to inject and can declare the file
    # here instead — set omlxBaseUrl and the module generates models.json.
    omlxBaseUrl = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "http://192.168.1.238:8000/v1";
      description = ''
        When non-null, generate ~/.pi/agent/models.json pointing pi's `omlx`
        provider at this base URL, listing `models`. When null (the default),
        models.json is left to stow + `just secrets`.
      '';
    };

    models = lib.mkOption {
      type = lib.types.listOf modelType;
      default = [];
      description = "Models to expose under the generated `omlx` provider. Only used when omlxBaseUrl is set.";
    };

    # Where the web-search extension sends queries. SearXNG runs as a container
    # on dungeon (home-lab), so every other host reaches it over the tailnet.
    # dungeon itself overrides this to localhost.
    searxngBaseUrl = lib.mkOption {
      type = lib.types.str;
      default = "http://${vars.networking.hosts.dungeon.tailscale}:8214";
      example = "http://localhost:8214";
      description = ''
        Base URL of the SearXNG instance pi's `web_search` tool queries. Written
        to ~/.pi/agent/searxng.json, which dot/pi/.pi/agent/extensions/web-search.ts
        reads. Deliberately not a literal in the extension: only nix knows each
        host's answer, and hardcoding one silently breaks the others.
      '';
    };

    # Packages installed via `pi install`. Pi resolves these at runtime.
    # Git-based packages are cloned to ~/.pi/agent/git/; npm packages go to
    # the global node_modules. Local extensions live in ~/.pi/agent/extensions/
    # managed by stow from dot/pi/.
    #
    # Entries are either a plain source string, or pi's object form for
    # filtering what a package loads (docs/packages.md -> "Package Filtering").
    # The object form matters here: on a local model every tool schema and every
    # line of injected system prompt is re-sent on EVERY request, so a package
    # that ships 22 extensions is not free just because we only wanted three.
    packages = lib.mkOption {
      type = lib.types.listOf (lib.types.either lib.types.str (lib.types.attrsOf lib.types.anything));
      default = [
        # Rust-powered frecency-ranked, fuzzy, git-aware file search
        # https://github.com/dmtrKovalenko/fff
        "npm:@ff-labs/pi-fff"

        # Context management, but it ships 22 extensions and we want two.
        # Excluded, and why:
        #   codex-*        OpenAI Codex quota/verbosity features. This host is
        #                  strictly local oMLX, so they are dead weight.
        #   mcp-wrapper    superseded by pi-mcp-adapter below; loading both
        #                  gives two MCP layers.
        #   run-subagent   2,691 tokens/request (four tool schemas plus the
        #                  system-prompt block it adds while they are active),
        #                  and it cannot be made lazy from outside: the suite's
        #                  runtime composition re-applies its baseline tool
        #                  list before every turn, so a setActiveTools() from
        #                  another extension holds for exactly one turn. Only
        #                  pi's own --exclude-tools beats it. Loaded on demand
        #                  by the `pi-subagents` alias in dot/zsh/.zshrc; see
        #                  dot/pi/CLAUDE.md -> "Lazy tools".
        # https://github.com/n-r-w/pi-agent-suite
        {
          source = "npm:pi-agent-suite";
          extensions = [
            "extensions/context-projection/index.ts" # hides stale tool output
            "extensions/custom-compaction/index.ts" # proactive compaction
          ];
        }

        # Directory containment and path/bash permission gates. Replaces moonpi,
        # whose guard skipped `bash` entirely (guards.ts: shouldCheckPath covers
        # read/write/edit/grep/find/ls only) and so caught typos, not damage.
        # https://github.com/gotgenes/pi-packages
        "npm:@gotgenes/pi-permission-system"

        # Read-only /plan mode. Replaces moonpi's plan/act modes and the local
        # plan-mode extension, which had been failing to load since pi renamed
        # its npm scope.
        # https://www.npmjs.com/package/@narumitw/pi-plan-mode
        "npm:@narumitw/pi-plan-mode"

        # Powerline-style footer: model, thinking level, context %, token counts.
        # The most-installed pi status line by a wide margin (23.3k/mo, 394
        # stars) versus @narumitw/pi-statusline at 12.5k/mo.
        #
        # Free under the token budget in dot/pi/CLAUDE.md: it registers no tools
        # and injects no system prompt, so it costs 0 tok/request. It is a UI
        # extension only. Configured under `powerline` in settings.json below.
        #
        # Pinned, like ccstatusline in claude.nix. This one replaces pi's editor
        # component — not just the footer — so a float-to-latest has a wider
        # blast radius than the other packages here. 0.15.1 also declares
        # peerDependencies of >=0.81.0 <0.85.0 on @earendil-works/pi-*, and
        # installed pi is 0.84.2: one minor bump from falling out of range, so
        # a pi upgrade may need this version moved with it.
        # Mirrored in hosts/macs/citadel/default.nix, which mkForces this list.
        # https://github.com/nicobailon/pi-powerline-footer
        "npm:pi-powerline-footer@0.15.1"

        # Reddit JSON research tools + a matching skill: compact evidence packs
        # for opinions, bugs, fixes, comparisons. Needs a session cookie —
        # see reddit-research.json below.
        # ~2,151 tok/request for 7 tools. Kept global deliberately: that is an
        # eighth of what moonpi cost, and scoping it to a project fails silently
        # under `pi -p`, which never prompts for project trust. See dot/pi/CLAUDE.md.
        # https://github.com/SaintNerona/pi-reddit-research
        "npm:pi-reddit-research"
      ];
      description = "Pi packages to declare in settings.json";
    };
  };

  config = lib.mkIf cfg.enable {
    # Remote-oMLX hosts declare models.json here; everyone else gets it from
    # stow + op inject (dot/pi/.pi/agent/models.json.tpl, via `just secrets`).
    home.file.".pi/agent/models.json" = lib.mkIf (cfg.omlxBaseUrl != null) {
      text = builtins.toJSON {
        providers.omlx = {
          baseUrl = cfg.omlxBaseUrl;
          api = "openai-completions";
          apiKey = "no-key-needed"; # oMLX does not authenticate
          compat = {
            supportsDeveloperRole = false;
            supportsReasoningEffort = false;
          };
          models = map (m:
            m
            // {
              cost = {
                input = 0;
                output = 0;
                cacheRead = 0;
                cacheWrite = 0;
              };
            })
          cfg.models;
        };
      };
    };

    # pi-reddit-research needs a Reddit session cookie — Reddit has required
    # auth on its .json endpoints since mid-2026. The cookie is NOT declared
    # here: it expires every few days, and `cookieFile` is re-read before every
    # request, so refreshing it means editing one file — no rebuild, no
    # `just secrets`, no restart. This file holds only the pointer, so a
    # read-only /nix/store symlink is the right shape for it.
    home.file.".pi/agent/reddit-research.json" = {
      text = builtins.toJSON {
        cookieFile = "${config.home.homeDirectory}/.config/pi-reddit-research/cookie.txt";
      };
    };

    # Endpoint for the local web-search extension. No secret in it, so a
    # read-only /nix/store symlink is the right shape — same as reddit-research.json.
    home.file.".pi/agent/searxng.json" = {
      text = builtins.toJSON {inherit (cfg) searxngBaseUrl;};
    };

    home.file.".pi/agent/settings.json" = {
      text = builtins.toJSON {
        defaultProvider = "omlx";
        inherit (cfg) defaultModel;
        lastChangelogVersion = "0.67.6";
        inherit (cfg) packages;

        # Which models Ctrl+P cycles through. Provider globs, same format as
        # the --models flag. `defaultProvider`/`defaultModel` above still decide
        # what a bare `pi` starts on — this only widens what you can switch TO
        # without restarting, so the local model stays the default everywhere.
        enabledModels = ["omlx/*"] ++ lib.optionals cfg.deepseek ["deepseek/*"];

        # Point pi at Claude Code's skill directory instead of maintaining a
        # second copy. Both agents implement the same Agent Skills standard
        # (docs/skills.md: "Using Skills from Other Harnesses"), so one
        # SKILL.md in claude-skills/ works unmodified in both — see
        # claude-skills/teach/SKILL.md for the first one written this way.
        skills = ["${config.home.homeDirectory}/.claude/skills"];

        # pi-powerline-footer. This file is a read-only /nix/store symlink, so
        # its `/powerline` and `/vibe` slash commands cannot persist a change —
        # they write back here and fail. Everything it should do is declared.
        #
        # Belt-and-braces, not load-bearing. Vibes are already inert when the
        # key is absent: working-vibes.ts derives `theme` from this setting and
        # every entry point returns early on a null theme, so `workingVibeMode`
        # defaulting to "generate" against `openai-codex/gpt-5.4-mini` never
        # fires on its own. Pinning "off" is what stops a stray `/vibe pirate`
        # in one session from leaving every later session calling a model oMLX
        # does not serve.
        workingVibe = "off";

        powerline = {
          # Glyphs are chosen per terminal, NOT per installed font: icons.ts
          # hasNerdFonts() reads POWERLINE_NERD_FONTS, then GHOSTTY_RESOURCES_DIR,
          # then a TERM_PROGRAM allowlist. So Ghostty gets glyphs (its env var
          # survives into tmux), while rohan's kmscon TTY and any ssh into
          # dungeon get the ASCII fallback — the font being installed there is
          # irrelevant. That degradation is per-host and automatic, which is why
          # nothing here forces it either way.
          preset = "default";
          welcome = false; # no startup splash over the session

          # Deliberately narrower than the ccstatusline layout, which does carry
          # git: context pressure and token counts only. Branch state is in the
          # shell prompt already, and local inference makes `cost` a permanent
          # $0.00.
          #
          # `context_pct` already renders "10k/262k (4.0%)" — used, total and
          # percentage in one segment — so `context_total` alongside it would
          # only repeat the 262k.
          #
          # `shell_mode` and `queue` earn their place despite the trim: both
          # self-hide when empty, and each is the only indicator for a mode this
          # extension can silently put you in — ctrl+shift+b bash mode, and a
          # prompt held back during compaction (which pi-agent-suite's
          # custom-compaction makes a routine event here).
          #
          # All three groups are listed explicitly: a present array replaces
          # that preset group exactly, an omitted one keeps the preset's.
          # `secondary` keeps `extension_statuses`, the generic sink any
          # extension's ctx.ui.setStatus writes to — clearing it would blank
          # future extensions' output too, not just this one's.
          layout = {
            left = ["model" "thinking" "shell_mode" "queue"];
            right = ["context_pct" "token_in" "token_out"];
            secondary = ["extension_statuses"];
          };
        };
      };
    };

    # Install pi packages (npm/git) on activation. Pi declares packages in
    # settings.json but the actual npm globals and git clones need `pi install`.
    # This runs after writeBoundary so settings.json is already in place.
    # Each install is idempotent — pi skips already-installed packages.
    home.activation.installPiPackages = lib.hm.dag.entryAfter ["writeBoundary"] ''
      # Home-manager activation runs with a minimal PATH. pi lives in Homebrew
      # on Darwin and the user profile on NixOS, so neither is reachable by
      # default and the `command -v pi` guard below silently skipped the whole
      # block — the same stripped-PATH trap nixos/CLAUDE.md documents for stow.
      # Symptom: activation prints "Activating installPiPackages", never prints
      # the success line, and new packages are simply never installed.
      export PATH="/opt/homebrew/bin:/run/current-system/sw/bin:$HOME/.nix-profile/bin:$PATH"

      if command -v pi &>/dev/null; then
        ${builtins.concatStringsSep "\n        " (map (pkg: ''pi install "${packageSource pkg}" 2>/dev/null || true'') cfg.packages)}
        echo "✓ Pi packages installed"
      fi
    '';

    # web-fetch and bash-guard are vendored local extensions (not `pi install`
    # packages — nothing in cfg.packages names them) with their own
    # package.json. The folded stow symlink at ~/.pi/agent/extensions already
    # makes their source visible; only node_modules is missing on a fresh
    # checkout, since it's gitignored (see dot/pi/CLAUDE.md). Guarded on the
    # directory existing so this no-ops harmlessly if it runs before
    # stowDotfiles on a fresh host — the next activation picks it up once stow
    # has.
    home.activation.installPiExtensionDeps = lib.hm.dag.entryAfter ["writeBoundary"] ''
      export PATH="/opt/homebrew/bin:/run/current-system/sw/bin:$HOME/.nix-profile/bin:$PATH"

      if command -v npm &>/dev/null; then
        for ext in web-fetch bash-guard; do
          ext_dir="${config.home.homeDirectory}/.pi/agent/extensions/$ext"
          if [ -d "$ext_dir" ] && [ ! -d "$ext_dir/node_modules" ]; then
            # Deliberately not silencing stderr here (unlike installPiPackages
            # above): a first-time install failing is the interesting case,
            # and swallowing it left no way to tell why.
            (cd "$ext_dir" && npm install --no-audit --no-fund) || echo "WARNING: npm install failed for pi extension $ext"
          fi
        done
        echo "✓ Pi extension deps installed"
      fi
    '';
  };
}
