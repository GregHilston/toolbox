---
name: youtube-transcript
description: Fetch the transcript and title of a YouTube video as JSON. Use when the user provides a YouTube URL and you need the spoken content (captions) for analysis, summarization, quoting, or search.
---

# YouTube Transcript

<!-- Vendored from https://github.com/amosblomqvist/pi-config/blob/main/skills/youtube-transcript -->

Fetches a YouTube video's title and full transcript by pulling captions via `yt-dlp`. Prefers manual English subtitles, falls back to auto-generated English.

## Requirements

- `yt-dlp` and `ffmpeg` on PATH (already in `nixos/config/base-packages.nix` on every managed host)
- Python 3

## Usage

Run `fetch_transcript.py` from this skill's own directory (the directory this SKILL.md lives in):

```bash
python3 fetch_transcript.py "<youtube_url>"
```

## Output

Prints a JSON object to stdout:

```json
{
  "title": "Video title",
  "transcript": "full transcript text as a single string"
}
```

Progress/info logs go to stderr. On failure (no English captions, network error, bad URL), the script exits non-zero with a message on stderr.

## Notes

- Only English captions are attempted (`en`, `en-US`, `en-GB`, then any `en*`). Manual captions are preferred over auto-generated.
- Transcript is plain text with timing/formatting stripped — not timestamped.
- For non-English videos or videos with captions disabled, the script will fail.
