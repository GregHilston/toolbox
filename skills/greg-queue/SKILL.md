---
name: greg-queue
description: Walk Greg through everything waiting on him across home-lab, toolbox, gridkeep, loser-picks and dradis. Each decision or discussion becomes a question with a recommended option, then a closing list of manual tasks. Use for /greg-queue, or when Greg asks what needs him, for his queue, or to go through his picks.
license: MIT
---

# Greg's queue

The queue is every open ticket labelled `needs-greg` in the five repos, as the
dradis core has already synced them. The dradis board's Needs-you view reads the
same list, so an answer given here shows there too.

Run these in your shell (Bash in Claude Code, `bash` in pi, the `terminal` tool
in Hermes) exactly as shown, with no `python3` and no directory in front:

```
factory needs --json
factory answer <repo> <n> --pick <KEY> [--note '<why>'] [--ready]
factory answer <repo> <n> --text '<answer>' [--ready]
factory answer <repo> <n> --done [--note '<what happened>']
```

Never use `gh issue list`, `gh api` or `curl` to build the queue: the core
reads GitHub with conditional requests that cost no quota, and a second reader
would. Never comment or relabel with `gh`: `factory answer` writes the comment,
drops `needs-greg` and wakes the orchestrator waiting on it.

## Each item

`factory needs --json` gives `{asks: [...]}`, already sorted: most tickets
unblocked first, then priority, then longest waiting. Each item has `repo`,
`number`, `title`, `url`, `ask`, `type` (pick, text or done), `options`,
`minutes`, `images`, `blocks`, `priority`, `waited_minutes`, `kind`, `body`
and `warning`.

- `type: pick` is a decision and `type: text` a discussion: walk these first, in
  the order given.
- `type: done` is a manual task (his hands, money, sudo, phone, a playtest):
  hold it for the closing list.

## Asking

Greg reads on his phone. Before each question, write at most four lines: the
linked ticket (`[loser-picks#61](url)`), priority, how long it has waited, what
it unblocks, and the one fact from `body` that decides it. Open any local path
in `images` with Read so he sees it; give a URL as a link.

Then ask with `AskUserQuestion`:

- **pick:** the ask's options, at most four. Put your recommendation first with
  "(Recommended)" and one line of why in its description. Recommend the ask's
  `default` when it has one, otherwise what the body's evidence favours.
- **text:** draft two or three concrete answers from the body, recommended first.
  Greg can always type his own.
- Put up to four independent items in one call, so one screen settles them.
- If Greg says skip or later, leave the ticket alone and move on.

After each answer, record it at once with `factory answer`, passing `repo`
exactly as the JSON gives it (`GregHilston/gridkeep`). Add `--ready` when
the body says a build waits on this answer. Pass Greg's reasoning, if he gave
any, as `--note`, in his words. Exit 3 ("ticket changed") means run
`factory needs --json` again and re-ask only that item; exit 75 means the dradis
core is down, so stop and tell Greg.

## Closing list

Last, list the `done` items, grouped by `kind` and ordered as served. Give each
as one line: what to do, in the imperative, its minutes, and the link. Then ask
which he has already done, as a multi-select `AskUserQuestion`, and record each
with `factory answer <repo> <n> --done`.

End with counts: answered, skipped, tasks done, tasks left.

## Rules

- Never answer for Greg, and never act on an answer beyond recording it: the
  orchestrators pick up the work.
- An item with a `warning` has a malformed ask block: ask it from its title as
  text, and say the block needs fixing.
- Something that needs Greg but has no ticket goes on one: ask the repo's
  orchestrator to file it with `needs-greg` and an ask block. Don't keep a second
  list here.
