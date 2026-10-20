---
description: Draft a commit message for the staged changes
argument-hint: "[hint]"
---
Draft a commit message for the staged changes. Hint from me: $@

1. Run `git status`, `git diff --cached` and `git log --oneline -5`.
2. If nothing is staged, say so and stop.
3. If the staged diff mixes unrelated changes (a fix with a feature, a refactor with a behavior change), name which files belong in separate commits and stop without a message.
4. Otherwise write `type(scope): subject`: type is feat, fix, refactor, style, test, docs or chore; the subject is imperative, lowercase, no period, 50 characters or fewer. Add a short body only when the why is not obvious.
5. Show the message in a code block and ask if it looks right.

Never run `git commit` yourself. Never mention AI, and never add Co-Authored-By, "Generated with" or session-link lines.
