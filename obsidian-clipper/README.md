# Obsidian Web Clipper templates

`templates/` holds one [Obsidian Web Clipper](https://obsidian.md/clipper) template per
file, in the extension's own export format. They write clips to `clippings/` and recipes
to `recipes/` in the shape the notes vault expects. Each template
picks itself through its triggers, so no manual choice is needed when you clip.

Nix installs the extension in Firefox on every Mac (an enterprise policy in
`nixos/modules/darwin/homebrew-base.nix`; quit and reopen Firefox after the deploy) and on
every NixOS desktop (`nixos/modules/programs/gui/firefox/`). The templates and the
settings below still go in by hand, once per browser profile.

## Why the settings cannot be automated

The extension keeps its settings in `browser.storage.sync` and its source never reads
`storage.managed`, so a Firefox enterprise policy can install it but cannot configure it.
Settings that live anywhere else are an open upstream request
([obsidian-clipper#174](https://github.com/obsidianmd/obsidian-clipper/issues/174)).
With Firefox Sync on, they follow you to your other Firefoxes.

## Import the templates

Open the extension, click the cog, select any template, then **Import** (top right) and
pick a file from `templates/`. Repeat for each file. Re-importing a template whose name
already exists adds a copy named `recipe (1)` and so on; delete the old one.

An import lands at the top of the list, and the top template is the fallback for any page
no trigger matches. Drag your general-purpose template back to the top afterwards, or
unmatched pages get whichever template you imported last.

A property that already exists in **Properties** keeps the type it has there, not the one
in the file. If `dinner` or `leftovers` imports as text instead of a checkbox, fix its type
in that list.

## Vault

Under **General**, the vault name must match the notes vault exactly, or clips go to
whichever vault Obsidian opened last.

## Interpreter (the recipe template only)

The recipe template asks a model for `protein`, `dinner` and `leftovers`. Under
**Interpreter**, turn it on and add:

- a provider: custom, Base URL `https://llm.grehg2.xyz/v1/chat/completions`, API key the
  LiteLLM master key from 1Password (`Infra`). The key lives only in the browser's
  storage; never commit it.
- a model: that provider, model ID `local-small`.

The template's context is only the recipe's name, description, category, yield and
ingredients, so the request stays small. The gateway is reachable only over Tailscale.
Click **interpret** in the popup before **Add to Obsidian**; with Interpreter off the
three properties come out empty.

## What a live clip captures

- **Only what the page has loaded.** Reddit and Hacker News collapse and lazy-load
  comments, and the clip holds only the ones in the page when you click. Expand what you
  want first.
- **A link to one comment** shows that comment and its replies, not the comments above
  it. The clip therefore has no parent chain, unlike the vault's bulk conversion. If the
  context matters, open the parent first ("context" on Reddit, "parent" on HN) and clip
  that.
- **YouTube** transcripts and duration come from the page's metadata, which YouTube drops
  when you reach a video by clicking inside the site. Reload the video page before
  clipping if they come out empty.
- **Recipes** need schema.org `Recipe` data on the page. A page without it gets the top
  template in the list instead.
