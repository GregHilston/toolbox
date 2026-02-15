---
description: Create context handoff for session continuation
allowed-tools: Read, Write, Glob
---

# /handoff

Save state for continuation in new chat (use when context ~10-15% remaining).

## Handoff Chain

It's possible for long tasks that we have multiple hands offs to complete al the work. To ensure we always have a full chain of context, be sure to mention in the handoff if this is the first in a chain, if not, mention the previous handsoffs in the chain.

## Execute

1. Summarize current project/phase
2. Note key files and decisions
3. Save to .claude/handoffs/handoff-[date]-[time].md
4. Provide continuation prompt

## Handoff Format

```
# Context Handoff - [Date]

## Current Project / Plan
## Current Phase
## Work Completed This Session
## Key Files
## Decisions Made
## Next Steps
## Continuation Prompt
```

## Output

```
Handoff saved to: .claude/handoffs/handoff-YYYY-MM-DD-HHMM.md

To continue, paste:
---
Resume from handoff: [path]
Context: [brief]
Next: [action]
---
```
