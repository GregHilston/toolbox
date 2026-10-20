---
description: Write a handoff note so a new session can continue this work
argument-hint: "[extra context]"
---
Write a handoff for the next session. Extra context from me: $@

First reflect: what did we learn that a future session should know (technical, project rules, how I like to work)? Write each lesson into the file where it will be read next time (the repo's AGENTS.md or CLAUDE.md, or the relevant doc), editing an existing line instead of duplicating it.

Then save `.pi/handoffs/handoff-YYYY-MM-DD-HHMM.md` with these headings: Current Project, Work Completed This Session, Key Files, Decisions Made, Next Steps, Continuation Prompt. If an earlier handoff exists in that folder, name it as the previous link in the chain.

Finish by listing the files you changed and giving a short paste-ready prompt: "Resume from handoff: <path>. Next: <action>".
