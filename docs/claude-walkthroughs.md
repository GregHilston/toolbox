# Walking Greg through a website, and scripting a site's download

Read this when Greg is stuck on a website (Steamworks, a vendor dashboard, a bank), or wants a site's download scripted. The global `CLAUDE.md` points here.

## He is stuck on a screen

- He saves the page with ⌘S and gives you the `.html` path. Parse it with a short `python3 -I` script for the text, links, inputs and selected options; don't Read the whole file.
- Walk him through one screen at a time, and say plainly when you're guessing at a screen you haven't seen.
- Open each screen's steps with one line on why the step exists, then short numbered clicks naming the exact button text. On 2026-10-28 "set it live on default, then beta" lost him until it said why and named the one dropdown on the row.
- If the file isn't there, say so and wait for him to re-save. Don't fetch the same facts another way (2026-10-26).

## Scripting a site's own download

He would rather save a sanitized HAR (DevTools → Network → **Save all as HAR (sanitized)**) than have you drive Chrome.

- Read only URLs, parameter names and statuses from the HAR.
- Write a console snippet he pastes into his logged-in tab, so his session never leaves the browser (2026-11-12, a bank CSV backfill).
