---
name: llm-wiki-review
description: Add a manual human review gate to Hermes' built-in llm-wiki workflow before compiled Wiki pages are created or changed. Use when the user explicitly invokes /llm-wiki-review for review-first LLM Wiki ingest or update work.
---

# LLM Wiki Review

Act as a lightweight human-in-the-loop wrapper around Hermes' built-in `llm-wiki` skill. Preserve the built-in workflow and intercept only the final decision to create or change compiled Wiki pages.

## Authority Boundary

- Explicitly load `llm-wiki` with `skill_view(name='llm-wiki')`.
- Let it orient to the Wiki, capture Raw material, search existing pages, synthesize changes, preserve provenance, surface contradictions, and perform post-write maintenance.
- Own the review decision for the current invocation. Do not allow the built-in skill to write compiled pages before approval.
- Do not modify the installed `llm-wiki` skill.
- If a deterministic Agentic Librarian such as `scripts/librarian_tool.py` already owns review and apply operations, stop. Never run both review authorities on the same change.

## Workflow

### 1. Prepare the change

1. Resolve `WIKI_PATH` or ask for the Wiki root.
2. Confirm the source and Wiki root exist inside the intended workspace. If either is missing or ambiguous, stop without searching other workspaces.
3. Load `llm-wiki` and follow its normal orientation, capture, retrieval, and synthesis steps.
4. Allow immutable Raw capture, but stop before creating or changing a compiled entity, concept, comparison, query, index, or log entry.

When capturing Raw, hash the exact source body before adding frontmatter. Store one blank separator after the closing `---`, then the unchanged body. Immediately recompute the hash by removing the frontmatter and that one separator; correct the new metadata if it does not match.

### 2. Create one review proposal

Create `Review/` if needed. Write one Markdown proposal per target:

```text
Review/YYYY-MM-DD-<target-name>-proposal.md
```

Use this minimal structure:

```yaml
---
type: llm-wiki-review
status: needs-review
decision: pending
revision: 1
operation: create
target: concepts/example.md
sources:
  - raw/example-source.md
---
```

Include these sections:

```markdown
# Proposed Wiki change

## What will change
Explain the change in plain language.

## Proposed content
Include the exact content that would be written.

## Evidence and uncertainty
Identify supporting sources, uncertainty, and conflicting claims.

## Human feedback
Optionally explain or edit what should change.
```

Set `operation` to `create`, `update`, or `conflict-resolution`. Keep all paths relative to the Wiki root.

Before presenting the proposal, validate its proposed content against the active `SCHEMA.md`. Require at least `title`, `created`, `updated`, `type`, `tags`, and `sources`, as specified by the built-in skill. If no tag taxonomy exists, use `tags: []` rather than omitting the field. Do not ask the human to approve structurally invalid content.

For contradictions, show competing claims before details and propose preserving both as contested. Replace the generic `Human feedback` line with exactly these three primary choices, and repeat them in the response:

- **Keep both:** approve this proposal.
- **Not a contradiction:** revise it to preserve compatible or context-dependent claims without `contested`, then stop for approval again.
- **Decide later:** defer without changing compiled content.

Put source preference and custom resolutions under `Advanced: revise`. Require a reason or stronger evidence before preferring a source or removing its claim. Never silently select a winner.

### 3. Stop for a decision

Report the proposal path, target, operation, and main uncertainty. For ordinary proposals ask for `approve`, `reject`, `revise`, or `defer`. For contradictions use the labels above; accept `reject` or custom `revise` as advanced input.

Accept the decision in conversation or through the proposal's `decision` frontmatter. Then stop. Silence and elapsed time are not approval.

Use only these canonical `decision` values: `pending`, `approve`, `reject`, `revise`, and `defer`.

### 4. Resume safely

On the next explicit invocation, reread the proposal and its current revision before acting:

- Revalidate the reviewed content before any write. If it is structurally invalid, do not apply it; create a corrected proposal revision and request review again.
- **Approve:** Apply the exact valid reviewed content. Set `decision: approve` and `status: applied`. Then use the built-in workflow to update links, index, log, and lint.
- **Reject:** Leave the target unchanged. Set `decision: reject` and `status: rejected`.
- **Revise:** Incorporate the feedback into a new proposal, increment `revision`, reset `decision: pending`, and stop for review again.
- **Defer:** Leave the target unchanged. Set `decision: defer` and `status: deferred`.

Never apply an approval to a different revision from the one the human reviewed.

## Completion Checks

Before reporting completion, confirm that:

- Raw material remains source-traceable and unchanged.
- A new Raw capture immediately passes its own stored body-hash check.
- No compiled page changed before approval.
- The proposal records its target, sources, operation, revision, and decision.
- Proposed and applied content satisfy the active schema and required frontmatter.
- Approved content matches the reviewed proposal.
- Rejected or deferred proposals caused no compiled Wiki mutation.
- Built-in maintenance ran after an approved write.

This companion provides a review convention, not deterministic enforcement. Use the full Agentic Librarian when hashes, receipts, replay safety, automation, or mechanically enforced policies are required.
