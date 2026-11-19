# Ending a chat: the handoff

Read this when Greg says he is ending the chat or asks for a handoff. The global `CLAUDE.md` keeps the Throughput rule for closing reports.

First reflect: what did we learn this session that a future session should know? Cover technical lessons, domain lessons (game dev, the project's rules), how you and Greg work together, and how subagents and lanes behaved.

Then answer two questions with this session's numbers, not guesses:

- **How could the next chat go faster?** Where did work wait: gates, lanes stuck or parked, his answers, setup steps redone by hand, a tool that failed silently.
- **How could it use fewer tokens?** Cover both meters: DeepSeek dollars (`gridkeep/.claude/pi-usage.py`, lane `Real:` lines, `pi-ask` costs) and Claude subscription use (orchestrator turns, especially wake-ups for routine events; subagent runs and their models; duplicated reviews). Name the biggest spender on each meter and one change that would cut it.

Write each lesson where it will be read next time, then write the handoff and list what you changed:

- Project rules every worker needs: the repo's `CLAUDE.md`.
- Project process for orchestrators: the repo's docs (such as `docs/orchestrating.md`).
- Orchestration that applies to any repo: the skill that runs it (such as `~/Git/toolbox/skills/swarm/SKILL.md`).
- How we work together, in every repo: the global `CLAUDE.md`, under "Working with me".

Skip lessons already written down; edit the existing line instead of adding a near-duplicate.

End every handoff with the exact message Greg pastes to start the next chat, in a code block: what to read (the handoff's full path) and what to do first. A bare path to the handoff is not enough.

When he wants to end fast, the plan goes into tickets, not a handoff doc: file the planned work, write lessons where they're read, and give him the paste-in message pointing at the tickets (2026-11-13).

## Investigation reports

An investigation reports as short reports, one screen each: findings with numbers, figures, a recommendations table, and a marimo notebook behind it. Each ends with a line he can paste to open a new Claude Code chat on that report (2026-11-06). Bugs and obvious fixes from it become tickets; anything needing a design call goes in a handoff for him.
