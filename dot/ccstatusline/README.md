# ccstatusline

[ccstatusline](https://github.com/sirmalloc/ccstatusline) renders the status line
(context used/window/%, weekly quota, git state). Wired up by `statusLine` in
`dot/claude/.claude/settings.json`; layout in `dot/ccstatusline/`, symlinked by the
same activation as `~/.claude` so it stays writable — run `ccstatusline` bare to open
its TUI, then commit or discard the diff.

Version pin and the `~/.npm-global` install live in `nixos/modules/programs/tui/claude.nix`
(`ccstatuslineVersion`); bump there. It needs `node` on `$PATH`: Homebrew's on the Macs,
`nodejs_22` in `nixos/modules/home/default.nix` on NixOS.

**Widget choices, and why:**

- `context-bar` alone, not `context-length` + `context-window` + `context-percentage`
  beside it. The bar already renders `342k/1.0M (34%)`, so the other three only repeat it.
- The plain `Context %` widget, never the "usable" variant — that one assumes an
  auto-compact cutoff, and we run `autoCompactEnabled: false`.
- `current-working-dir` (segments: 1) and `git-worktree`, so a glance identifies *which*
  session you're typing into. With many concurrent sessions the git widgets alone show
  `master` almost everywhere, and a worktree is indistinguishable from the main checkout.
- A `custom-command` widget on **a line of its own**, running
  `pi-workers.py --from-statusline --oneline`, so an `/orchestrate-pi` run is
  visible without asking Claude: `pi 5w 2▸ 1~ 1✓ $0.0912 ⚠1 stalled`.
  The dedicated line is not cosmetic — ccstatusline does **not** drop a
  separator adjacent to a widget that renders nothing, so putting it inline left
  either a dangling `|` when idle or no gap when active. On its own line the
  whole row disappears when the script prints nothing, which is every session
  that is not orchestrating. Verified by rendering both states, per the advice
  at the end of this file. The script must also never exit non-zero in this
  mode: ccstatusline renders `[Exit: N]` in the bar if it does.
- `weekly-usage` (the `weekly_all` quota) and `session-usage` (the 5-hour block).
  **Not** `weekly-opus-usage` / `weekly-sonnet-usage`: ccstatusline reads
  `https://api.anthropic.com/api/oauth/usage`, which now returns `seven_day_opus: null`
  and `seven_day_sonnet: null` — there is one combined weekly limit, no per-model split.
  ccstatusline maps a null bucket to `0` rather than "absent", so those two widgets sit
  at a permanent `0.0%` instead of hiding. Curl that endpoint with the OAuth token from
  the `Claude Code-credentials` keychain item to see what your plan actually reports.

Deliberately **not** enabled: powerline mode needs a Nerd Font present on every host
(NixOS, darwin, Termux), which is a poor trade for a repo whose point is uniform deploys.
To audit the other ~80 widgets, render them against a real session rather than guessing —
pipe a Claude Code status payload into `ccstatusline` with `HOME` pointed at a throwaway
config dir, so your live line is untouched.
