# Skills: one set for Claude Code, pi and Hermes

Every skill here reaches all three harnesses. Write a new one here, not in a
harness's own directory, unless only one harness could ever use it.

## The shape

- **A skill is `skills/<name>/SKILL.md`, one level deep.** Claude Code loads only
  `~/.claude/skills/<name>/SKILL.md`, and pi and Hermes read the same file.
  The format is the [Agent Skills](https://agentskills.io/specification) open
  standard.
- **Frontmatter:** `name` must equal the directory name: lowercase, digits and
  hyphens. `description` is at most 1024 characters, and it is the only part
  loaded on every request. Say what the skill does and when to use it. Optional
  fields: `license`, `compatibility`, `metadata` (string values; Hermes-only
  skills may nest), `allowed-tools`,
  and the Claude Code extensions `disable-model-invocation`, `argument-hint`,
  `model` and `disallowed-tools`, which pi ignores. Nothing else.
- **No bare colon in a frontmatter value.** `description: Look it up: a summary`
  is invalid YAML. Hermes then drops the skill without a word, and the bot
  improvises with `curl`.
- **`disable-model-invocation: true`** for a skill you only invoke by name (the
  review and planning skills), so its description leaves the prompt; `/<name>`
  still works.

## A tool is a script plus a skill

**The script in `bin/` is the functionality; the skill only tells an agent how
to call it.** Don't put tool logic in a skill, a SOUL, a Hermes plugin or
`home-lab/hermes/scripts/`.

- **Not locked in.** The scripts run from any shell. Leaving a harness loses only
  the thin skill files.
- **An agent must be told.** A script on `PATH` is not enough: asked about
  Reddit, a Hermes bot tried DuckDuckGo and gave up after 4.5 minutes.
- **Cheap.** Only the description is in every prompt; the body loads on use.

A tool skill:

- **names its commands in a code block**, each typed exactly as run;
- **says to run them in your shell** (the `terminal` tool in Hermes, Bash in
  Claude Code, `bash` in pi), with no `python3` in front and no directory, since
  a local model otherwise prefixes a path. Keep the word `terminal`;
- **says what not to use instead**, such as web search or `curl`;
- **stays small**, so granting it grants only it.

The script follows `bin/CLAUDE.md`: the standard library where possible, plain
text out, and errors that say what broke.

## Who gets which skill

| Harness | Gets | Where it is set |
|---|---|---|
| Claude Code | every skill here | `~/.claude/skills` → `skills/` (`nixos/modules/programs/tui/claude.nix`) |
| pi | every skill here except claude.ai's `synced/` | `skills` setting in `nixos/modules/programs/tui/pi.nix`: the exclusion must be an absolute path, because pi's globs skip `.claude` |
| Hermes on moria | per profile, by grant | `botSkills` and `defaultSkills` in `nixos/modules/programs/tui/hermes.nix` |
| Hermes on dungeon | per mount | the `hermes` service in home-lab's `docker-compose.yaml` |

**Hermes is opt-in, per profile.** A grant is written `lab-tools/<name>` and links
`skills/<name>` under a `lab-tools/` category. Hermes lists an uncategorised
skill as `reddit:` then `- reddit`, and Gemma called that `reddit:reddit`.
Removing a grant revokes it: activation prunes our links that are no longer
listed. A grant is advice, not a fence: every bot can still run anything on
`PATH`.

`hermes/skills/` holds the skills that only make sense in Hermes. Claude Code
has no exclude list, so a Hermes-only skill would otherwise reach it.

`tests/test_skills.py` checks each skill against these rules, checks that every
command it names is in `bin/`, and checks that every Hermes grant names a skill.
