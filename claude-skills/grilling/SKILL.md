---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
metadata:
  upstream: https://github.com/mattpocock/skills/tree/3cca18b368ae95cdbdebbff572ccafa662551015/skills/productivity/grilling
  vendored: 3cca18b368ae95cdbdebbff572ccafa662551015
---

<!-- Vendored from https://github.com/mattpocock/skills (MIT), license copy in claude-skills/wayfinder/. Local edits: Tool mapping section -->

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.

## Tool mapping

The process above names two moves generically. Use whichever concrete tool your current harness gives you:

| Generic move | Claude Code | pi |
| --- | --- | --- |
| Ask a round | One `AskUserQuestion` call per round, up to 4 questions, the recommended option listed first. A frontier wider than 4 spans consecutive calls. | Numbered questions in the reply, the recommended answer under each, then wait for the typed answers. |
| Dispatch a sub-agent for a fact | The `Agent` tool. | The `subagent_*` tools, present only in a session started with `pi-subagents`. Otherwise look the fact up yourself, inline. |
