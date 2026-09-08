---
name: research
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
metadata:
  upstream: https://github.com/mattpocock/skills/tree/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/research
  vendored: 3cca18b368ae95cdbdebbff572ccafa662551015
---

<!-- Vendored from https://github.com/mattpocock/skills (MIT), license copy in claude-skills/wayfinder/. Local edits: Tool mapping section -->

Spin up a **background agent** to do the research, so you keep working while it reads.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source.
3. Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.

## Tool mapping

| Generic move | Claude Code | pi |
| --- | --- | --- |
| Background agent | The `Agent` tool, run in the background. | The `subagent_*` tools, present only in a session started with `pi-subagents`. Otherwise do the research inline in this session and say so. |
