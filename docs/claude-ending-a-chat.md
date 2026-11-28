# Ending a chat

Read this when Greg says he is ending the chat, or you report an investigation. The global `CLAUDE.md` points here.

First reflect: what did we learn this session that a future session should know? Cover technical lessons, domain lessons (game dev, the project's rules), how you and Greg work together, and how subagents behaved.

Then answer two questions with this session's numbers, not guesses:

- **How could the next chat go faster?** Where did work wait: gates, his answers, setup steps redone by hand, a tool that failed silently.
- **How could it use fewer tokens?** Cover both meters: DeepSeek dollars (`gridkeep/.claude/pi-usage.py`, `pi-ask` costs) and Claude subscription use (orchestrator turns, especially wake-ups for routine events; subagent runs and their models; duplicated reviews). Name the biggest spender on each meter and one change that would cut it.

Write each lesson where it will be read next time, then list what you changed. State goes on tickets or docs, never a handoff note:

- Project rules every worker needs: the repo's `CLAUDE.md`.
- Project process for orchestrators: the repo's docs (such as `docs/orchestrating.md`).
- How we work together, in every repo: the global `CLAUDE.md`, under "Working with me".

Skip lessons already written down; edit the existing line instead of adding a near-duplicate.

When he wants to end fast, file the planned work as tickets and write lessons where they're read (2026-11-13). Sessions are ephemeral: no handoff doc, no paste-in message.

## Investigation reports

An investigation reports as short reports, one screen each: findings with numbers, figures, a recommendations table, and a marimo notebook behind it. Bugs and obvious fixes from it become tickets; anything needing a design call goes on a ticket for him.
