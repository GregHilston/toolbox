# Toolbox

---

My toolbox contains a series of configuration files, helper scripts, and automations to allow me to quickly configure an OSX or Linux environment.

## What's In This Repo?

```bash
├── bin/                                    # Helper scripts. Should be added to $PATH for user convenience.
├── docs/                                   # Additional documentation that supplements this `README.md`
├── dot/                                    # Dotfiles to configure a slew of programs and environments.
├── nixos/                                  # NixOS and nix-darwin configurations for all hosts.
├── secret/                                 # Secrets, such as passwords. Purposefully ignored by Git, and populated on each individual machine.
├── Brewfile                                # Describes which programs to install with Brew.
├── README.md                               # This documentation.
```

## How Do I Use This Repo?

See the [nixos/](nixos/) directory for NixOS and nix-darwin host configurations. Each host is managed declaratively via Nix flakes.

## Local Diff & PR Viewers

Two browser-based diff viewers for reviewing changes locally, without pushing anything or opening a GitHub PR. Both are **Mac-only** — they need a Node.js runtime (`npx`), which the Macs have (citadel via volta; dungeon/moria via Homebrew) but the NixOS hosts do not (node lives only inside per-project dev shells there).

### View your working-tree changes — `diff2html`

Installed via nixpkgs (`diff2html-cli`). Opens the diff in your browser.

```bash
dhtml        # all changes vs HEAD (staged + unstaged), unified
dhtmls       # staged changes only
dhtmlside    # all changes vs HEAD, side-by-side
```

Or drive it directly: `git diff --no-ext-diff HEAD | diff2html -i stdin`
(`--no-ext-diff` is required because git is configured to use difftastic as its external diff).

### Review a branch as a PR — `difit` / `gpr`

`difit` renders a GitHub-PR-like UI in the browser. It is not in nixpkgs, so it runs via `npx` pinned to an exact version.

```bash
# Working-tree changes (alternative to diff2html)
difit                  # all uncommitted changes (staged + unstaged) — the default
difit staged           # staged only
difit working          # unstaged only

# This branch vs a base, PR-style
gpr                          # vs the repo's default branch (auto-detected, e.g. origin/main)
gpr origin/develop           # vs an explicit base
difit HEAD main --merge-base # equivalent, done by hand

# Don't open a browser / pick a port
gpr --no-open --port 5000
```

`gpr` auto-detects the base branch from `origin/HEAD` (falling back to `main`/`master`) and uses GitHub's 3-dot (`--merge-base`) semantics by default; set `GPR_MERGE_BASE=0` for a plain 2-dot diff.

**Pinning / bumping difit:** the pinned version lives in one place — `DIFIT_VERSION` at the top of `bin/difit.sh` (currently `5.0.6`). Bump it by editing that default, or override per-run with `DIFIT_VERSION=5.1.0 difit …`. Pinning avoids `npx`'s stale-cache footgun and keeps runs reproducible.

## Setting Terminal Font

### Windows 11

Since we do not do much developing on Windows, and may only use it to SSH into a remote Linux box, we will not be automating this much. Please follow these steps to get the fonts working on your Windows machine.

1. Navigate to [this URL](https://github.com/romkatv/powerlevel10k#manual-font-installation), and download `MesloLGS NF Regular.ttf`, `MesloLGS NF Bold.ttf`, `MesloLGS NF Italic.ttf`, and `MesloLGS NF Bold Italic.ttf`.
2. For each of the four `.ttf` files, double click them, which opens up a popup showing you sample text in your font. Click the `install` button in the right corner.

![Font Installation](./docs/res/font-installation.png)

3. Open our WSL application, which is usually called `Debian` or `Ubuntu.`

![Debian Application](./docs/res/debian-application.png)

![Ubuntu Application](./docs/res/ubuntu-application.png)

4. Right click on the top of the terminal, and navigate to `Settings`

![Application Settings](./docs/res/application-settings.png)

5. Then navigate to `Profiles > Debian/Ubuntu` <sup>5</sup>

![More Application Settings](./docs/res/application-settings2.png)

6. Then navigate to `Additional Settings/Appearance` <sup>6</sup>

![Additional Settings](./docs/res/additional-settings.png)

7. Select `MesloLGS NF` from the `Font face` dropdown. <sup>7</sup>

![Font Face](./docs/res/font-face.png)
