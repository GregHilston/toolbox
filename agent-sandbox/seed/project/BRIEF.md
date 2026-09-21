# vt-smb — Vermont small businesses, as a prospect list

## Why this exists

My owner sells web design and hosting as a service. He needs to know which
Vermont small businesses exist, what they do, who runs them, how to reach them,
and — the part that decides whether they are worth approaching — whether they
have a website and whether it is any good. A business with no site, or with a
site that is broken, unencrypted, unreadable on a phone, or last touched in
2011, is a prospect. A business with a well-kept site is not.

Weight the work toward **northern Vermont**: Chittenden, Franklin, Grand Isle,
Lamoille, Orleans, Essex, Caledonia and Washington counties. Statewide coverage
is welcome where it is free to obtain, but northern coverage is what is being
paid for. Depth beats breadth: five hundred rows where every field is sourced
and checked are worth more than fifty thousand rows of registry noise.

## What "done" means

Two deliverables, and the second is the one that matters.

1. **A dataset.** `data/final/`, in Parquet and CSV, with a written schema and a
   per-field note on where the value came from and when it was fetched.
2. **The pipeline that produced it.** Anyone can `uv run vt-smb build` on a clean
   checkout with an empty `data/` and get the dataset back, and
   `uv run vt-smb refresh` later to pick up what has changed. Tests pass.
   A dataset I cannot regenerate is a dead artifact.

An honest first milestone is **one source, end to end, with tests** — ingest,
map to the domain, persist, and a CLI that rebuilds it — not a broad dataset
from many half-wired sources. Get one vertical slice working, then widen it.

## What to record per business

Group these; they are not a flat wish-list.

- **Identity** — legal name, trade or "doing business as" name, registry
  identifier where one exists, status (active / dissolved / lapsed).
- **What it does** — a human description, plus a classification. Prefer an
  existing scheme (NAICS from the registry, or OSM's category tags) over
  inventing one, and record which scheme a given value came from.
- **Where it is** — street address, town, county, ZIP, and coordinates where
  available. County matters: it is how northern-Vermont weighting is applied.
- **Who runs it** — registered agent, officers, or owner where the registry or
  the site discloses it. Often absent. Absent is a fine answer; invented is not.
- **How to reach them** — phone, email, contact-form URL, mailing address.
- **Online presence** — website, Google Maps / Apple Maps / Yelp listings,
  Facebook or Instagram page. Note explicitly when a business has *only* a
  social page and no site of its own; that is one of the strongest signals in
  the whole dataset.
- **Website quality** — see below.
- **Provenance** — for every field, which source and which fetch date. This is
  what lets the dataset be refreshed, audited, and defended.
- **`outreach_score`** — a float from 0.0 to 1.0. 1.0 means "definitely worth
  approaching"; 0.0 means "do not bother". This is the column the whole dataset
  exists to produce, so it is required on every row and must never be null.
- **`outreach_reason`** — one sentence, in plain language, saying *why* that
  score. "No website at all; active food licence; phone and owner name on file"
  is a good reason. "Score 0.8" is not a reason.

### How to score

The score is a judgement, but it must be a *reproducible* one: compute it in the
domain layer from the signals already on the record, never by asking a model.
Put the weighting in one place, document it, and test it.

Roughly, what raises a score: no website at all; a website that fails the
quality checks below; only a Facebook or Instagram page; a business type that
plainly needs a web presence to get customers (restaurants, trades, retail,
lodging, services); a current licence or registration proving it actually
trades; reachable contact details. What lowers it: a modern, fast,
mobile-friendly site; a national chain or franchise; a dissolved or lapsed
registration; no way to contact anyone.

Record the component signals alongside the score. A score nobody can take apart
is a score nobody can trust or tune, and my owner will want to know *why*
before he writes to anyone.

## Sources, in priority order

Open and official first. Verify each one's current terms before relying on it;
these are starting points, not guarantees.

1. **Vermont Secretary of State, Corporations Division** — the authoritative
   registry of business entities, with names, status, addresses, agents and
   officers. The canonical spine everything else is joined onto.
2. **`data.vermont.gov`** — the state's Socrata open-data portal, with a SODA
   API. Licensing, food, lodging and liquor registers here are gold: they are
   per-establishment, current, and name real operating businesses rather than
   shell registrations.
3. **OpenStreetMap, via the Overpass API** (ODbL — attribution required, and
   record that requirement). Carries `website`, `phone`, `opening_hours`,
   `cuisine` and category tags for a surprising share of Vermont main streets.
4. **Regional chamber and downtown-association directories** — small, curated,
   and often list the owner by name.
5. **Google Places API / Yelp Fusion API** — only through the official APIs, and
   only if a key is supplied in the environment. Do not scrape Google Maps or
   Yelp HTML: it is against their terms, it breaks constantly, and it would make
   the pipeline unrepeatable, which defeats the point of the project.

Registry data is stale and full of entities that never traded. Open licensing
and OSM data is current but partial. Neither is the dataset on its own — the
value is in the join, and the join is where the hard problems are (name
normalisation, address matching, deciding when two records are one business).
That is domain logic. Treat it as such.

## Website quality

Assess with signals obtainable without any paid key:

- Does the site resolve and respond at all? What status?
- HTTPS, and is the certificate valid and current?
- Time to first byte, and total page weight.
- Is there a `<meta name="viewport">`? Its absence is a near-certain sign the
  site predates mobile and will be unusable on a phone.
- `<title>` and meta description present and not boilerplate.
- Parked, placeholder or registrar holding pages — detect and flag them.
- A Facebook or Instagram page given as the website.
- `Last-Modified`, visible copyright years, or dated content: staleness.

Use PageSpeed Insights only if an API key is present. Roll the signals into a
score, but **keep the individual signals in the dataset** — the score is a
convenience, the signals are the evidence, and my owner will want to know *why*
something scored badly before he writes to anyone.

## Rules of collection

- Honour `robots.txt`. Where it forbids, record that it forbids and move on.
- Rate-limit every source, and identify with a real User-Agent and a contact
  address. Be a good citizen; these are small public services.
- **Cache every raw response, content-addressed, under `data/raw/`.** Re-runs
  then cost nothing, results are reproducible, and recorded responses become the
  fixtures the adapter tests run against. This one decision buys correctness,
  speed and testability at once — do it before the first fetch, not after.
- Record the source and fetch date for every contact detail. That is what is
  needed if anyone later asks where an address came from.
- Read a source's terms before building on it, and write what they say into
  memory next to the adapter that depends on them.
