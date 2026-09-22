Build a scored Vermont small-business prospect list from the data already on disk
All source data is ALREADY DOWNLOADED. Do not fetch anything. Do not search the web. There is no internet.

Four files in /instance/workspace/data/raw/:

1. vt-childcare-providers.json — 1,048 licensed child care providers. THE SPINE. Every row has provider_name, address_1, provider_town, zip_code, county, latitude, longitude, phone_number, email_address, total_licensed_capacity, current_stars_level, license_type.
2. vt-dfs-licensed-trades.json — 11,489 licensed electricians, plumbers and gas installers: last_name, first_name, street_address, city, zip_code, type_desc, level_desc, license_number, license_exp_date.
3. vt-website-probes.json — one row per custom email domain seen in file 1, already probed: reachable, status, final_url, ttfb_ms, title, has_viewport, parked, copyright_year.
4. socrata-active-vendors.json — 600 state vendor registrations. Thin: vendor, name, city, st, postal, location_1. NOTE its ":@computed_region_5r79_s8s6" field is a Socrata region id, NOT a NAICS code. Do not emit it as an industry.

THE FILES ARE TOO BIG TO READ. vt-dfs-licensed-trades.json is 3.2 MB and vt-childcare-providers.json is 1.4 MB — reading either whole would consume most of your context and leave you nothing to work with. Inspect them with `head -c 2000`, `jq '.[0]'`, `jq 'length'` and `jq -r '.[0] | keys[]'` from the terminal, and have your CODE stream them. Never read a raw file into the conversation.

Build a Python package under /instance/workspace following ENGINEERING.md: domain/ pure (no I/O imports), DTOs adapter-local and frozen, ports as typing.Protocol, one mapper per source tested against that source as a recorded fixture.

THE WEB-PRESENCE SIGNAL IS THE POINT. Derive it in the domain layer:
- Split every email into a domain. A domain in the freemail list (gmail, yahoo, hotmail, aol, outlook, comcast, icloud, msn, myfairpoint, verizon, att, charter, together, vermontel, burlingtontelecom) means the business has NO web presence of its own — that is the strongest buying signal in the dataset, not missing data.
- A custom domain joins to file 3. Unreachable, parked, missing viewport, or a copyright year <= 2020 each mean a site that exists and is bad — the second strongest signal.
- A reachable, mobile-ready, current site means deprioritise.

Emit data/final/businesses.csv with EXACTLY these columns, one row per business:

business_name, contact_name, is_organisation, category, street, town, county, zip_code,
latitude, longitude, phone, email, email_domain, email_domain_is_freemail,
website_url, website_reachable, website_has_viewport, website_parked, website_copyright_year,
source, outreach_score, outreach_reason

- is_organisation: false when the name parses as a person ("Abair,Andrew R." or "Wallace,Kyle"), true otherwise. Trades rows are people; most providers are organisations.
- contact_name: the person where there is one, else empty.
- category: "child care", "electrician", "plumber", "gas installer", or "state vendor".
- source: which input file the row came from.
- A row nobody can contact is not a prospect, whatever its web presence. The trades file carries no phone or email, so those rows must score BELOW an otherwise-equal provider that has both. Contactability is a component signal like any other: keep it in a column and let the weighting see it.
- outreach_score: float 0.0-1.0, required, never null, computed in the domain layer from the recorded signals above, with the weighting in ONE place and unit-tested including boundaries. Never ask a model for it.
- outreach_reason: one plain sentence naming the ACTUAL signals that moved the score for THAT row. Not a template. "No website; uses a gmail address; 42 licensed places in Chittenden" is useful. "Vermont-registered business; city and postal on file" is not.

DONE WHEN all five hold:
1. `uv run pytest` passes with zero failures
2. `uv run vt-smb build` exits 0 from a clean tree
3. data/final/businesses.csv has at least 1,000 rows
4. every row has outreach_score in [0,1] and a non-empty outreach_reason
5. at least 400 rows have a non-empty phone AND a non-empty email
