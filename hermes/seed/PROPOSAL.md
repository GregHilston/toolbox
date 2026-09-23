# vt-smb v2 — proposal

## Why the dataset looks like a childcare project

It is not a targeting decision. `fetch-vt-sources.py` pulls two Socrata
datasets, and **`vt-childcare-providers.json` is the only one with email
addresses**. The whole web-presence signal is derived from the email domain, so
the one file that has emails became "THE SPINE" in `BRIEF.md`, and every other
source became a footnote.

The consequence is in the output: **all 1,031 emailable rows are childcare
providers.** The 11,489 licensed trades — sole-trader electricians, plumbers and
gas installers, who are the actual buyers of a small business website — carry no
phone and no email at all, so they sit in the file contributing nothing.

**Fix: no source is the spine.** The spine is the *prospect*. Every source
contributes evidence about prospects, and a source with no contact details is a
source that describes a prospect we must reach another way — not a second-class
row.

## One row per prospect, or many?

Both, as two files, because they answer different questions.

**`prospects.csv` — one row per entity you would contact.** This is the mailing
list. Carries `prospect_id`, best-known name, one contact channel, the score,
the pitch line, and a count of supporting evidence.

**`evidence.csv` — one row per source record**, with a `prospect_id` foreign
key. A person holding six trade licences is six rows here and one row there,
and the six are worth keeping: each has its own type, level, town and expiry,
and "Master electrician *and* gas installer in two towns" is a stronger
prospect than either licence alone.

Three rules make this work, and all three are places a bot will otherwise
invent something:

1. **`prospect_id` is derived, not generated.** A hash of the normalised
   identity key, so re-running the pipeline produces the same ids. A random
   UUID would reshuffle every id on every refresh and silently break the
   suppression list below.
2. **Identity resolution states its rule and its confidence**, per row. Two
   different Andrew Abairs in the same zip is a real possibility, and merging
   them must be a visible decision rather than a side effect.
3. **Ambiguous matches are emitted, never silently merged.** A `review` bucket
   with the competing candidates, because the alternative is a mailing list
   that is confidently wrong.

**Why the id has to be stable:** the opt-out list joins on it. Build a
`suppression.csv` now — `prospect_id`, date, reason — even while it is empty.
US B2B cold email is legal under CAN-SPAM, but it requires a working opt-out,
accurate headers and a physical postal address in every message. Retrofitting a
suppression key onto a list whose ids move is genuinely painful; adding it up
front is ten minutes.

## Cleaning worth doing, all of it from data already on disk

| | finding | effect |
|---|---|---|
| duplicate humans | 11,489 rows are 10,007 distinct person+zip; one person holds **6** licences | emailing the same electrician six times |
| expired licences | **1,790** already expired, 9,699 live | 15% of the list is lapsed or retired |
| `level_desc` unused | 3,663 **Master**, 2,140 Journeyman | a Master runs the shop; a Journeyman works for one |
| town casing | 1,360 city strings, 1,294 lowercased | 66 dupes (`ST ALBANS` / `St Albans`) |
| density unused | 326 trades in Milton, 268 in Colchester | *"one of 326 licensed trades in your town, four have a website"* is the cold email |

## Getting contact details for the other 12,106 — MEASURED, and mostly bad news

I tried the top three before proposing them. Two do not work.

**OpenStreetMap does not enrich the trades.** Of 11,489 licensed trades, **31**
surname+town matched an OSM POI, and spot-checking shows those are false —
"Block" the gas installer against H&R Block. Only 36 OSM names even look like a
trade. The reason is structural: **OSM maps premises.** A sole-trader
electrician working from a van at a home address is not a mapped feature, and
never will be. Convenience stores and supermarkets are.

**There is no Vermont business registry in open data.** 172 datasets on
data.vermont.gov, none with trading names plus contacts. The Secretary of
State's search is a web app at `bizfilings.vermont.gov`. The nearest thing is
Vendor Payments (2.59M rows) — business names, no contact details.

