# Global instructions for pi

## Agent skills

### Issue tracker

Wayfinder, to-spec and to-tickets need to know where this repo tracks issues.
Run `git config wayfinder.tracker`. `github` means GitHub Issues: follow
`~/.claude/skills/setup-matt-pocock-skills/issue-tracker-github.md`. `local` means
markdown files under `.scratch/`: follow
`~/.claude/skills/setup-matt-pocock-skills/issue-tracker-local.md`. If it is unset,
ask the user in your reply which of the two this repo should use, then store the
answer with `git config wayfinder.tracker <answer>` before doing anything else. A
repo's own CLAUDE.md or AGENTS.md issue-tracker block overrides this. If a label a
skill applies does not exist yet, `gh label create` it first.

The choice lives in local git config on purpose: never committed, so a work repo's
history stays clean, and shared by every worktree of the clone.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root. Follow
`~/.claude/skills/setup-matt-pocock-skills/domain.md`.
