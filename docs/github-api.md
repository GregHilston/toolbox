# GitHub API quota: development first

Greg's account has two hourly buckets, shared by every orchestrator, builder and script on
every host:

| Bucket | Size | Who spends it |
|---|--:|---|
| REST (`core`) | 5,000 calls | `gh api repos/...`, `git push` hooks, scripts that call REST |
| GraphQL | 5,000 points | `gh issue`, `gh pr`, `gh label` (most `gh` subcommands), `gh api graphql` |

The quota is for development: orchestrators labelling, commenting and landing tickets. An
analysis never spends more than a few percent of either bucket (Greg, 2026-11-20).
`gh api rate_limit` costs nothing; read it before and after anything bulk.

## Bulk reads go through paged GraphQL, never REST per issue

On 2026-11-20 a ticket-timeline test read each issue's timeline over REST
(`repos/O/R/issues/N/timeline --paginate`): about 3 calls an issue, 1,326 calls for one
gridkeep run. A few test runs emptied the REST bucket for 40 minutes, and the orchestrator's
`gh` calls failed until it reset.

The same data through one paged GraphQL query costs about 15 points per repo (389 issues),
and no REST calls:

```graphql
issues(first: 25, after: $after, filterBy: {since: $since}) {
  nodes { number closedAt
    timelineItems(first: 100, itemTypes: [LABELED_EVENT, UNLABELED_EVENT]) { ... } } }
```

Rules for any script that reads many issues, PRs or timelines:

- Page through GraphQL with nested connections; never loop a REST call over issues.
- Check `rate_limit` first and refuse a run that would leave the orchestrators under 1,500.
- Run it on a schedule no tighter than hourly, or on demand; never in a watcher loop.

## The GraphQL trap: 100 issues a page returns stale timelines

With `issues(first: 100)` and a nested `timelineItems`, GitHub returned an older snapshot of
each issue's label history, silently: no error, no truncation flag, `totalCount` agreeing
with the stale nodes. #375 came back with 0 events against 9, and only 73 of 389 tickets
showed a stage label against 225. A single-issue query, and the same list at
`first: 25`, both returned the full history.

So: page at 25 when nesting timelines, and before trusting a new bulk query, compare two or
three issues against a single-issue query.
