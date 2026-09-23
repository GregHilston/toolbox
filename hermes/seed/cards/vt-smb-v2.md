Rebuild the Vermont prospect list so it is a list of BUSINESSES, not of licence records
All source data is ALREADY DOWNLOADED in `data/raw/`. There is no internet. Do not fetch anything.

WHY THIS IS A REBUILD, NOT A TWEAK. v1 emitted one row per source record and called child care "the spine". The result: all 1,031 emailable rows were child care providers, one person holding six trade licences appeared six times, and 1,790 rows were expired licences. No source is the spine. The prospect is. Every file contributes EVIDENCE about prospects.

FIVE INPUT FILES. Inspect them from the terminal — `jq 'length'`, `jq -r '.[0]|keys[]'`, `jq -c '.[0]'`, `head -c 2000`. Some are megabytes. NEVER read a raw file into the conversation; have your CODE stream them.

1. osm-vt-businesses.json — 5,969 OpenStreetMap businesses across 287 distinct verticals. Has name, category, category_kind, street/city/zip, lat/lon, and directly: phone, email, website, facebook, opening_hours. The widest vertical coverage you have.
2. vt-childcare-providers.json — 1,048 licensed providers. phone + email on every row.
3. vt-dfs-licensed-trades.json — 11,489 licensed trades. NO phone, NO email, NO business name: a person, an address, a licence type/level/expiry.
4. socrata-active-vendors.json — 600 state vendor registrations. Thin. Its ":@computed_region_5r79_s8s6" is a Socrata region id, NOT a NAICS code. Never emit it as an industry.
5. vt-website-probes.json — one row per probed domain. On a probe that never connected, EVERY field but domain/reachable/probed_at is null.

=== STEP 1 IS A DELIVERABLE, NOT ADVICE ===

Before you write a single mapper, produce `data/profile.md` and SHOW IT TO ME. It must contain, per source file:
- every distinct value of every field you intend to map to a fixed set, with counts
- the null rate of every field you intend to score on
- the row count, and the count of distinct values of whatever you plan to use as an identity key

Then STOP and ask me about anything where the data disagrees with this card. v1's builder had a `clarify` tool and two files telling it to ask, defaulted 2,120 rows into a category belonging to another source file, and never said a word. Asking is part of the job, not an interruption to it.

=== OUTPUT: THREE FILES, NOT ONE ===

`data/final/prospects.csv` — ONE ROW PER BUSINESS YOU WOULD CONTACT. Columns:
prospect_id, business_name, contact_name, is_organisation, verticals, towns, county,
zip_code, latitude, longitude, phone, email, email_domain, email_domain_is_freemail,
website_url, website_status, facebook_url, web_presence, evidence_count, sources,
outreach_score, outreach_reason

`data/final/evidence.csv` — ONE ROW PER SOURCE RECORD, joined by prospect_id. Columns:
prospect_id, source, source_record_id, name_as_given, street, town, zip_code,
category, detail, valid_until, match_rule, match_confidence

`data/final/suppression.csv` — header only, created empty:
prospect_id, suppressed_on, reason
It exists now because US B2B cold email needs a working opt-out, and a suppression key
is painful to retrofit onto ids that move between runs.

=== IDENTITY IS THE HARD PART. DO IT EXPLICITLY ===

- prospect_id is DERIVED, never generated: a stable hash of the normalised identity key. Two consecutive runs over unchanged inputs MUST produce identical ids. A UUID would reshuffle every id on every refresh and break the suppression join.
- Normalise before comparing: case, punctuation, and legal suffixes (inc, llc, co, corp, ltd).
- Every evidence row records the `match_rule` that attached it and a `match_confidence` in [0,1].
- AMBIGUOUS MATCHES ARE EMITTED, NEVER SILENTLY MERGED. Write them to `data/final/review.csv` with the competing candidates. Two different people with one surname in one zip is real, and merging them must be a visible decision.
- A business with several licences, several towns, or several verticals is ONE prospect. `verticals` and `towns` are semicolon-joined, sorted, deduplicated.

=== SIGNALS ===

web_presence is one of: `none` (no site and no facebook), `facebook_only`, `site_broken`, `site_dated`, `site_ok`, `unknown`. `unknown` means NOT LOOKED AT and must never be scored as if it were a measurement.

- A freemail email domain (gmail, yahoo, hotmail, aol, outlook, comcast, icloud, msn, myfairpoint, verizon, att, charter, together, vermontel, burlingtontelecom) means no site of its own — the strongest buying signal in the data, and a FINDING, not missing data.
- A row with no email at all is NEITHER freemail NOR custom-domain. Emit empty, not false.
- A custom domain joins to file 5. Unreachable, parked, no viewport, or copyright year <= 2020 => `site_broken`/`site_dated`.
- A website field pointing at facebook.com is `facebook_only`, not a website.
- Contactability is a component signal: a prospect nobody can contact must score BELOW an otherwise-equal one with a phone and an email.
- Use the licence data you were given and v1 ignored: an EXPIRED licence (valid_until in the past) is not a prospect. `level_desc` of Master means someone who runs a shop; Journeyman means someone who works in one.
- Competitive density is a real signal and it is free: how many licensed trades share this town.

outreach_score is a float in [0,1], never null, computed in the domain layer, with the weighting in ONE place and unit-tested at its boundaries. Never ask a model for it.

outreach_reason is one plain sentence naming ONLY the signals that actually moved THAT row's score, with their evidence. "No website of its own — emails from gmail.com; Master electrician; one of 326 licensed trades in Milton" is useful. "No contact information; website status unknown; site quality indeterminate" is four non-findings and was v1's most common reason, shared by 11,489 rows.

=== ENGINEERING ===

Follow ENGINEERING.md. domain/ pure (no I/O imports), DTOs adapter-local and FROZEN, ports as typing.Protocol and only for things something actually implements, one mapper per source tested against that source as a recorded fixture. A Protocol nothing satisfies, a DTO that is declared and bypassed, or a factory nothing calls is ceremony — delete it or wire it.

=== DONE WHEN all of these hold ===

1. `uv run pytest` passes with zero failures
2. `uv run vt-smb build` exits 0 from a clean tree, and `data/profile.md` exists
3. prospects.csv has at least 10,000 rows, covering AT LEAST 40 distinct verticals
4. every prospect row has outreach_score in [0,1] and a non-empty outreach_reason
5. at least 2,500 prospects have a non-empty phone OR email
6. every evidence row's prospect_id exists in prospects.csv, and every prospect has >= 1 evidence row
7. running the build TWICE produces byte-identical prospect_id sets
8. no prospect_id appears twice in prospects.csv
9. every distinct source value of a field you mapped to a fixed set appears in the output, or is listed in profile.md with the reason it was dropped
10. for any derived column, its empty-rate equals the empty-rate of the column it derives from
11. no single outreach_reason covers more than 5% of rows
12. suppression.csv exists with its header
