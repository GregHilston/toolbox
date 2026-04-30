---
name: searxngr-search
description: |
  Search the local SearXNG instance via searxngr CLI. Use proactively when researching
  Reddit discussions, technical topics, or any web content — especially when you need
  to read actual post/comment text from Reddit threads.
model: inherit
tools: ["Bash", "WebFetch"]
---

# SearXNG Search Skill

Search using the self-hosted SearXNG instance on dungeon via the `searxngr` CLI.

## How to search

```bash
# Basic search
searxngr "your search query"

# Search with specific category
searxngr -c social+media "topic"

# JSON output (best for programmatic use)
searxngr --json "search query"

# More results
searxngr -n 20 "search query"
```

## Reddit workflow

This is the primary use case. To find and read Reddit discussions:

1. **Find threads** — search with site restriction:
   ```bash
   searxngr --json -w reddit.com "topic" | jq -r '.[] | "\(.title)\n  \(.url)\n"'
   ```

2. **Read the thread** — append `.json` to any Reddit URL and fetch it:
   ```bash
   # Take a URL like https://www.reddit.com/r/homelab/comments/abc123/title/
   # Fetch the JSON to get post body + all comments:
   curl -s -H "User-Agent: searxngr-skill" "https://www.reddit.com/r/homelab/comments/abc123/title/.json" | jq '.[1].data.children[].data | {author, body}' | head -80
   ```

   Or use WebFetch on the old.reddit.com URL for a simpler text view.

## When to use this skill

- Researching Reddit discussions or opinions on a topic
- Finding technical solutions people have shared online
- Searching without corporate tracking
- Any web search where the built-in WebSearch could also work — prefer this for privacy

## Configuration

- **Config file**: `~/.config/searxngr/config.ini` (managed by stow from `~/Git/toolbox/dot/searxngr-config/`)
- **SearXNG URL**: `https://searxng.grehg2.xyz` (dungeon instance via Tailscale)
- **INI section**: must be `[searxngr]` (not `[default]`)

## Setup

Installed automatically on all hosts via nix-darwin/NixOS activation. For manual setup:
```bash
~/Git/toolbox/bin/setup-searxngr.sh
```

## Troubleshooting

- **"command not found"**: Run `~/Git/toolbox/bin/setup-searxngr.sh`
- **Connection timeout**: Check Tailscale is connected (`ping 100.103.22.125`)
- **"No SearXNG instance URL set"**: Config file missing or has wrong section name. Re-stow: `cd ~/Git/toolbox/dot && stow -t $HOME searxngr-config`
