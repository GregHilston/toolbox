# Commit Message Helper

Help write a high-quality, atomic git commit message for the current changes.

## Step 1: Gather State

Run these in parallel:
- `git status`
- `git diff --cached` (staged changes)
- `git diff` (unstaged changes)
- `git log --oneline -5` (recent commits for style reference)

## Step 2: Atomic Commit Audit

Before writing any message, evaluate whether the **staged** changes represent a single, atomic unit of work.

**An atomic commit:**
- Makes exactly one logical change
- Can be reverted without affecting unrelated functionality
- Would pass tests (if they existed) on its own
- Can be described without using "and" to join unrelated concerns

**Red flags — the staged diff should NOT be committed as-is if it:**
- Mixes a bug fix with a new feature
- Mixes refactoring with behavior changes
- Mixes formatting/whitespace cleanup with logic changes
- Touches multiple unrelated subsystems without a single unifying reason
- Would require "and" to describe two genuinely separate concerns

**If the changes are not atomic:**
- Explain specifically why (point to the files/sections that belong in separate commits)
- Suggest how to split: which files/hunks belong together, and what order to commit them
- Do NOT write a commit message — stop here and ask the user to stage the right subset first

**If nothing is staged:**
- Note that there are no staged changes
- Show what's unstaged and ask the user which changes they want to commit

## Step 3: Write the Commit Message

Only proceed here if the staged changes are atomic.

### Format

```
type(scope): short description in imperative mood

Optional body — explain the WHY, not the HOW. Wrap at 72 characters.
Bullet points are fine for multiple related points.
```

### Type

Choose one:
- `feat` — new capability or behavior
- `fix` — corrects a bug
- `refactor` — restructures code without changing behavior
- `style` — formatting, whitespace, naming (no logic changes)
- `test` — adds or updates tests
- `docs` — documentation only
- `chore` — build, deps, tooling, config

### Scope

Optional. Use the subsystem, module, or filename affected (e.g., `auth`, `api`, `yt-transcript`). Omit if the change is repo-wide or the scope is obvious from the type alone.

### Subject Line Rules

- Imperative mood: "add X", not "added X" or "adds X"
- No trailing period
- 50 characters or fewer (hard limit: 72)
- Lowercase after the colon
- Describes *what* changes, not *how*

### Body Rules (include when useful)

- Explain *why* the change was made
- Explain *what problem* it solves
- Note non-obvious tradeoffs or context
- Skip it for self-evident changes

### Authorship

Never mention AI, Claude, or any AI tool in the commit message. Never add "Co-authored-by" lines for AI assistants. The commit should read as if the developer wrote it themselves.

### Good Examples

```
feat(yt-transcript): add --language flag for subtitle selection
```

```
fix(tmux): remove C-l binding to preserve terminal clear

C-l was shadowing the shell's clear-screen shortcut. Removing
it restores expected behavior without losing any tmux functionality.
```

```
refactor(auth): extract token validation into its own module

The validation logic was duplicated across three handlers. Centralizing
it removes the duplication and makes future changes to validation rules
a single-site edit.
```

### Bad Examples (avoid)

```
fix: fixed stuff          # past tense, vague
update auth.py            # no type, describes the file not the change
feat: add login and also fix the session timeout bug   # two concerns, not atomic
WIP                       # not a real commit message
```

## Step 4: Present and Confirm

Show the proposed commit message in a code block. Then ask:
> Does this look right, or would you like to adjust the wording?

Do NOT run `git commit` automatically. The user will commit when ready.
