# Cards

Work for a bot to pick up, version-controlled so a card that produced a run can
be recovered later. Hand one to a bot in its Bot Chat, or put it on the board
with `hermes kanban create` if you want the durable queue and review lane.

- `vt-smb.md` — the real card. Build the scored Vermont prospect list from the
  corpus `../tools/fetch-vt-sources.py` assembles. Four sources, 13k rows, and a
  DONE WHEN clause that the tree must install from clean — which is what
  `hermes/hooks/require-green.sh` and `bin/installs-from-clean.sh` check.
- `gate-probe.md` — a card small enough to reach a handoff in minutes. Use it to
  test anything that only fires on `kanban_complete` or `kanban_request_review`;
  proving such a mechanism with the real card is a 50-minute coin flip.
