# Per-Project Dev Environment Examples

Runnable, copy-me examples of this repo's per-project development workflow:
**`direnv` + `nix-direnv` + a Nix flake `devShell`**. No Docker — the flake *is*
the environment. `cd` into a project and its tools load automatically; leave and
they unload.

This is the runnable companion to the
[Per-Project Development Environments](../README.md#per-project-development-environments)
section of `nixos/README.md`.

## Examples

| Directory | Provides |
|-----------|----------|
| [`python-devshell/`](python-devshell/) | Python 3 + `requests` + `ruff` |
| [`typescript-devshell/`](typescript-devshell/) | Node.js 22 + `typescript` (`tsc`) |

Each example is just three files: `flake.nix` (the environment), `.envrc`
(`use flake` — the direnv hook that auto-loads it), and a tiny `hello` program
that proves the toolchain is on `PATH`.

## How it works

1. `flake.nix` declares a `devShells.default` listing the exact tools/packages.
   It uses [`flake-utils`](https://github.com/numtide/flake-utils)'
   `eachDefaultSystem`, so the same flake works on every architecture
   (x86_64-linux, aarch64-linux, aarch64-darwin, …) with no edits.
2. `.envrc` contains a single line, `use flake`. When you enter the directory,
   direnv evaluates the flake and exports the dev shell into your shell —
   including editors/LSPs launched from it.
3. `nix-direnv` **caches** the built shell (and pins it as a GC root), so
   re-entry is near-instant and garbage collection won't blow the toolchain away.

Because the direnv + nix-direnv module (`modules/programs/tui/direnv/`) is already
enabled on every Nix-managed host, direnv and the caching are there out of the box.

## Try it

### Python

```bash
cd python-devshell
direnv allow      # one-time: trust this .envrc. From now on the env auto-loads on cd.
python hello.py   # runs the flake's Python, with requests available

# Without direnv:
nix develop       # drops you into the same shell manually
python hello.py
```

### TypeScript

```bash
cd typescript-devshell
direnv allow
tsc hello.ts && node hello.js   # both tsc and node come from the flake

# Without direnv:
nix develop
tsc hello.ts && node hello.js
```

Leaving the directory (`cd ..`) unloads the environment automatically.

## A note on `flake.lock`

These examples ship **without** a committed `flake.lock`. The first
`direnv allow` / `nix develop` generates one, pinning `nixpkgs` to an exact
revision. For a real project you'd **commit `flake.lock`** so every contributor
gets a byte-for-byte identical toolchain — that lock file is what makes the
environment truly reproducible.