**Search does find them, one at a time.** "Trombly, plumber" resolves to
Trombly Plumbing & Heating with a live site — but the person-to-business link
is inferential and it got the town wrong (St. Johnsbury, not St. Albans) and
surfaced a New Hampshire namesake. At 11,489 rows that is a project, not a step.

### So the trades are probably not an email segment

Not at acceptable cost. They have **no business name in the data at all** — only
a person, an address and a licence — and the person-to-business link is the
whole problem. Treat them as a phone or direct-mail segment, or as a long-tail
search project, and stop pretending the email pipeline will reach them.

### What OSM IS good for

A **new prospect pool**, not an enrichment. Fetched and saved to
`osm-vt-businesses.json`:

| | |
|---|---|
| named Vermont businesses | **3,068** |
| with a phone | 1,054 |
| with an email | 181 |
| **with a phone and NO website** | **238** — immediately actionable |
| whose entire web presence is a Facebook page | **77** — the pitch writes itself |

That is 238 prospects you can call tomorrow, against the 617 warm ones the
current dataset yields, and they are spread across every vertical rather than
concentrated in childcare.

### Still worth trying, in this order

1. **Domain guessing into the prober we already have** — free, but expect a low
   hit rate against surnames with no trading name attached.
2. **Facebook** — now the *first*-class path for trades rather than the last,
   because it is the only source that links a person to a local trading name at
   scale. Same engineering caveat: its own adapter, every field optional, never
   fails the pipeline. And 77 rows of the signal arrive free from OSM already.
3. **VT Secretary of State** — needs scraping a web app. Highest value for the
   trades, highest effort.

## Original plan, kept for the record

## Getting contact details for the other 12,106

In the order I would build them:

1. **OpenStreetMap / Overpass.** Free, no key, no ToS friction, and
   `ENGINEERING.md` already specifies an `overpass/` adapter that was never
   built. POIs carry `website`, `phone`, `email`, `opening_hours`. Match on
   name + town.
2. **Domain guessing into the prober we already have.** "Abair Gas, St Albans"
   → `abairgas.com`. Low hit rate, zero marginal cost, and every hit arrives
   with a measurable site.
3. **VT Secretary of State registry.** Connects a licensed *person* to a
   registered *trading name* — which is what a domain guess needs and what you
   actually pitch to.
4. **Facebook pages.** The strongest signal available in rural Vermont: a trade
   with 400 followers and no website is the entire pitch. Two caveats worth
   planning around rather than arguing about. It breaks constantly — Meta
   rate-limits and blocks aggressively, so treat every field as optional and
   never let a failure fail the pipeline. And it is against Meta's terms, which
   is a contract matter and your call, not a legal one.
   **Build it last, in its own adapter, as an enrichment pass over a list that
   already works without it.** Much of the value arrives free anyway: OSM and
   registry `website` fields frequently already point at facebook.com.

Not doing: Google Places. Declined.

## Better signals from the probe we have

Today it records reachable / viewport / parked / copyright year. Add: Wix,
Squarespace, GoDaddy and Weebly fingerprints (a template site is cheap to
beat), missing or expired SSL, `last-modified` age, and whether the "site" is a
redirect to Facebook or Linktree.

## How the next Hermes run should differ

1. **The card must not name a spine vertical.** Ours did, and the output
   inherited it.
2. **Profiling is an acceptance criterion, not advice.** Before any mapper is
   written: the distinct values of every field being mapped to an enum, and the
   null rate of every field being scored on. The builder had `clarify`, and two
   files told it to ask rather than guess, and it silently defaulted 2,120 rows
   into the wrong category. Asking must be a deliverable.
3. **Data contracts go in the card as DONE WHEN clauses**, so they are checked
   rather than hoped for:
   - every distinct source enum value maps to a distinct output category
   - `category` x `source` is a function
   - a derived column's null rate equals its source column's
   - no generated per-row string covers more than 5% of rows
   - `prospect_id` is stable across two consecutive runs
4. **The orchestrator reviews every build**, running `verify-agent-output`
   first. Not on request — the builder cannot be relied on to notice it needs
   help.
