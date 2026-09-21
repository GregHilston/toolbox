# Cards

`agent-iterate.sh` reads `~/Git/agent-runs/card.md`, which is outside any repo.
These are the version-controlled copies, so a card that produced a run can be
recovered later.

- `vt-smb.md` — the real card. Build the scored prospect list from the seeded
  corpus. Copy to `~/Git/agent-runs/card.md`.
- `gate-probe.md` — a card small enough to reach a handoff in minutes. Use it to
  test anything that only fires on `kanban_complete` or `kanban_request_review`;
  proving such a mechanism with the real card is a 50-minute coin flip.
  `AGENT_CARD=.../gate-probe.md ./bin/agent-iterate.sh probe 15 "..."`
