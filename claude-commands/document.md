---
description: Write documentation my way — trace code, diagram-backed, simple, file:line-pinned
argument-hint: <what to document — a flow, entrypoint, subsystem, or concept>
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
---

# /document

Write or update documentation following my standards. Works for code flows, backend entrypoints, subsystems, processes, or concepts.

The canonical example of the structure and quality to aim for is `docs/architecture/flows/breach-pipeline.md`. When documenting a code flow, read it first, every time, before writing.

## Input

`$ARGUMENTS` is what to document (a name, a route, a path, or a short description). If anything is ambiguous — which handler is meant, or where the doc should live — find the candidates and confirm with me before writing.

## Method

1. Trace it in code. Read the actual code through to its side effects (DB, cache, queue, email, external APIs). Every `file:line` you cite must come from reading that line — never guess. Use the Explore agent for the initial search when scope is uncertain.
2. Choose the location. A code flow, entrypoint, or subsystem goes in `docs/architecture/flows/<slug>.md`. Anything else goes where similar docs already live; if there is no obvious home, ask.
3. Write the doc, then pause for my review before updating any index.
4. If what you documented is a backend entrypoint, also add or update its row in `docs/architecture/entrypoints.md` (see Index update below).

## Structure for a code-flow doc (mirror breach-pipeline.md)

- `# Flow: <Name>` (or a fitting `# <Title>` for non-flow docs).
- One or two sentence intro: what triggers it and what it accomplishes. Link a relevant ADR under `docs/adr/` if one explains a design choice.
- If it spans more than one process or component: a short bullet list naming each role, then a `## Topology` `flowchart` showing the boxes and how they are wired (datastores as `[(...)]`, queues as `([...])`, processes grouped in `subgraph`s, edges labeled with the protocol or call). Skip the topology for a single-component flow.
- One `## <Stage>` heading per stage. Begin each with `Entrypoint: [file:line](...)`.
- A `sequenceDiagram` only when a stage has multiple participants and non-obvious ordering or branching. A thin or linear handler gets a `| Step | Code |` table instead, not a diagram.
- Carry every `file:line` anchor in a `| Step | Code |` table (or inline prose), never in a separate "code map" index.
- Add a focused subsystem section (caching, delivery semantics, idempotency, auth) only when it holds a non-obvious truth. Use a `> Important:` blockquote for boundaries and gotchas.

## Writing standards (apply to every doc)

- Simplicity first: as simple as possible, no simpler. One idea, one place. Never describe the same thing twice — for example a diagram and a step-by-step list of the same flow. The diagram is the flow; tables and prose add only what a diagram cannot (file:line, config names, the "why").
- Diagram and table for the same stage: split the labor. The diagram owns ordering and branching; each table row is an operation name plus its anchor, not a retelling of the diagram's branches. Keep a row explanatory only when it carries something the diagram does not show — process startup, a config value, or a cross-reference to another section.
- Keep diagrams coarse: components and ordering, not every helper call, so routine refactors do not falsify them.
- Disambiguate overloaded nouns and gloss jargon on first use — say which thing a term refers to (the message vs. the email) and what an acronym implies (what "at-least-once" means for duplicates) before relying on it.
- Headings in Title Case, but keep code identifiers verbatim (e.g. `## Consumer: emailBreachAlerts Container`).
- Sparse bold, rare italics, plain declarative sentences. No decorative `---` separators between sections — headers do the separating.

## Link conventions

- From a flow doc (`docs/architecture/flows/<slug>.md`): code links are `../../../src/...#L<n>`; sibling flow docs are `./<slug>.md`; ADRs are `../../adr/<file>.md`.
- From `docs/architecture/entrypoints.md`: code links are `../../src/...#L<n>`; flow docs are `./flows/<slug>.md`.
- Wrap any URL containing Next.js route-group parens (e.g. `(redesign)`, `(authenticated)`) in angle brackets — `[text](<../../../src/app/[locale]/(redesign)/.../file.ts#L40>)` — or GitHub's Markdown parser breaks the link.

## Index update (backend entrypoints only)

Add or update exactly one row in the table for the correct trigger-source group in `entrypoints.md`, using the next free ID in that group:

`| **<ID> · <Name>** | <what or who triggers it> | [<file>:<line>](<link>) | [<slug>](./flows/<slug>.md) |`

Keep the groups in their existing order. If the entrypoint shares a flow doc with another row (for example a producer/consumer pair), point both rows at the same flow doc.

## Verify before finishing

- Re-read each cited line to confirm the anchor is correct.
- Remind me to preview the rendered Markdown and Mermaid on GitHub (the diagrams, and any angle-bracketed links).
